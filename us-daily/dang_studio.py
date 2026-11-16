"""Đăng video bằng Chrome và YouTube Studio, đúng các bước bấm tay.

1. Mở Chrome với hồ sơ đã lưu.
2. Mở trang chủ YouTube.
3. Nếu chưa đăng nhập, điền email và mật khẩu trong .env. Không in mật khẩu.
4. Mở Studio của kênh.
5. Bấm Tổng quan.
6. Bấm Tải video lên.
7. Chọn file.
8. Điền tiêu đề, mô tả, hashtag.
9. Chọn Không dành cho trẻ em.
10. Bấm Tiếp ba lần.
11. Chọn Lên lịch, đặt giờ Việt Nam tương ứng giờ miền Đông.
12. Bấm Đăng. Lặp lại từ bước 6 cho video sau.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dang_nha
import mo_studio

VN = ZoneInfo("Asia/Ho_Chi_Minh")
ROOT = Path(__file__).resolve().parents[1]


def _schedule(page, stamp: str) -> None:
    when = datetime.fromisoformat(stamp)
    if when.tzinfo is None:
        when = when.replace(tzinfo=VN)
    local = when.astimezone(VN)
    # Studio không nhận giờ đã qua. Dựng trễ thì lùi tới mốc 15 phút kế tiếp.
    earliest = datetime.now(VN) + timedelta(minutes=20)
    if local < earliest:
        bump = earliest.replace(second=0, microsecond=0)
        local = bump + timedelta(minutes=(15 - bump.minute % 15) % 15)
    # Chờ bước Visibility. Short mới tải lên đôi khi còn đang kiểm tra.
    page.get_by_text(re.compile(r"chế độ hiển thị|visibility|lưu hoặc xuất bản|save or publish", re.I)).first.wait_for(
        state="visible", timeout=60_000
    )
    _open_schedule(page)
    page.locator("#datepicker-trigger").first.wait_for(state="visible", timeout=30_000)
    _pick_date(page, local)
    _pick_time(page, local)
    _dismiss_popups(page)
    print(f"Đã đặt lịch {local.strftime('%d/%m/%Y %H:%M')} giờ Việt Nam.")


def _open_schedule(page) -> None:
    """Bật chế độ Lên lịch. Short có thể còn đang kiểm tra và radio nằm dưới vùng cuộn."""
    try:
        page.get_by_text(re.compile(r"đã kiểm tra xong|checks complete|no issues found", re.I)).first.wait_for(
            state="visible", timeout=45_000
        )
    except Exception:
        print("Chưa thấy dòng kiểm tra xong; vẫn thử lên lịch.")
    # Cuộn trong hộp tải lên để thấy hàng Lên lịch.
    for box in page.locator("#scrollable-content, ytcp-uploads-dialog #dialog-content, #left-button-section").all():
        try:
            box.evaluate("el => { el.scrollTop = el.scrollHeight; }")
        except Exception:
            pass
    page.wait_for_timeout(400)
    candidates = [
        page.locator('tp-yt-paper-radio-button[name="SCHEDULE"]'),
        page.locator("#second-container-radio-button"),
        page.locator("#schedule-radio-button"),
        page.locator("ytcp-visibility-selector tp-yt-paper-radio-button").nth(3),
    ]
    last_error: Exception | None = None
    for candidate in candidates:
        if candidate.count() == 0:
            continue
        target = candidate.first
        try:
            target.click(timeout=8_000, force=True)
            page.wait_for_timeout(800)
            if page.locator("#datepicker-trigger").count():
                return
        except Exception as exc:
            last_error = exc
            continue
    # Không dùng get_by_text("Lên lịch"): dễ trùng nút Đăng ở góc dưới.
    raise RuntimeError(f"Không bật được chế độ Lên lịch: {last_error}")


def _dismiss_popups(page) -> None:
    for _ in range(3):
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    heading = page.locator("#visibility-title, ytcp-uploads-review h1, #second-container-radio-button").first
    if heading.count():
        try:
            heading.click(timeout=3_000, force=True)
        except Exception:
            pass
    page.wait_for_timeout(300)


def _pick_date(page, local: datetime) -> None:
    trigger = page.locator("#datepicker-trigger").first
    trigger.click(timeout=10_000)
    page.wait_for_timeout(400)
    # Ưu tiên bấm đúng ô ngày trong lịch; gõ tay dễ để lịch mở đè nút.
    label = re.compile(rf"{local.day}.*{local.strftime('%B')}|{local.strftime('%B')}.*{local.day}|^{local.day}$", re.I)
    cell = page.get_by_role("gridcell", name=label)
    if cell.count() == 0:
        cell = page.locator(f"[aria-label*='{local.day}'][aria-label*='{local.strftime('%B')}'], .ytcp-date-picker-day, .calendar-day")
    clicked = False
    if cell.count():
        try:
            cell.first.click(timeout=5_000)
            clicked = True
        except Exception:
            clicked = False
    if not clicked:
        page.keyboard.press("Control+A")
        page.keyboard.type(local.strftime("%d/%m/%Y"))
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
    _dismiss_popups(page)


def _pick_time(page, local: datetime) -> None:
    clock = page.locator("#time-of-day-container input").first
    clock.click(timeout=10_000)
    clock.fill(local.strftime("%H:%M"))
    clock.press("Enter")
    page.wait_for_timeout(300)
    if page.locator("tp-yt-paper-listbox:visible, #time-of-day-container tp-yt-iron-dropdown:visible").count():
        stamp = local.strftime("%H:%M")
        option = page.get_by_role("option", name=stamp)
        if option.count():
            try:
                option.first.click(timeout=3_000)
            except Exception:
                clock.press("Tab")
        else:
            clock.press("Tab")
    _dismiss_popups(page)


def _daily_limit(page) -> bool:
    return page.get_by_text(re.compile(r"giới hạn tải video lên hằng ngày|daily upload limit", re.I)).count() > 0


def _one(page, item: dict) -> None:
    video = Path(item["file"])
    if not video.exists():
        raise RuntimeError(f"Không thấy {video}")
    mo_studio._click_upload(page)
    page.wait_for_timeout(1000)
    if not mo_studio._upload_is_open(page):
        raise RuntimeError("Chưa thấy màn hình tải video lên.")
    page.locator("input[type=file]").first.set_input_files(str(video))
    print(f"Đã chọn file {video.name}.")
    page.locator("#title-textarea #textbox").first.wait_for(state="visible", timeout=60_000)
    if _daily_limit(page):
        raise RuntimeError(
            "YouTube chặn: đã đạt giới hạn tải video lên hằng ngày. "
            "Cần bấm Xác minh số điện thoại trong Studio, hoặc đợi 24 giờ. Không thử lại để tránh đốt hạn mức."
        )
    dang_nha._fill_box(page, "title-textarea", item["title"])
    dang_nha._fill_box(page, "description-textarea", item["description"])
    dang_nha._mark_not_for_kids(page)
    print("Đã điền tiêu đề, mô tả và hashtag.")
    for step in range(3):
        dang_nha._click_when_enabled(page, "#next-button")
        page.wait_for_timeout(800)
        print(f"Đã bấm Tiếp, bước {step + 1}.")
        if _daily_limit(page):
            raise RuntimeError(
                "YouTube chặn: đã đạt giới hạn tải video lên hằng ngày. "
                "Cần bấm Xác minh số điện thoại trong Studio, hoặc đợi 24 giờ. Không thử lại để tránh đốt hạn mức."
            )
    _schedule(page, item["publish_at"])
    dang_nha._click_when_enabled(page, "#done-button")
    print("Đã bấm Đăng.")
    page.get_by_text(re.compile(r"đã đăng|video published|đã xử lý|đã lên lịch|scheduled", re.I)).first.wait_for(
        state="attached", timeout=120_000
    )
    close = page.locator("#close-button, ytcp-button#close-button").first
    if close.count() and close.is_visible():
        close.click(timeout=10_000)
        page.wait_for_timeout(800)


def _goto(page, url: str, tries: int = 5) -> None:
    for attempt in range(1, tries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            if "chrome-error://" not in page.url:
                return
        except Exception as exc:
            if attempt == tries:
                raise
            print(f"Chưa mở được {url} (lần {attempt}): {str(exc).splitlines()[0][:120]}")
        page.wait_for_timeout(30_000 * attempt)
    raise RuntimeError(f"Không mở được {url} sau {tries} lần.")


def upload_day(folder: Path) -> int:
    manifest = folder / "lich.json"
    done = folder / "da-dang.txt"
    if not manifest.exists():
        print(f"Chưa có {manifest}. Chưa mở Studio.")
        return 1
    finished = set(done.read_text(encoding="utf-8").splitlines()) if done.exists() else set()
    items = [
        item
        for item in json.loads(manifest.read_text(encoding="utf-8"))
        if Path(item["file"]).exists() and Path(item["file"]).name not in finished
    ]
    if not items and finished:
        print("Ngày này đã đăng đủ. Không đăng lại.")
        return 0
    if not items:
        print("Chưa có file video để đăng.")
        return 1
    playwright, context, page = mo_studio._open_chrome()
    shot = folder / "studio-dang.jpg"
    try:
        _goto(page, mo_studio.HOME)
        mo_studio._wait_for_login(page)
        print("Đã mở trang chủ YouTube.")
        _goto(page, mo_studio.STUDIO)
        mo_studio._wait_for_login(page)
        page.wait_for_url(re.compile(rf"studio\.youtube\.com/channel/{mo_studio.CHANNEL_ID}"), timeout=60_000)
        print("Đã vào kênh trong YouTube Studio.")
        mo_studio._click_overview(page)
        print("Đã bấm Tổng quan.")
        for item in items:
            _one(page, item)
            name = Path(item["file"]).name
            with done.open("a", encoding="utf-8") as handle:
                handle.write(name + "\n")
            print(f"Xong {name}.")
        page.screenshot(path=str(shot), full_page=True)
        print(shot)
    except Exception:
        try:
            page.screenshot(path=str(shot), full_page=True)
            print(f"Đã chụp màn hình lỗi: {shot}")
        except Exception:
            pass
        raise
    finally:
        context.close()
        playwright.stop()
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python us-daily/dang_studio.py output/us-daily/YYYY-MM-DD")
        return 1
    return upload_day(Path(sys.argv[1]))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise
