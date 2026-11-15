---
name: us-news-finance-videos
description: >-
  Builds and checks the daily U.S. Shorts pack: one sourced news Short and one
  household money Short, with retention hooks and rival comparison. Use when
  the user asks for a U.S. news Short, a finance explainer Short, layout or
  safe-zone checks, rival Short analysis, or updates to this daily pipeline.
---

# U.S. news and finance Shorts

Reply to the user in Vietnamese. Spoken words in the videos stay English.

Do not publish, upload, or schedule anything on YouTube, TikTok, or email unless the user explicitly asks. Keys stay in `.env` and are never printed.

## Daily pack (current)

Since 2026-11-13 the scheduled pack is **Shorts only**:

| Slot (Eastern) | File | Job |
|---|---|---|
| 8:00 | `short-tin.mp4` | Top U.S. stories of the day, ranked and hooked |
| 16:00 | `short-tien.mp4` | One money/housing number from the 30-day calendar |

Built by `us-daily/lam_short.py`. Verified by `us-daily/kiem_dinh.py` (1080×1920, 15–59s, ≥29 fps, loudness, safe-zone text). Do **not** cut Shorts out of a 1280×720 long video.

Retention, hooks, and rival-beat rules live in [retention.md](retention.md). The latest high-view rival snapshot is [rival-compare.md](rival-compare.md). Read both before changing scripts or layout.

## Write rules (short version)

**News**

1. Rank stories (two outlets, hot words, digits) before picking three.
2. Hook names the lead story in ≤3 seconds. Big on-screen text for muted viewers.
3. Re-hook by ~7s: why it matters (votes / markets / safety / paychecks).
4. Lead story first, then two supports. Outlet credit stays on screen.
5. Close the loop + follow CTA. No invented facts.

**Money**

1. Proof-first: open on the number.
2. Re-hook: what the number means.
3. One context beat, where the example fails, this week's action, disclaimer.
4. Title keeps a digit. Source on screen.

## Pipeline

1. **Collect.** RSS in `us-daily/run.py` (PBS NewsHour, New York Times, NPR). Optional `newspaper3k` only for an article the RSS already named.
2. **Write.** Follow [retention.md](retention.md). Do not invent seat counts, poll numbers, or prices.
3. **Speak.** `edge-tts`, `en-US-AndrewNeural`, rate `-4%`. First word ASAP; no greeting.
4. **Picture.** News: article photo; full-bleed if portrait, letterboxed if landscape. Money: new icon each beat. Captions word-highlight inside the phone safe zone.
5. **Check.** `python us-daily/kiem_dinh.py output/us-daily/YYYY-MM-DD`. Also compare duration/loudness to `us-daily/doi_thu_short.json`.
6. **Rival deep dive (when asked).** `python us-daily/phan_tich_doi_thu.py` → `doi_thu_phan_tich.json`. Beat rivals on at least two retention axes before claiming an upgrade.

## Sources that were checked

Read [sources.md](sources.md) before adding a tool. Defaults:

- Production voice/layout: local `us-daily/lam_short.py` + Edge-TTS + article photos
- Retention craft (adapted, not copied wholesale): Spotlight-Revenue short-form-video-script-writer; xsrazy fyp-skills `video-hook`
- Rival measurement: `yt-dlp` + Deno JS runtime + `imageio_ffmpeg`
- Article text: `newspaper3k`
- Bar-chart race (rare): `dexplo/bar_chart_race` only with a sourced year table

## Verify

```bash
python us-daily/kiem_dinh.py output/us-daily/YYYY-MM-DD
```

`ĐẠT` means both Shorts present and every blocking check passed. Fix named errors and run again.
