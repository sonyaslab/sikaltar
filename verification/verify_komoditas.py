from playwright.sync_api import sync_playwright
import os

def run_cuj(page):
    # Navigate to the new Master Data Komoditas page
    page.goto("http://localhost:8000/app/admin/master/komoditas.html")
    page.wait_for_timeout(3000)

    # 1. Expand a category
    page.locator(".toggle-icon").first.click()
    page.wait_for_timeout(1000)
    page.locator(".row-l2 .toggle-icon").first.click()
    page.wait_for_timeout(1000)
    page.locator(".row-l3 .toggle-icon").first.click()
    page.wait_for_timeout(1000)

    # 2. Screenshot
    page.screenshot(path="verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
