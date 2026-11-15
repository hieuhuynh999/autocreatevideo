# Rival Short compare (snapshot 2026-11-15)

Measured from public Shorts tabs (metadata only when download/subtitle rate-limits hit). Full JSON: `us-daily/doi_thu_phan_tich.json`.

## News Shorts — highest views in sample

| Channel | Views | Duration | Title pattern |
|---|---:|---:|---|
| @ABCNews | 398,063 | 84s | FAA nationwide ground stop — live disruption |
| @NBCNews | 221,523 | 66s | Busiest U.S. airport after ground stop |
| @NBCNews | 205,765 | 23s | SpaceX catch — spectacle, instant payoff |
| @NBCNews | 190,545 | 39s | Senate race projection — election stake |
| @CNN | 53,877 | 93s | Blame game on flights fiasco |
| @PBSNewsHour | 24,532 | 78s | Boebert loses House seat |

### What the top news Shorts share

1. **One lead story only.** The top clips are not equal three-story stacks. They open on the day's dominant event (ground stop / SpaceX / Senate).
2. **Personal relevance in the title.** Airport, passengers, "how … is operating", "watch", race called — the viewer sees themselves or a clear stake.
3. **Motion or face in frame 1.** Reporter stand-up, rocket catch, press conference — not a static logo.
4. **Duration split.** Spectacle clips win short (23s). Explainers run longer (60–90s). Our pack stays under 58s, so we must pick the lead hard and cut support.
5. **Open loop.** Ground stop → when do flights restart? Race → who won? Rocket → did the catch work?

### Where our old news Short lost

- Treated 3 RSS items as equal; lead was not highlighted.
- First spoken line was the first headline, with no "why care" before story 2.
- On-screen text was only captions + outlet credit — muted scrollers got no hook board.
- Ending said "today's briefing" without promising tomorrow's top story.

### How we beat that (implemented)

- Rank stories; label **LEAD**.
- Spoken hook + big on-screen hook in first seconds.
- Re-hook: why it matters (votes / markets / safety / paychecks).
- Trim order protects hook/re-hook.
- Description marks LEAD and lists supports.

## Money Shorts — highest views in sample

| Channel | Views | Duration | Title pattern |
|---|---:|---:|---|
| @moneyguyshow | 579,323 | 54s | Was life more affordable in 1980? — contrast + identity |
| @GrahamStephan | 162,665 | 64s | Crazy tenant destroyed property — story + outrage |
| @GrahamStephan | 53,173 | 57s | How is this legal?? — curiosity + anger |
| @GrahamStephan | 51,002 | 44s | NBA player flying private — lifestyle contrast |
| @moneyguyshow | 45,800 | 36s | Coast FIRE couple — transformation |
| @moneyguyshow | 35,348 | 41s | Extra $200 spend or save? — forced choice + number |

### What the top money Shorts share

1. **Identity or forced choice in the first line.** "Was life …", "How is this legal", "Would you spend $200".
2. **A single sticky number or contrast.** 1980 vs now; $200; private jet vs normal flyer.
3. **Talking head + big captions.** Face carries trust; captions carry the muted hook.
4. **Emotional stake.** Outrage, envy, relief, or "this is for people like me".
5. **Payoff closes the question.** The title's question is answered before the end.

### Where our old money Short lost

- Opened with dry fact sentences from the long script.
- Number appeared on screen but was not the spoken first promise.
- No forced "keep this one number" identity line.
- Where-it-fails came late without a re-hook after the open.

### How we beat that (implemented)

- Proof-first: "If you keep one money number this week, make it {number}."
- Immediate re-hook with the fact sentence.
- Keep fails + this week + disclaimer.
- Verifier blocks missing proof-first hook or missing "this week".

## Scorecard vs rivals (after change)

| Axis | Top rivals | Our Shorts after update |
|---|---|---|
| Lead clarity | One story | Ranked LEAD + two supports |
| First 3s | Event / question / number | Hook spoken + on-screen |
| Re-hook ~7s | Often visual cut | Spoken why-it-matters / number meaning |
| Duration | 23–93s news; 36–64s money | Hard cap 58s |
| Muted readability | Mixed | Hook board + 84px captions |
| Fact safety | Desk reporting | Still outlet-sourced; no invented stats |

Re-run `python us-daily/phan_tich_doi_thu.py` when YouTube rate limits ease to refresh stills and opening transcripts.
