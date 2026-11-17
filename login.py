"""One-time login. Opens Chrome with a saved profile. Log in to YouTube, then close the window."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://studio.youtube.com")
    print("Log in, wait until you see YouTube Studio, then close the browser window.")
    try:
        page.wait_for_event("close", timeout=0)
    except Exception:
        pass
    ctx.close()
