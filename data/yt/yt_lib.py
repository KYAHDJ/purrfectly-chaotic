"""Helpers to drive YouTube Studio with the saved login (profile/). Close any Chrome using profile/ first."""
import re
from playwright.sync_api import sync_playwright
def open_studio(p):
    ctx = p.chromium.launch_persistent_context("profile", channel="chrome", headless=False,
        ignore_default_args=["--enable-automation"], args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900})
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://studio.youtube.com", wait_until="domcontentloaded")
    pg.wait_for_url(re.compile(r"/channel/UC"), timeout=40000); pg.wait_for_timeout(4000)
    return ctx, pg
