"""
Manual crawl tester — run with:
    python test_crawl.py "i7 14700KF"
    python test_crawl.py "RTX 4090" --pages 2
"""
import asyncio
import sys
import argparse
from app.crawler.xianyu import crawl_keyword


async def main(keyword: str, pages: int):
    print(f"\nCrawling: [{keyword}]  max_pages={pages}\n")
    items = await crawl_keyword(keyword, max_pages=pages)

    if not items:
        print("No items captured.")
        return

    print(f"Captured {len(items)} items:\n")
    print(f"{'#':<4} {'Price':>8}  {'Title':<50}  Area")
    print("-" * 80)
    for i, item in enumerate(items, 1):
        title = item.title[:48] if item.title else "-"
        area = item.area or "-"
        print(f"{i:<4} {item.price:>8.0f}  {title:<50}  {area}")

    prices = [item.price for item in items]
    print(f"\nMin: {min(prices):.0f}  Max: {max(prices):.0f}  "
          f"Avg: {sum(prices)/len(prices):.0f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", help="Search keyword")
    parser.add_argument("--pages", type=int, default=1, help="Max pages (default 1)")
    args = parser.parse_args()
    asyncio.run(main(args.keyword, args.pages))
