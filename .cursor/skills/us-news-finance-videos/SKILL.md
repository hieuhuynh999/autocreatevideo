---
name: us-news-finance-videos
description: >-
  Builds and checks the daily U.S. pack: one sourced news video and two
  household money explainers. Use when the user asks for a U.S. news video,
  a finance or cost-of-living explainer, a bar chart race, Pexels or Edge-TTS
  assembly, newspaper scraping, or to verify those videos before they are shown.
---

# U.S. news and finance videos

Reply to the user in Vietnamese. Spoken words in the videos stay English.

Each New York day is one news video and two money explainers. Do not publish, upload, or schedule anything on YouTube, TikTok, or email. Keys stay in `.env` and are never printed.

The scheduled channel pack is different: since 2026-11-13 it is Shorts only. `us-daily/lam_short.py` builds two native 1080x1920 Shorts under 58 seconds (news at 8:00, money at 16:00 Eastern), and `us-daily/kiem_dinh.py` blocks any Short whose text leaves the phone safe zone recorded in `short-*.layout.json`. Do not go back to cutting Shorts out of a 1280x720 video.

## Which video

| Ask | Make | Picture |
|---|---|---|
| Tin Mỹ, daily news | 1 briefing | The article's own photo, credited, or a drawing of the thing just said |
| Tiền, thẻ, lương, quỹ, đời sống | 2 explainers, about one minute each when using the cartoon short, or the sourced script in `us-daily` | A new scene every sentence. Character drawings come from `cartoon/templates/bridge/toon.ts` |
| Bảng số theo năm (lương, GDP, lạm phát) | 1 bar-chart race | Only a real table with a source and years |

Do not grab a random stock clip for a news fact. Pexels, Openverse, or Wikimedia is allowed only when the clip shows the thing being said. Otherwise use the article image or a drawn scene.

## Pipeline

1. **Collect.** Prefer the RSS already in `us-daily/run.py` (PBS NewsHour, New York Times, NPR). Use `newspaper3k` (`codelucas/newspaper`, MIT) only to read one article the RSS already named: title, authors, top image, text. Do not crawl a site the feed did not cite.
2. **Write.** News: the outlet's headline, then one sentence from that article's summary, then "That is {outlet}." Do not add a hook that changes the fact. Do not invent seat counts, poll numbers, or prices. Finance: one labeled example, the arithmetic, where it fails, what to do this week, and "This is not personal financial advice."
3. **Speak.** `edge-tts`, voice `en-US-AndrewNeural`, rate `-4%`. Kokoro only if that venv already exists. Do not require Azure Speech.
4. **Picture.** News keeps the article photo through the last frame. Finance cuts to a new drawing each sentence (card, coins, scale, jars). A bar-chart race uses `bar_chart_race` and a CSV that names its source.
5. **Check.** Run the verifier below. Do not hand over a folder that prints `FAIL`.

## Sources that were checked

Read [sources.md](sources.md) before adding a new tool. These are the only defaults:

- Voice and stock assembly: [itsPremkumar/Automated-Video-Generator](https://github.com/itsPremkumar/Automated-Video-Generator) (MIT). No watermark. Edge-TTS is the fallback. Pexels needs `PEXELS_API_KEY` in `.env`. Do not pass `--post`.
- News scrape plus MoviePy: [akshatkhatri/Video_generation_tool](https://github.com/akshatkhatri/Video_generation_tool). It wants Azure Speech and an LLM that writes catchy lines. Do not copy that catchy-line step. Keep Edge-TTS and the outlet's sentence.
- Gemini scripts, thumbnails, YouTube upload: [Likhithsai2580/Automated-YouTube-Video-Creator](https://github.com/Likhithsai2580/Automated-YouTube-Video-Creator) (MIT). Do not run its upload. Do not put a Gemini key in the script.
- Article text: `newspaper3k`.
- Bar chart race: [dexplo/bar_chart_race](https://github.com/dexplo/bar_chart_race) (MIT). `drivesys/bar-chart-race` returns 404. The Fortune notebook is a template; it does not include the full 26-year table.

## Verify

From the project root:

```bash
python .cursor/skills/us-news-finance-videos/scripts/verify_pack.py output/us-daily/YYYY-MM-DD
```

`PASS` means every file that is present meets the checks. A missing news video is `THIEU`, not a pass, when the user asked for the daily pack. Fix the named check and run it again.

Finance must contain a digit in the title, the phrase "not personal financial advice", and a video of at least 40 seconds. News, when present, must name PBS, NPR, or New York Times, and the video must be at least 60 seconds.
