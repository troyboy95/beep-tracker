"""Capture proof screenshots of the live site and public GitHub Actions pages → eval/proofs/*.png

Needs Playwright + a local Edge/Chrome:  pip install playwright
Run:  python eval/proof_screenshots.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "proofs"
SITE = "https://beep-tracker.vercel.app"
REPO = "https://github.com/troyboy95/beep-tracker"
SHOTS = [
    # (file, url, viewport height, wait-for selector)
    ("site-city-pune.png", f"{SITE}/?city=Pune", 1000, "text=/of \\d+ openings/"),
    ("actions-pipeline-runs.png", f"{REPO}/actions/workflows/pipeline.yml", 900, "text=pipeline"),
]

OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme="light")
    for name, url, height, wait in SHOTS:
        page.set_viewport_size({"width": 1280, "height": height})
        # "load", not "networkidle": GitHub keeps long-lived connections open.
        page.goto(url, wait_until="load", timeout=60000)
        try:
            page.wait_for_selector(wait, timeout=15000)
        except Exception as e:  # noqa: BLE001 — still capture what loaded
            print(f"  ! {name}: wait for {wait!r} timed out ({type(e).__name__})")
        page.screenshot(path=str(OUT / name))
        print("saved", name)
    browser.close()
