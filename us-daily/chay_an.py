"""Chạy job.py không mở cửa sổ console, ghi toàn bộ chữ ra vào nhật ký theo ngày.

Task Scheduler gọi file này bằng pythonw.exe. Cửa sổ đen của python.exe từng bị
đóng giữa chừng (mã 0xC000013A), làm mất ba ngày đăng.

    pythonw.exe us-daily/chay_an.py --now --dang
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "output" / "us-daily" / "nhat-ky"


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable)
    if python.name.lower() == "pythonw.exe":
        python = python.with_name("python.exe")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    log = LOGS / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}.log"
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        proc = subprocess.run(
            [str(python), "-u", str(ROOT / "us-daily" / "job.py"), *sys.argv[1:]],
            cwd=ROOT,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        handle.write(f"\nexit={proc.returncode}\n")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
