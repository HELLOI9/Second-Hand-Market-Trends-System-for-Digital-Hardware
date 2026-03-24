"""
Goofish crawler — based on spider.py (Firefox + mtop API interception)

Strategy:
1. Launch Playwright Firefox (headless) with login cookies
2. Navigate to goofish homepage, fill search box, submit
3. Intercept mtop.taobao.idlemtopsearch.pc.search XHR responses
4. Parse item list and return RawItem list for the service layer
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page, Response, BrowserContext

logger = logging.getLogger(__name__)

COOKIE_FILE = Path(__file__).parent.parent.parent / "cookies.json"
SEARCH_API_URL = "h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search"


@dataclass
class RawItem:
    title: str
    price: float
    item_url: str | None = None
    area: str | None = None
    seller: str | None = None
    image_url: str | None = None
    publish_time: datetime | None = None


# ── Cookie helpers ────────────────────────────────────────────


def _load_cookies() -> list[dict]:
    if not COOKIE_FILE.exists():
        logger.warning("cookies.json not found — running without login")
        return []
    try:
        data = json.loads(COOKIE_FILE.read_text())
        logger.info("Loaded %d cookies", len(data))
        return data
    except Exception as e:
        logger.error("Failed to parse cookies.json: %s", e)
        return []


def _normalize_cookies(raw: list[dict]) -> list[dict]:
    out = []
    for c in raw:
        cookie: dict[str, Any] = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".goofish.com"),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", c.get("http_only", False)),
        }
        expiry = c.get("expirationDate") or c.get("expires") or c.get("expiry")
        if expiry and isinstance(expiry, (int, float)) and expiry > 0:
            cookie["expires"] = int(expiry)
        same_site = c.get("sameSite") or c.get("same_site") or "Lax"
        if same_site not in ("Strict", "Lax", "None"):
            same_site = "Lax"
        cookie["sameSite"] = same_site
        out.append(cookie)
    return out


# ── Response parsing ──────────────────────────────────────────


async def _safe_get(data: Any, *keys: str, default: Any = "暂无") -> Any:
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


async def _parse_response(response: Response) -> list[RawItem]:
    """Extract RawItems from a mtop search API response."""
    if SEARCH_API_URL not in response.url:
        return []
    try:
        result_json = await response.json()
        items = result_json.get("data", {}).get("resultList", [])
        results = []
        for item in items:
            raw = await _parse_item(item)
            if raw:
                results.append(raw)
        return results
    except Exception as e:
        logger.debug("Response parse error: %s", e)
        return []


async def _parse_item(item: dict) -> RawItem | None:
    try:
        main_data = await _safe_get(item, "data", "item", "main", "exContent", default={})
        click_params = await _safe_get(item, "data", "item", "main", "clickParam", "args", default={})

        title = await _safe_get(main_data, "title", default="")
        if not title:
            return None

        # Price is a list of text parts e.g. [{"text": "¥"}, {"text": "1200"}]
        price_parts = await _safe_get(main_data, "price", default=[])
        price_str = ""
        if isinstance(price_parts, list):
            price_str = "".join(str(p.get("text", "")) for p in price_parts if isinstance(p, dict))
            price_str = price_str.replace("当前价", "").strip()
            if "万" in price_str:
                num = re.sub(r"[^\d.]", "", price_str.replace("万", ""))
                price_str = str(float(num) * 10000) if num else ""

        price_clean = re.sub(r"[^\d.]", "", price_str)
        if not price_clean:
            return None
        price = float(price_clean)

        area = await _safe_get(main_data, "area", default=None)
        seller = await _safe_get(main_data, "userNickName", default=None)

        raw_link = await _safe_get(item, "data", "item", "main", "targetUrl", default="")
        item_url = raw_link.replace("fleamarket://", "https://www.goofish.com/") if raw_link else None

        image_url = await _safe_get(main_data, "picUrl", default=None)
        if image_url and not str(image_url).startswith("http"):
            image_url = f"https:{image_url}"

        publish_time = None
        ts = click_params.get("publishTime", "")
        if ts and str(ts).isdigit():
            try:
                publish_time = datetime.fromtimestamp(int(ts) / 1000)
            except Exception:
                pass

        return RawItem(
            title=str(title),
            price=price,
            item_url=item_url,
            area=str(area) if area and area != "暂无" else None,
            seller=str(seller) if seller and seller != "暂无" else None,
            image_url=str(image_url) if image_url else None,
            publish_time=publish_time,
        )
    except Exception as e:
        logger.debug("Item parse error: %s", e)
        return None


# ── Main crawl function ───────────────────────────────────────


async def _wait_for_search_hit(
    get_hit_count,
    previous_count: int,
    timeout: float = 15.0,
) -> bool:
    """Wait until a new search API response has been captured."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if get_hit_count() > previous_count:
            return True
        await asyncio.sleep(0.2)
    return False


async def _click_next_page(page: Page) -> bool:
    """
    Try several selectors because goofish pagination DOM is not stable.
    Returns True if a next-page control was clicked.
    """
    selectors = [
        "[class*='search-pagination-arrow-right']:not([disabled])",
        "button[class*='arrow-right']:not([disabled])",
        "button[aria-label*='下一页']:not([disabled])",
        "button:has-text('下一页'):not([disabled])",
        "div[role='button']:has-text('下一页')",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            await locator.scroll_into_view_if_needed(timeout=3000)
            await locator.click(timeout=5000)
            return True
        except Exception:
            continue

    return False


async def crawl_keyword(keyword: str, max_pages: int = 3) -> list[RawItem]:
    """
    Crawl goofish search results for a keyword using Firefox.
    Requires cookies.json for authenticated access.
    """
    results: list[RawItem] = []
    cookies = _load_cookies()

    proxy_url = os.environ.get("https_proxy") or os.environ.get("http_proxy")
    proxy = {"server": proxy_url} if proxy_url else None
    search_hit_count = 0

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=True,
            proxy=proxy,
        )
        context: BrowserContext = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        if cookies:
            await context.add_cookies(_normalize_cookies(cookies))

        page: Page = await context.new_page()

        async def on_response(response: Response) -> None:
            nonlocal search_hit_count
            items = await _parse_response(response)
            if items:
                search_hit_count += 1
                results.extend(items)
                logger.debug("Captured %d items from page, hit=%d", len(items), search_hit_count)

        page.on("response", on_response)

        try:
            await page.goto("https://www.goofish.com", wait_until="networkidle", timeout=30_000)

            # Dismiss login modal if present
            try:
                await page.wait_for_selector("[class*='login-modal-wrap']", timeout=5000)
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
            except Exception:
                pass

            await page.fill('input[class*="search-input"]', keyword)
            await page.click('button[type="submit"]')

            # Wait for search results XHR to complete (page 1)
            if not await _wait_for_search_hit(lambda: search_hit_count, 0, timeout=20.0):
                logger.warning("Search API did not return page 1 for [%s]", keyword)
            await page.wait_for_load_state("networkidle", timeout=20_000)

            # Dismiss ad popup if present
            try:
                await page.wait_for_selector("div[class*='closeIconBg']", timeout=3000)
                await page.click("div[class*='closeIconBg']")
            except Exception:
                pass

            logger.info("Crawling [%s] page 1", keyword)

            # Pages 2..max_pages
            for page_num in range(2, max_pages + 1):
                previous_hits = search_hit_count
                if not await _click_next_page(page):
                    logger.info("No usable next-page control found for [%s] at page %d", keyword, page_num - 1)
                    break
                if not await _wait_for_search_hit(lambda: search_hit_count, previous_hits, timeout=15.0):
                    logger.info("No new search response after clicking next for [%s] page %d", keyword, page_num)
                    break
                await page.wait_for_load_state("networkidle", timeout=15_000)
                logger.info("Crawling [%s] page %d", keyword, page_num)

        except Exception as e:
            logger.warning("Error crawling [%s]: %s", keyword, e)
        finally:
            await browser.close()

    logger.info("Keyword [%s]: collected %d raw records", keyword, len(results))
    return results
