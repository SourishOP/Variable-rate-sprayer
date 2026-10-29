"""Take real screenshots of the running PaddyGuard web application.

Start the server first:  venv_ml python app/server.py   (port 5000)
Then run this script with the same environment.
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "report", "figures")
URL = "http://127.0.0.1:5000"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def upload_and_wait(page, path):
    page.set_input_files("#file", path)
    page.wait_for_function("document.querySelector('#verdictArea').innerText.trim().length > 20",
                           timeout=120000)
    page.wait_for_timeout(7000)  # let the animations finish


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE, headless=True)
        page = browser.new_page(viewport={"width": 1360, "height": 900}, device_scale_factor=1.5)
        page.goto(URL)
        page.wait_for_timeout(2500)
        page.screenshot(path=os.path.join(OUT, "ui_home.png"), full_page=False)

        first = os.path.join(ROOT, "data", "sample_images", "Brown_Spot", "Brown_Spot_09.jpg")
        upload_and_wait(page, first)
        page.screenshot(path=os.path.join(OUT, "ui_result_brown_spot.png"), full_page=True)

        second = os.path.join(ROOT, "data", "sample_images", "Neck Blast", "Neck_Blast_04.jpg")
        page.click('.tab[data-page="analyze"]')
        upload_and_wait(page, second)
        page.screenshot(path=os.path.join(OUT, "ui_result_neck_blast.png"), full_page=True)

        page.click('.tab[data-page="history"]')
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(OUT, "ui_history.png"), full_page=False)

        page.click('.tab[data-page="about"]')
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUT, "ui_about.png"), full_page=False)
        browser.close()
    print("screenshots saved to", OUT)


if __name__ == "__main__":
    main()
