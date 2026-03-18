"""
Step-by-step crawler debugger.
Run: python debug_crawler.py "RTX 4090"
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

COOKIE_FILE = Path(__file__).parent / "cookies.json"
SEARCH_API = "mtop.taobao.idlemtopsearch.pc.search"


def load_cookies():
    if not COOKIE_FILE.exists():
        print("[WARN] cookies.json not found")
        return []
    data = json.loads(COOKIE_FILE.read_text())
    print(f"[OK]   Loaded {len(data)} cookies")
    return data


def normalize_cookies(raw):
    out = []
    for c in raw:
        cookie = {
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
        same_site = c.get("sameSite") or "Lax"
        if same_site not in ("Strict", "Lax", "None"):
            same_site = "Lax"
        cookie["sameSite"] = same_site
        out.append(cookie)
    return out


async def main(keyword: str):
    cookies = load_cookies()
    proxy_url = os.environ.get("https_proxy") or os.environ.get("http_proxy")
    proxy = {"server": proxy_url} if proxy_url else None
    print(f"[OK]   Proxy: {proxy_url or 'none'}")

    all_responses = []
    search_hits = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True, proxy=proxy)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        if cookies:
            await context.add_cookies(normalize_cookies(cookies))

        page = await context.new_page()

        async def on_response(resp):
            url = resp.url
            all_responses.append(url)
            # Only match the exact search endpoint, not shade/activate variants
            if SEARCH_API not in url or "shade" in url or "activate" in url:
                return
            try:
                body = await resp.json()
                items = body.get("data", {}).get("resultList", [])
                entry = {"url": url, "count": len(items), "body": body}
                search_hits.append(entry)
                print(f"[HIT]  Search API — resultList count={len(items)}  ret={body.get('ret')}")
                # Print full body for the first hit so we can see the real structure
                if len(search_hits) == 1:
                    print("\n      === First search response (full) ===")
                    print(json.dumps(body, ensure_ascii=False, indent=2)[:3000])
                    print("      =====================================\n")
            except Exception as e:
                search_hits.append({"url": url, "error": str(e)})
                print(f"[ERR]  Search API parse failed: {e}")

        page.on("response", on_response)

        # Step 1: load homepage
        print("\n[1/5] Loading goofish homepage...")
        try:
            await page.goto("https://www.goofish.com", wait_until="networkidle", timeout=30_000)
            print(f"      URL: {page.url}")
            print(f"      Title: {await page.title()}")
        except Exception as e:
            print(f"[ERR]  Homepage failed: {e}")
            await browser.close()
            return

        # Step 2: dismiss login modal
        print("\n[2/5] Checking for login modal...")
        try:
            await page.wait_for_selector("[class*='login-modal-wrap']", timeout=4000)
            await page.keyboard.press("Escape")
            print("      Login modal dismissed")
        except Exception:
            print("      No login modal (good)")

        # Step 3: fill search box
        print(f"\n[3/5] Filling search box with: {keyword!r}")
        try:
            search_input = await page.wait_for_selector('input[class*="search-input"]', timeout=10_000)
            await search_input.fill(keyword)
            print(f"      Input filled OK")
        except Exception as e:
            print(f"[ERR]  Cannot find search input: {e}")
            # Print all input elements on the page
            inputs = await page.query_selector_all("input")
            print(f"      Found {len(inputs)} input elements on page:")
            for inp in inputs[:5]:
                cls = await inp.get_attribute("class") or ""
                ph = await inp.get_attribute("placeholder") or ""
                print(f"        class={cls[:60]}  placeholder={ph}")
            await browser.close()
            return

        # Step 4: submit
        print("\n[4/5] Submitting search...")
        try:
            await page.click('button[type="submit"]')
            print("      Clicked submit, waiting for networkidle...")
            await page.wait_for_load_state("networkidle", timeout=20_000)
            print(f"      Done. URL: {page.url}")
            print(f"      Title: {await page.title()}")
        except Exception as e:
            print(f"[WARN] networkidle timeout or error: {e}")
            print(f"      Current URL: {page.url}")

        # Step 5: results
        print(f"\n[5/5] Results:")
        print(f"      Total responses intercepted: {len(all_responses)}")
        print(f"      Search API hits: {len(search_hits)}")

        if search_hits:
            for hit in search_hits:
                if "error" in hit:
                    print(f"      [ERR] {hit['error']}")
                else:
                    print(f"      Items in resultList: {hit['count']}")
                    if hit["count"] > 0:
                        first = hit["body"]["data"]["resultList"][0]
                        print(f"      First item keys: {list(first.keys())}")
                        print(f"\n      Sample (first item):")
                        print(json.dumps(first, ensure_ascii=False, indent=2)[:1500])
        else:
            print("\n      [WARN] Search API never fired. URLs intercepted:")
            for url in all_responses[-20:]:
                print(f"        {url[:120]}")

        await browser.close()


if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "RTX 4090"
    asyncio.run(main(keyword))
