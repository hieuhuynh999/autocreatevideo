"""Mở Chrome, đăng nhập Google, vào YouTube Studio, bấm Tổng quan rồi Tải video lên.

Hồ sơ Chrome nằm trong output/chrome-youtube nên lần sau còn đăng nhập.
Email và mật khẩu đọc từ .env. Không in mật khẩu, không chọn file, không bấm Đăng.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "output" / "chrome-youtube"
CHANNEL_ID = "UCE056WfiFMV6k4N5irnIDnA"
STUDIO = f"https://studio.youtube.com/channel/{CHANNEL_ID}"
HOME = "https://www.youtube.com/"
OVERVIEW = re.compile(r"tổng quan|overview", re.I)
UPLOAD = re.compile(r"tải video lên|upload videos?", re.I)


def _open_chrome():
    from playwright.sync_api import sync_playwright

    PROFILE.mkdir(parents=True, exist_ok=True)
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        str(PROFILE),
        channel="chrome",
        headless=False,
        locale="vi-VN",
        viewport={"width": 1440, "height": 900},
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    return playwright, context, page


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = ROOT / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _wait_for_login(page) -> None:
    page.wait_for_timeout(800)
    sign_in = page.get_by_role("link", name=re.compile(r"^sign in$|^đăng nhập$", re.I))
    if "accounts.google.com" not in page.url and sign_in.count() and sign_in.first.is_visible():
        sign_in.first.click(timeout=10_000)
        page.wait_for_timeout(1000)
    if "accounts.google.com" not in page.url:
        return
    email = _env("YOUTUBE_GOOGLE_EMAIL")
    password = _env("YOUTUBE_GOOGLE_PASSWORD")
    if not email or not password:
        print("Chrome đang ở trang Google. Hãy đăng nhập trong cửa sổ đó.")
    else:
        print(f"Đăng nhập Google bằng {email}. Không in mật khẩu.")
        mail = page.locator('input[type="email"]')
        if mail.count() and mail.first.is_visible():
            mail.first.fill(email)
            page.locator("#identifierNext").click(timeout=10_000)
        page.locator('input[type="password"]').first.wait_for(state="visible", timeout=30_000)
        page.locator('input[type="password"]').first.fill(password)
        page.locator("#passwordNext").click(timeout=10_000)
    try:
        page.wait_for_function(
            "() => !location.href.includes('accounts.google.com')",
            timeout=180_000,
        )
    except Exception as exc:
        raise RuntimeError(
            "Google chưa vào được YouTube. Nếu có mã điện thoại hoặc captcha, hãy bấm trong cửa sổ Chrome."
        ) from exc


def _click_overview(page) -> None:
    drawer = page.locator("ytcp-navigation-drawer, #left-nav, tp-yt-app-drawer").first
    link = drawer.get_by_role("link", name=OVERVIEW)
    if link.count() == 0:
        link = page.get_by_role("link", name=OVERVIEW)
    link.first.click(timeout=20_000)
    page.wait_for_load_state("domcontentloaded")


def _click_first_visible(locator) -> bool:
    count = min(locator.count(), 6)
    for index in range(count):
        item = locator.nth(index)
        if item.is_visible():
            item.click(timeout=10_000)
            return True
    return False


def _click_upload(page) -> None:
    named = page.get_by_role("button", name=UPLOAD).or_(page.get_by_role("link", name=UPLOAD))
    if _click_first_visible(named):
        return
    create = page.get_by_role("button", name=re.compile(r"^tạo$|^create$", re.I))
    if not _click_first_visible(create):
        create.first.click(timeout=10_000)
    page.get_by_role("menuitem", name=UPLOAD).first.click(timeout=10_000)


def _upload_is_open(page) -> bool:
    if "/videos/upload" in page.url:
        return True
    dialog = page.get_by_text(re.compile(r"chọn tệp|select files", re.I))
    return dialog.count() > 0


def main() -> int:
    playwright, context, page = _open_chrome()
    try:
        page.goto(HOME, wait_until="domcontentloaded")
        _wait_for_login(page)
        print("Đã mở trang chủ YouTube.")
        page.goto(STUDIO, wait_until="domcontentloaded")
        _wait_for_login(page)
        page.wait_for_url(re.compile(rf"studio\.youtube\.com/channel/{CHANNEL_ID}"), timeout=60_000)
        print("Đã vào kênh trong YouTube Studio.")
        _click_overview(page)
        print("Đã bấm Tổng quan.")
        _click_upload(page)
        page.wait_for_timeout(1500)
        if not _upload_is_open(page):
            raise RuntimeError("Chưa thấy màn hình tải video lên.")
        print("Đã bấm Tải video lên. Chưa chọn file và chưa bấm Đăng.")
        print("Đóng cửa sổ Chrome khi xem xong.")
        while context.pages:
            try:
                page.wait_for_timeout(1000)
            except Exception:
                break
    finally:
        context.close()
        playwright.stop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise
