"""
Rerun today's crawl/LLM/aggregation pipeline for one hardware item only.

Behavior:
1. Delete today's price_snapshots and daily_stats for the selected hardware
2. Crawl today's data again
3. Validate today's snapshots with LLM, sequentially
4. Recompute today's daily_stats

Examples:
    python rerun_one_hardware.py --hardware-name "RTX 4090"
    python rerun_one_hardware.py --hardware-id 12 --pages 5
    python rerun_one_hardware.py --hardware-name "i7-14700K" --verbose-llm
"""

import argparse
import asyncio
import json
from datetime import date

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.hardware_pool import get_search_keywords
from app.crawler.xianyu import crawl_keyword
from app.models import DailyStats, HardwareItem, PriceSnapshot
from app.services.llm_validator import validate_snapshot_rows_sequential
from app.services.stats import compute_daily_stats, save_snapshots


def _print_raw_items(raw_items) -> None:
    if not raw_items:
        print("No raw items captured.")
        return

    print(f"\nCaptured {len(raw_items)} raw items:\n")
    print(f"{'#':<4} {'Price':>8}  {'Title':<50}  {'Area':<10}  Seller")
    print("-" * 110)
    for i, item in enumerate(raw_items, 1):
        title = item.title[:48] if item.title else "-"
        area = (item.area or "-")[:10]
        seller = item.seller or "-"
        print(f"{i:<4} {item.price:>8.0f}  {title:<50}  {area:<10}  {seller}")


def _print_validation_rows(validation_rows) -> None:
    if not validation_rows:
        print("No snapshots selected for LLM validation.")
        return

    print(f"\nSnapshots sent to LLM ({len(validation_rows)} rows):\n")
    print(f"{'#':<4} {'ID':<6} {'Price':>8}  {'Title':<50}")
    print("-" * 80)
    for i, (snapshot, _) in enumerate(validation_rows, 1):
        title = snapshot.title[:48] if snapshot.title else "-"
        print(f"{i:<4} {snapshot.id:<6} {snapshot.price:>8.0f}  {title:<50}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete today's data for one hardware item, then crawl/validate/aggregate again.",
    )
    parser.add_argument("--hardware-id", type=int, help="hardware_items.id")
    parser.add_argument("--hardware-name", help="hardware_items.name, case-insensitive exact match")
    parser.add_argument("--pages", type=int, default=3, help="Max crawl pages for this rerun")
    parser.add_argument(
        "--verbose-llm",
        action="store_true",
        help="Print full LLM request/response JSON during validation",
    )
    return parser.parse_args()


def _llm_debug_printer(payload: dict) -> None:
    event = payload.get("event", "unknown")
    title = payload.get("title", "")
    hardware_name = payload.get("hardware_name", "")
    attempt = payload.get("attempt", "")

    print("\n" + "=" * 80)
    print(f"LLM DEBUG | event={event} | attempt={attempt} | hardware={hardware_name}")
    print(f"title={title}")

    if event == "request":
        print(f"url={payload['url']}")
        print("request_json=")
        print(json.dumps(payload["payload"], ensure_ascii=False, indent=2))
    elif event == "response":
        print(f"status_code={payload['status_code']}")
        print("response_json=")
        print(json.dumps(payload["response_json"], ensure_ascii=False, indent=2))
        print("response_content=")
        print(payload["response_content"])
    elif event == "parsed_result":
        print("parsed_json=")
        print(json.dumps(payload["parsed_json"], ensure_ascii=False, indent=2))
        print(f"is_valid={payload['is_valid']}")
        print(f"reason={payload['reason']}")
    elif event == "error":
        print(f"error_type={payload['error_type']}")
        print(f"error={payload['error']}")


async def _resolve_hardware(session, hardware_id: int | None, hardware_name: str | None) -> HardwareItem:
    if hardware_id is not None and hardware_name is not None:
        result = await session.execute(
            select(HardwareItem).where(
                HardwareItem.id == hardware_id,
                HardwareItem.name.ilike(hardware_name),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise ValueError("`--hardware-id` and `--hardware-name` do not match the same hardware item")
        return item

    if hardware_id is not None:
        item = await session.get(HardwareItem, hardware_id)
        if item is None:
            raise ValueError(f"Hardware id not found: {hardware_id}")
        return item

    if hardware_name is not None:
        result = await session.execute(
            select(HardwareItem).where(HardwareItem.name.ilike(hardware_name))
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise ValueError(f"Hardware name not found: {hardware_name}")
        return item

    raise ValueError("Either --hardware-id or --hardware-name is required")


async def main() -> None:
    args = _parse_args()
    today = date.today()

    async with AsyncSessionLocal() as session:
        hardware = await _resolve_hardware(session, args.hardware_id, args.hardware_name)
        search_keywords = get_search_keywords(hardware.name)

        delete_stats = await session.execute(
            delete(DailyStats).where(
                DailyStats.hardware_id == hardware.id,
                DailyStats.stat_date == today,
            )
        )
        delete_snapshots = await session.execute(
            delete(PriceSnapshot).where(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == today,
            )
        )
        await session.commit()

        print(
            f"Deleted today's old data for {hardware.name}: "
            f"snapshots={delete_snapshots.rowcount or 0}, daily_stats={delete_stats.rowcount or 0}"
        )

        print(f"Search keywords: {search_keywords}")
        raw_items = await crawl_keyword(search_keywords, max_pages=args.pages)
        _print_raw_items(raw_items)
        saved = await save_snapshots(session, hardware, raw_items, today)
        await session.commit()
        print(f"Crawl finished for {hardware.name}: raw={len(raw_items)}, saved={saved}")

        result = await session.execute(
            select(PriceSnapshot, HardwareItem.name)
            .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
            .where(
                PriceSnapshot.hardware_id == hardware.id,
                PriceSnapshot.snapshot_date == today,
            )
            .order_by(PriceSnapshot.id)
        )
        validation_rows = result.all()
        _print_validation_rows(validation_rows)

        validation_summary = await validate_snapshot_rows_sequential(
            session,
            validation_rows,
            commit_each=True,
            debug_hook=_llm_debug_printer if args.verbose_llm else None,
        )

        stats = await compute_daily_stats(session, hardware, today)
        await session.commit()

        print("Rerun finished.")
        print(f"Hardware: {hardware.name}")
        print(f"Date: {today.isoformat()}")
        print(f"Search keywords: {search_keywords}")
        print(f"Pages: {args.pages}")
        print(f"Raw crawled: {len(raw_items)}")
        print(f"Saved snapshots: {saved}")
        print(
            "Validation summary: "
            f"validated={validation_summary['validated']} "
            f"valid={validation_summary['valid']} "
            f"invalid={validation_summary['invalid']} "
            f"failed={validation_summary['failed']}"
        )
        if stats is None:
            print("Aggregation: no valid samples, daily_stats removed or not created")
        else:
            print(
                "Aggregation: "
                f"median={stats.median_price:.0f} "
                f"avg={stats.avg_price:.0f} "
                f"samples={stats.sample_count} "
                f"level={stats.price_level.value}"
            )


if __name__ == "__main__":
    asyncio.run(main())
