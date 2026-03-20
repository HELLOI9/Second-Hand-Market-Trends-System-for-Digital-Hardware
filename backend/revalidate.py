"""
Revalidate historical price snapshots with the local LLM.

Examples:
    python revalidate_snapshots.py --hardware-name "RTX 4090" --date 2026-03-19
    python revalidate_snapshots.py --hardware-id 12 --date 2026-03-19 --force
    python revalidate_snapshots.py --hardware-name "RTX 4090" --limit 50 --skip-stats
"""

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models import HardwareItem, PriceSnapshot
from app.services.llm_validator import validate_snapshot_record
from app.services.stats import compute_daily_stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use LLM to revalidate historical price_snapshots with optional filters.",
    )
    parser.add_argument("--hardware-id", type=int, help="hardware_items.id")
    parser.add_argument("--hardware-name", help="hardware_items.name, case-insensitive exact match")
    parser.add_argument("--date", type=date.fromisoformat, help="Snapshot date in YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="Max number of snapshots to validate")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Revalidate already validated rows too; default only processes is_valid IS NULL",
    )
    parser.add_argument(
        "--skip-stats",
        action="store_true",
        help="Do not recompute daily_stats after validation",
    )
    parser.add_argument(
        "--verbose-llm",
        action="store_true",
        help="Print full LLM request/response JSON for each processed snapshot",
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


async def _resolve_hardware_id(session, hardware_id: int | None, hardware_name: str | None) -> tuple[int | None, str | None]:
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
        return item.id, item.name

    if hardware_id is not None:
        item = await session.get(HardwareItem, hardware_id)
        if item is None:
            raise ValueError(f"Hardware id not found: {hardware_id}")
        return item.id, item.name

    if hardware_name is not None:
        result = await session.execute(
            select(HardwareItem).where(HardwareItem.name.ilike(hardware_name))
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise ValueError(f"Hardware name not found: {hardware_name}")
        return item.id, item.name

    return None, None


async def _collect_affected_groups(
    session,
    hardware_id: int | None,
    snapshot_date: date | None,
    *,
    only_unvalidated: bool,
    limit: int | None,
) -> list[tuple[int, date]]:
    stmt = select(PriceSnapshot.hardware_id, PriceSnapshot.snapshot_date)
    if hardware_id is not None:
        stmt = stmt.where(PriceSnapshot.hardware_id == hardware_id)
    if snapshot_date is not None:
        stmt = stmt.where(PriceSnapshot.snapshot_date == snapshot_date)
    if only_unvalidated:
        stmt = stmt.where(PriceSnapshot.is_valid.is_(None))
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt.distinct())
    return [(row.hardware_id, row.snapshot_date) for row in result]


async def _load_snapshots(
    session,
    hardware_id: int | None,
    snapshot_date: date | None,
    *,
    only_unvalidated: bool,
    limit: int | None,
) -> list[PriceSnapshot]:
    stmt = (
        select(PriceSnapshot)
        .options(selectinload(PriceSnapshot.hardware))
        .order_by(PriceSnapshot.snapshot_date, PriceSnapshot.id)
    )
    if hardware_id is not None:
        stmt = stmt.where(PriceSnapshot.hardware_id == hardware_id)
    if snapshot_date is not None:
        stmt = stmt.where(PriceSnapshot.snapshot_date == snapshot_date)
    if only_unvalidated:
        stmt = stmt.where(PriceSnapshot.is_valid.is_(None))
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _recompute_stats(session, groups: list[tuple[int, date]]) -> dict[str, int]:
    summary = defaultdict(int)

    for hardware_id, stat_date in groups:
        hardware = await session.get(HardwareItem, hardware_id)
        if hardware is None:
            summary["missing_hardware"] += 1
            continue

        stats = await compute_daily_stats(session, hardware, stat_date)
        if stats is None:
            summary["empty"] += 1
        else:
            summary["updated"] += 1

    return dict(summary)


async def main() -> None:
    args = _parse_args()

    async with AsyncSessionLocal() as session:
        resolved_hardware_id, resolved_hardware_name = await _resolve_hardware_id(
            session,
            args.hardware_id,
            args.hardware_name,
        )

        snapshots = await _load_snapshots(
            session,
            resolved_hardware_id,
            args.date,
            only_unvalidated=not args.force,
            limit=args.limit,
        )

        affected_groups = sorted({(snapshot.hardware_id, snapshot.snapshot_date) for snapshot in snapshots})

        validation_summary = {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}
        for index, snapshot in enumerate(snapshots, start=1):
            hardware_name = snapshot.hardware.name if snapshot.hardware else f"hardware_id={snapshot.hardware_id}"
            print(
                f"\n[{index}/{len(snapshots)}] validating snapshot_id={snapshot.id} "
                f"hardware={hardware_name} date={snapshot.snapshot_date} price={snapshot.price}"
            )

            row_summary = await validate_snapshot_record(
                session,
                snapshot,
                hardware_name,
                commit=True,
                debug_hook=_llm_debug_printer if args.verbose_llm else None,
            )

            for key in validation_summary:
                validation_summary[key] += row_summary[key]

            print(
                "result: "
                f"validated={row_summary['validated']} "
                f"valid={row_summary['valid']} "
                f"invalid={row_summary['invalid']} "
                f"failed={row_summary['failed']} "
                f"is_valid={snapshot.is_valid} "
                f"reason={snapshot.validation_reason}"
            )

        stats_summary: dict[str, int] | None = None
        if not args.skip_stats and affected_groups:
            stats_summary = await _recompute_stats(session, affected_groups)

        await session.commit()

    print("Revalidation finished.")
    print(f"Hardware: {resolved_hardware_name or 'ALL'}")
    print(f"Date: {args.date.isoformat() if args.date else 'ALL'}")
    print(f"Mode: {'force' if args.force else 'only_unvalidated'}")
    print(f"Limit: {args.limit if args.limit is not None else 'NONE'}")
    print(
        "Validation summary: "
        f"validated={validation_summary['validated']} "
        f"valid={validation_summary['valid']} "
        f"invalid={validation_summary['invalid']} "
        f"failed={validation_summary['failed']}"
    )
    if args.skip_stats:
        print("Stats recompute: skipped")
    else:
        print(f"Stats recompute: {stats_summary or {'updated': 0}}")


if __name__ == "__main__":
    asyncio.run(main())
