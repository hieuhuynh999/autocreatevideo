"""Đăng thử video nhà lên đúng kênh YouTube Studio.

Chọn file, điền tiêu đề, mô tả, hashtag, đánh dấu không dành cho trẻ em,
rồi bấm Đăng ở chế độ công khai. Không đọc mật khẩu ra màn hình.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mo_studio

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "output" / "us-daily" / "2026-11-05" / "nha.mp4"
TITLE = "A 7.18% mortgage adds about $191 a month on a $300,000 loan"
DESCRIPTION = """You did not search for a dream house. You searched for the price of the loan.

Freddie Mac, November 5, 2026: the average 30-year fixed rate was 7.18%. One year earlier the same survey was 6.22%.

On one example, a $300,000 loan for 30 years, principal and interest only, the monthly bill is about $1,841 at 6.22% and about $2,032 at 7.18%. The gap is about $191 a month. Taxes, insurance, and credit are not in that sketch.

Redfin, four weeks ending October 25, 2026, via Newsweek: median sale price $389,601, down 0.1% from a year earlier. Median mortgage payment $2,786, up 10.7%. Apartment List, October 2026: national median rent $1,384. These national numbers are not the same front door.

In March 2026 the New York Post reported that Google searches for "help with mortgage" passed the 2008 line. Investopedia noted the count is not comparable to 2008, and the share of single-family mortgages that were late was under 2% in the second quarter of 2025, versus above 11% in 2010.

This is not personal financial advice.

#PersonalFinance #Mortgage #Housing #CostOfLiving #USFinance
""".strip()
SHOT = ROOT / "output" / "us-daily" / "2026-11-05" / "studio-dang.jpg"


def _fill_box(page, box_id: str, text: str) -> None:
    box = page.locator(f"#{box_id} #textbox")
    box.first.click(timeout=20_000)
    box.first.fill(text)


def _mark_not_for_kids(page) -> None:
    radio = page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
    if radio.count():
        radio.first.click(timeout=10_000)
        return
    page.get_by_text(re.compile(r"không dành cho trẻ em|not made for kids", re.I)).first.click(timeout=10_000)


def _click_when_enabled(page, selector: str) -> None:
    button = page.locator(selector).first
    button.wait_for(state="visible", timeout=30_000)
    for _ in range(60):
        disabled = button.get_attribute("aria-disabled")
        if disabled not in {"true", "True"}:
            button.click(timeout=10_000)
            return
        page.wait_for_timeout(1000)
    raise RuntimeError(f"Nút {selector} vẫn bị khóa.")


def _publish(page) -> str:
    page.locator("input[type=file]").first.set_input_files(str(VIDEO))
    print("Đã chọn file video.")
    page.locator("#title-textarea #textbox").first.wait_for(state="visible", timeout=60_000)
    _fill_box(page, "title-textarea", TITLE)
    _fill_box(page, "description-textarea", DESCRIPTION)
    _mark_not_for_kids(page)
    print("Đã điền tiêu đề, mô tả và hashtag.")
    for step in range(3):
        _click_when_enabled(page, "#next-button")
        page.wait_for_timeout(800)
        print(f"Đã bấm Tiếp, bước {step + 1}.")
    public = page.locator('tp-yt-paper-radio-button[name="PUBLIC"]')
    if public.count() == 0:
        public = page.get_by_text(re.compile(r"^công khai$|^public$", re.I))
    public.first.click(timeout=10_000)
    _click_when_enabled(page, "#done-button")
    print("Đã bấm Đăng.")
    # "Video đã xử lý xong" thường nằm trong tooltip ẩn, không hiện trên màn hình.
    page.get_by_text(re.compile(r"đã đăng|video published|đã xử lý", re.I)).first.wait_for(
        state="attached", timeout=120_000
    )
    link = page.locator("a[href*='youtu']").first
    href = link.get_attribute("href") if link.count() else ""
    return href or page.url


def main() -> int:
    if not VIDEO.exists():
        raise RuntimeError(f"Không thấy {VIDEO}")
    playwright, context, page = mo_studio._open_chrome()
    try:
        page.goto(mo_studio.HOME, wait_until="domcontentloaded")
        mo_studio._wait_for_login(page)
        page.goto(mo_studio.STUDIO, wait_until="domcontentloaded")
        mo_studio._wait_for_login(page)
        page.wait_for_url(re.compile(rf"studio\.youtube\.com/channel/{mo_studio.CHANNEL_ID}"), timeout=60_000)
        mo_studio._click_overview(page)
        mo_studio._click_upload(page)
        page.wait_for_timeout(1000)
        if not mo_studio._upload_is_open(page):
            raise RuntimeError("Chưa thấy màn hình tải video lên.")
        link = _publish(page)
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT), full_page=True)
        print(f"Đã đăng: {link}")
        print(SHOT)
    except Exception:
        try:
            SHOT.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SHOT), full_page=True)
            print(f"Đã chụp màn hình lỗi: {SHOT}")
        except Exception:
            pass
        raise
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
