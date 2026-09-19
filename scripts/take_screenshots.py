import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Desktop
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        print("Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000")
        
        # Wait for the page to load
        await page.wait_for_timeout(2000)
        
        print("Capturing desktop hero...")
        await page.screenshot(path="docs/hero-desktop.png", full_page=False)
        
        # Mobile
        print("Capturing mobile view...")
        iphone_context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
        )
        mobile_page = await iphone_context.new_page()
        await mobile_page.goto("http://localhost:8000")
        await mobile_page.wait_for_timeout(2000)
        await mobile_page.screenshot(path="docs/mobile-view.png", full_page=False)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
