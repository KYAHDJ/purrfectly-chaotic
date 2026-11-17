"""Open the signed-in channel browser for manual use. Stays open until you close the window."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False, no_viewport=True,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://studio.youtube.com")
    try:
        ctx.wait_for_event("close", timeout=0)
    except Exception:
        pass
