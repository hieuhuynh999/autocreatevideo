"""Ba bài mỗi ngày: hai video tài chính và một bản tin Mỹ.

Chạy từ thư mục project:
  python us-daily/run.py

Kết quả nằm trong output/us-daily/YYYY-MM-DD/.
Tool không thu tiếng, không gọi Wan, không tự đăng.
"""

from __future__ import annotations

import asyncio
import html
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
NY = ZoneInfo("America/New_York")
UA = "us-daily/1.0 (research briefing; contact local)"
IMAGE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ISSUES = 6

FEEDS = (
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("NPR Business", "https://feeds.npr.org/1006/rss.xml"),
    ("New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("New York Times Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("PBS NewsHour", "https://www.pbs.org/newshour/feeds/rss/headlines"),
)

STOP = {
    "the", "a", "an", "of", "to", "and", "in", "on", "for", "as", "at", "by",
    "from", "with", "after", "over", "into", "its", "it", "is", "are", "was",
    "us", "u", "s", "new", "says", "say", "how", "what", "why", "who",
}


@dataclass
class Story:
    outlet: str
    title: str
    link: str
    summary: str
    author: str
    image: str
    order: int
    feed: int


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None and len(list(node)) == 0:
        return ""
    raw = "".join(node.itertext()) if node is not None else ""
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return " ".join(raw.split())


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def _image_url(item: ET.Element) -> str:
    best = ""
    best_width = -1
    for node in item.findall("{http://search.yahoo.com/mrss/}content"):
        url = node.get("url") or ""
        if not url:
            continue
        try:
            width = int(node.get("width") or 0)
        except ValueError:
            width = 0
        if width >= best_width:
            best, best_width = url, width
    if best:
        return best
    thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
    if thumb is not None and thumb.get("url"):
        return thumb.get("url") or ""
    enclosed = item.find("enclosure")
    if enclosed is not None and "image" in (enclosed.get("type") or "") and enclosed.get("url"):
        return enclosed.get("url") or ""
    encoded = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    raw = encoded.text if encoded is not None and encoded.text else ""
    found = re.findall(r"""src=['"]([^'"]+)""", raw)
    return found[0] if found else ""


def _parse_feed(outlet: str, url: str, feed: int) -> list[Story]:
    root = ET.fromstring(_fetch(url))
    stories: list[Story] = []
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for index, item in enumerate(items[:12]):
        title = _text(item.find("title")) or _text(item.find("{http://www.w3.org/2005/Atom}title"))
        if title.lower().startswith("news wrap"):
            continue
        link = _text(item.find("link"))
        if not link:
            link_node = item.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.get("href", "") if link_node is not None else ""
        summary = _text(item.find("description")) or _text(item.find("{http://www.w3.org/2005/Atom}summary"))
        author = _text(item.find("{http://purl.org/dc/elements/1.1/}creator")) or _text(item.find("author"))
        image = _image_url(item)
        if title and link and image:
            stories.append(Story(outlet, title, link, summary[:520], author, image, index, feed))
    return stories


def _tokens(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", title.lower())
    return {word for word in words if word not in STOP}


def _same(a: Story, b: Story) -> bool:
    if a.outlet == b.outlet:
        return False
    left, right = _tokens(a.title), _tokens(b.title)
    if not left or not right:
        return False
    overlap = len(left & right) / len(left | right)
    return overlap >= 0.34


def _clusters(stories: list[Story]) -> list[list[Story]]:
    groups: list[list[Story]] = []
    for story in stories:
        placed = False
        for group in groups:
            if any(_same(story, other) for other in group):
                if all(story.link != other.link for other in group):
                    group.append(story)
                placed = True
                break
        if not placed:
            groups.append([story])
    groups.sort(key=lambda group: (-len({item.outlet for item in group}), -len(group)))
    return groups


def _family(outlet: str) -> str:
    if outlet.startswith("NPR"):
        return "NPR"
    if outlet.startswith("New York Times"):
        return "New York Times"
    if outlet.startswith("PBS"):
        return "PBS NewsHour"
    return outlet


def _load_news() -> tuple[list[list[Story]], list[str]]:
    stories: list[Story] = []
    errors: list[str] = []
    for feed, (outlet, url) in enumerate(FEEDS):
        try:
            stories.extend(_parse_feed(outlet, url, feed))
        except Exception as exc:
            errors.append(f"{outlet}: {exc}")
    seen: set[str] = set()
    unique: list[Story] = []
    for story in stories:
        if story.link in seen:
            continue
        seen.add(story.link)
        unique.append(story)
    return _clusters(unique), errors


def _sentence(summary: str) -> str:
    clean = " ".join(summary.split()).replace("U.S.", "U_S_").replace("U.K.", "U_K_")
    clean = re.sub(r"\b(Mr|Mrs|Ms|Dr|Sen|Rep|Gen|Jr|Sr)\.", r"\1_", clean)
    if not clean:
        return ""
    match = re.search(r"(.+?[.!?])(?:\s|$)", clean)
    if not match:
        return ""
    sentence = match.group(1).replace("U_S_", "U.S.").replace("U_K_", "U.K.")
    sentence = re.sub(r"\b(Mr|Mrs|Ms|Dr|Sen|Rep|Gen|Jr|Sr)_", r"\1.", sentence)
    if len(sentence) > 340:
        return ""
    return sentence


def _jaccard(a: Story, b: Story) -> float:
    left, right = _tokens(a.title), _tokens(b.title)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _lead(group: list[Story]) -> Story | None:
    pictured = [item for item in group if item.image]
    if not pictured:
        return None
    explained = [item for item in pictured if item.summary]
    return (explained or pictured)[0]


def _pick(groups: list[list[Story]]) -> list[tuple[Story, list[Story]]]:
    """Lấy lần lượt PBS, New York Times, NPR để sáu vấn đề không dồn về một báo."""
    pool = [group for group in groups if _lead(group) is not None]
    families = ("PBS NewsHour", "New York Times", "NPR")
    chosen: list[tuple[Story, list[Story]]] = []
    used: set[str] = set()
    counts = {name: 0 for name in families}

    def take(threshold: float, cap: int) -> None:
        while len(chosen) < ISSUES:
            moved = False
            for family in families:
                if counts[family] >= cap:
                    continue
                best: Story | None = None
                best_group: list[Story] | None = None
                for group in pool:
                    if any(item.link in used for item in group):
                        continue
                    candidate = next(
                        (item for item in group if _family(item.outlet) == family and item.image),
                        None,
                    )
                    if candidate is None:
                        continue
                    if any(_jaccard(candidate, have) >= threshold for have, _rest in chosen):
                        continue
                    rank = (candidate.feed, candidate.order)
                    if best is None or rank < (best.feed, best.order):
                        best = candidate
                        best_group = group
                if best is None or best_group is None:
                    continue
                others = [item for item in best_group if item.link != best.link]
                chosen.append((best, others))
                counts[family] += 1
                used.update(item.link for item in best_group)
                moved = True
                if len(chosen) == ISSUES:
                    return
            if not moved:
                return

    take(0.22, 2)
    if len(chosen) < ISSUES:
        take(0.22, 3)
    if len(chosen) < 4:
        take(0.5, 3)
    return chosen


def _save_image(url: str, dest: Path) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": IMAGE_UA, "Referer": "https://www.google.com/"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except Exception:
        return False
    if len(data) < 2000:
        return False
    if not (
        data.startswith(b"\xff\xd8")
        or data.startswith(b"\x89PNG")
        or data.startswith(b"RIFF")
        or data.startswith(b"GIF")
    ):
        return False
    dest.write_bytes(data)
    small = dest.with_suffix(".jpg")
    proc = subprocess.run(
        [_ffmpeg(), "-y", "-i", str(dest), "-vf", "scale=1680:-2", "-q:v", "3", str(small)],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0 and small.stat().st_size > 2000:
        small.replace(dest)
    else:
        small.unlink(missing_ok=True)
    return True


def _ahead(title: str) -> str:
    text = title.rstrip(".").split(",")[0]
    words = text.split()
    weak = {"the", "a", "an", "of", "to", "in", "on", "for", "after", "and", "as", "with"}
    if len(words) > 8:
        words = words[:8]
    while len(words) > 3 and words[-1].lower().strip(".'") in weak:
        words.pop()
    return " ".join(words)


def _intro_line(when: datetime, ready: list[dict]) -> str:
    """Câu đầu là tin mạnh nhất. Ba tin sau là lời hứa, chưa kể hết."""
    lead = ready[0]["title"].rstrip(".")
    bits = [_ahead(item["title"]) for item in ready[1:4]]
    if len(bits) >= 2:
        stack = ", ".join(bits[:-1]) + ", and " + bits[-1]
    else:
        stack = bits[0] if bits else ""
    day = when.strftime("%A, %B ") + str(when.day)
    if stack:
        return f"{lead}. Still ahead: {stack}. {day}."
    return f"{lead}. {day}."


def _close_line() -> str:
    """Câu cuối bỏ lửng để khi video lặp, câu đầu trả lời luôn."""
    return "Not advice about your vote or your money. If you only remember one sentence, it is this."


def _issue_words(lead: Story, others: list[Story], index: int, total: int) -> str:
    brief = _sentence(lead.summary)
    outlet = _family(lead.outlet)
    headline = lead.title.rstrip(".") + "."
    lines = [headline]
    if brief and brief.lower().rstrip(".!?") not in headline.lower():
        lines.append(brief if brief[-1:] in ".!?" else brief + ".")
    lines.append(f"That is {outlet}.")
    different = [item for item in others if _family(item.outlet) != outlet]
    if different:
        lines.append(f"{_family(different[0].outlet)} is also reporting this.")
    del index, total
    return " ".join(lines)


def news_script(when: datetime, groups: list[list[Story]], folder: Path) -> tuple[str, list[dict]]:
    pictures = folder / "anh"
    pictures.mkdir(parents=True, exist_ok=True)
    chosen = _pick(groups)
    ready: list[dict] = []
    for lead, others in chosen:
        dest = pictures / f"{len(ready):02d}.img"
        if not _save_image(lead.image, dest):
            continue
        different = [item for item in others if _family(item.outlet) != _family(lead.outlet)]
        outlets = [_family(lead.outlet)]
        for item in different:
            name = _family(item.outlet)
            if name not in outlets:
                outlets.append(name)
        ready.append(
            {
                "confirmed": len(outlets) >= 2,
                "outlets": outlets,
                "title": lead.title,
                "link": lead.link,
                "image": str(dest),
                "outlet": _family(lead.outlet),
                "author": lead.author,
                "spoken": "",
                "others": [
                    {"outlet": _family(item.outlet), "title": item.title, "link": item.link}
                    for item in different[:1]
                ],
                "_lead": lead,
                "_others": different,
            }
        )
        if len(ready) == ISSUES:
            break
    total = len(ready)
    for index, item in enumerate(ready, start=1):
        item["spoken"] = _issue_words(item.pop("_lead"), item.pop("_others"), index, total)
    return _speak_ready(when, ready)


def _speak_ready(when: datetime, ready: list[dict]) -> tuple[str, list[dict]]:
    total = len(ready)
    blocks = []
    if total == 0:
        blocks.append("No article with a picture could be saved from the feeds. Do not record the news video.")
    else:
        blocks.append(_intro_line(when, ready))
        for item in ready:
            blocks.append(item["spoken"])
        blocks.append(_close_line())
    return "\n\n".join(blocks).strip() + "\n", ready


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9$%']+", text))


def _money(amount: float) -> str:
    return f"{amount:,.0f} dollars" if amount >= 100 else f"{amount:,.2f} dollars"


def finance_pair(when: datetime) -> list[dict]:
    rent_food_bills = 3000
    paycheck = 4000
    card = 1000
    apr = 0.20
    monthly_rate = apr / 12
    month_interest = card * monthly_rate
    minimum = 25
    principal_drop = minimum - month_interest
    yearly_if_frozen = card * apr
    save = 200
    months = 120
    rate = 0.07 / 12
    contributed = save * months
    grown = save * (((1 + rate) ** months) - 1) / rate
    topics = [
        _emergency(rent_food_bills),
        _split(paycheck),
        _card(card, apr, month_interest, minimum, principal_drop, yearly_if_frozen),
        _fund(save, contributed, grown),
        _debt_or_fund(paycheck),
        _grocery(paycheck),
    ]
    slot = (when.toordinal() * 2) % len(topics)
    chosen = [topics[slot], topics[(slot + 1) % len(topics)]]
    return chosen


def _wrap(title: str, number: str, body: list[str], source: str) -> dict:
    spoken = "\n".join(body).strip() + "\n"
    return {
        "title": title,
        "number": number,
        "spoken": spoken,
        "source": source,
        "words": _words(spoken),
    }


def _emergency(monthly: int) -> dict:
    three = monthly * 3
    six = monthly * 6
    body = [
        f"Here is the number. If the bills you must pay come to { _money(monthly) } a month, three months of those bills is { _money(three) }.",
        "This video is for someone in the United States who wants one savings target, not a tour of the whole economy.",
        f"Start with necessary bills only. Rent or the mortgage. Groceries you actually cook. Utilities. Insurance. The minimum payment on a debt. Add those for one normal month. In this example that total is { _money(monthly) }.",
        f"Multiply by three. {monthly} times 3 is {three}. That is { _money(three) }. The cash should sit in a savings account you can open without selling an investment and without paying a penalty.",
        f"If your work is seasonal, or a single missed paycheck would hit immediately, use six months instead. {monthly} times 6 is {six}. That is { _money(six) }.",
        "Do not put restaurants, vacations, or a new phone inside the monthly number. Those are wants. Mixing them in makes the target so large that people never start.",
        "This is a planning rule used by household guides in the United States. It is not a statute. The Consumer Financial Protection Bureau tells people to build emergency savings and to start with an amount they can actually reach. The Bureau does not require your number to be nine thousand dollars. Nine thousand is only this example.",
        "The rule fails when necessary bills already consume the whole paycheck. Then the first target is smaller: one month, or even one thousand dollars, before you aim at three months.",
        "This week, write five lines: rent, food at home, utilities, insurance, and debt minimums. Add them. Multiply by three. That product is your number. Move the first fifty dollars into a separate savings account if you can do it without missing a minimum payment.",
        "This is not personal financial advice. Your rent is not the rent in the example.",
    ]
    return _wrap(
        f"A {three:,} dollar emergency fund, from a {monthly:,} dollar month",
        f"${three:,}",
        body,
        "Consumer Financial Protection Bureau, consumerfinance.gov, emergency savings guides. The dollar amounts are an example.",
    )


def _split(pay: int) -> dict:
    needs, wants, save = int(pay * 0.5), int(pay * 0.3), int(pay * 0.2)
    body = [
        f"Here is the number. On a take-home paycheck of { _money(pay) }, the 50, 30, 20 split is { _money(needs) } for needs, { _money(wants) } for wants, and { _money(save) } for savings and extra debt payments.",
        "Take-home means the money after taxes, the amount that reaches the bank. Do not run this split on the larger salary printed on an offer letter.",
        f"Needs are half. Half of {pay} is {needs}. Housing, basic food, utilities, insurance, and minimum debt payments live here.",
        f"Wants are thirty percent. Thirty percent of {pay} is {wants}. Eating out, subscriptions, and trips live here.",
        f"The last twenty percent is {save} dollars. That slice is savings, including the emergency fund, and any payment above the minimum on a debt.",
        "The split is a framework from U.S. household writing, associated with Elizabeth Warren's book on family bills. It is not the tax code.",
        "It breaks when rent alone is close to the entire needs slice. If rent is 1,800 dollars, only 200 dollars of the needs slice remains for food, power, and insurance. In that city, the honest move is to shrink wants before you pretend the poster still fits.",
        "This week, label last month's deposits and withdrawals with three words: need, want, or save. Do not change banks yet. See which slice is already over the line.",
        "This is not personal financial advice.",
    ]
    return _wrap(
        f"How to split a {pay:,} dollar paycheck: {needs:,}, {wants:,}, and {save:,}",
        f"${needs:,} / ${wants:,} / ${save:,}",
        body,
        "The 50/30/20 budget is a published household framework, not a government rule. Amounts are an example on a 4,000 dollar take-home paycheck.",
    )


def _card(balance: int, apr: float, month_interest: float, minimum: int, drop: float, yearly: float) -> dict:
    body = [
        f"Here is the number. A { _money(balance) } card balance at {apr:.0%} a year costs about { _money(yearly) } in interest over a year if the balance never falls.",
        f"The yearly rate in this example is {apr:.0%}. Divide by twelve for a month. The month rate is about {apr / 12:.2%}. On {balance} dollars, the first month of interest is about {month_interest:.2f} dollars.",
        f"Suppose the required minimum that month is {minimum} dollars. About {month_interest:.2f} dollars of that payment is interest. Only about {drop:.2f} dollars reduces what you owe. The next month the balance is still near {balance} dollars. That is the trap.",
        "The two hundred dollar figure is the simple yearly illustration: one thousand times twenty percent. A real statement compounds every month, so a balance you do not pay down costs more than that sketch. Read the APR on your own statement. Do not use twenty percent if your card says something else.",
        "Walk the same card a second way, still as an example. Month one, you pay the twenty-five dollar minimum. About sixteen dollars and sixty-seven cents is interest. About eight dollars and thirty-three cents comes off the one thousand. The balance is about nine hundred ninety-two dollars. Month two, interest is a little smaller, and the minimum, if it stays twenty-five dollars, removes a little more principal. The direction is right. The speed is slow. That is why people feel they are paying and the balance barely moves.",
        "Now change one behavior in the example. You still pay the twenty-five dollars the issuer asks for, and you add one hundred dollars. In month one, about one hundred eight dollars reduces the balance after interest. The balance falls toward the high eight hundreds, not the high nine hundreds. Same card. Same APR. The extra hundred is the whole plot of the video.",
        "Do not use this sketch if your APR is not twenty percent. A fourteen percent card and a twenty-nine percent card are different stories. The formula stays: balance, times your APR, divided by twelve. Write your APR in the margin before you trust any dollar figure from a video, including this one.",
        "Do not skip the minimum on a second card in order to attack the first. A missed minimum can trigger a penalty rate. The extra payment is extra. The minimums on every card stay in place.",
        "This week, find the APR and the minimum on one card. Write the interest for one month the way we just did: balance, times APR, divided by twelve. If you can pay more than the minimum without missing rent, the extra dollars are the ones that cut the balance. Put that extra amount on autopay the same day you watch this, or write it on a calendar if autopay is not available.",
        "This is not personal financial advice, and it is not a promise about your card.",
    ]
    return _wrap(
        f"A {balance:,} dollar card at {apr:.0%} costs about {yearly:.0f} dollars a year",
        f"${yearly:.0f}",
        body,
        "Illustration only. Check the APR on the card statement. U.S. card interest is set by the issuer under Truth in Lending disclosures.",
    )


def _fund(monthly: int, contributed: float, grown: float) -> dict:
    body = [
        f"Here is the number you control. Two hundred dollars a month for ten years is { _money(contributed) } of your own money. Nobody has to promise a return for that sentence to be true.",
        f"The second number is a labeled hypothetical, not a forecast. If a fund averaged seven percent a year, compounded monthly, those deposits would grow to about { _money(grown) }. Markets do not owe you seven percent. Some years are negative. This video is not predicting the next ten years.",
        "An index fund owns a wide list of companies and tries to match a market index. Picking one stock means one company can cut the account in half. The contribution math is the same either way: two hundred dollars, times one hundred twenty months, is twenty-four thousand dollars.",
        "Use a U.S. account you understand, such as a workplace plan or an IRA, only after you read that account's own rules. This video does not tell you which fund to buy.",
        "Separate the two numbers whenever someone sells you a chart. The first number, twenty-four thousand dollars, is deposits. You can check it with a calculator: two hundred times one hundred twenty months. The second number, the hypothetical grown total, depends on a return nobody can assign to the next ten years. If a chart shows only the grown total, ask how much of it was money you put in. If they cannot answer, you do not have the fact yet.",
        "A single stock does not change the deposit math. Two hundred dollars into one company for ten years is still twenty-four thousand dollars of deposits. The difference is the risk around that deposit. One company can fall because of one product, one lawsuit, or one missed year. A broad index fund spreads that across many companies. It can still fall. It does not fall because one company had a bad Tuesday, in the same way.",
        "If two hundred dollars is more than the paycheck allows after rent and the card minimum, the honest monthly amount is smaller. Fifty dollars a month for ten years is six thousand dollars of deposits. The habit is the same. The video's two hundred is an example so the arithmetic is easy to say out loud.",
        "This week, decide the dollar you can automate. Open the account you already have, or read the rules of a workplace plan before you open a new one. Set the transfer for the day after payday. If two hundred is too high, type the number you can keep for six months without taking it back. Fifty dollars a month is still six hundred dollars a year of money you put in.",
        "This is not personal financial advice and not a projection of your account.",
    ]
    return _wrap(
        f"Two hundred dollars a month is {contributed:,.0f} dollars in ten years, before any gain",
        f"${contributed:,.0f}",
        body,
        "The contribution total is arithmetic. The seven percent path is a hypothetical compound illustration, not a market forecast.",
    )


def _debt_or_fund(pay: int) -> dict:
    extra = 100
    body = [
        f"Here is the number. One hundred extra dollars from a { _money(pay) } take-home paycheck is {extra} dollars that should have one job.",
        "If a credit card charges about twenty percent and a savings account pays a few percent, the card balance is the more expensive leak. Sending the extra hundred to that card, after you have made the minimum, cuts a high rate. Sending it to a new fund while the card compounds is a choice, and the card usually wins the math.",
        "The exception is a tiny cash buffer. If you have no cash at all, the first hundred may need to sit in savings so a flat tire does not go back onto the card. After a small buffer exists, the extra hundred returns to the highest-interest debt.",
        "This is the same idea debt guides in the United States call the avalanche: extra payments go to the highest rate, while minimums stay paid on every debt.",
        "This week, list each debt's balance and APR. Circle the highest APR. Automate one extra payment there, even if it is fifty dollars, and do not skip a minimum somewhere else.",
        "This is not personal financial advice.",
    ]
    return _wrap(
        "Where an extra 100 dollars goes when a card charges about 20 percent",
        "$100",
        body,
        "Avalanche method as described in U.S. consumer-debt guides, including the Consumer Financial Protection Bureau's material on paying more than the minimum. Rates in the script are an example.",
    )


def _grocery(pay: int) -> dict:
    week = 150
    body = [
        f"Here is the number. One hundred fifty dollars of groceries in a week is {week * 4} dollars in a four-week month, before restaurants.",
        f"On take-home pay of { _money(pay) }, that grocery line is {week * 4 / pay:.0%} of the paycheck. The point is not that one hundred fifty is correct for your city. The point is to have your own weekly number before a news story about prices tells you how you feel.",
        "Keep restaurant meals out of this count. They move around and hide the grocery trend. Write the supermarket total from the last four receipts, divide by four, and that is your week.",
        "The Bureau of Labor Statistics publishes the official U.S. inflation indexes. A personal receipt is not the national index. It is the bill you can actually change.",
        "This week, add the last four supermarket receipts and divide by four. Put that weekly number in the title of a note on your phone. When a briefing mentions prices, compare it with your note, not with a stranger's example.",
        "This is not personal financial advice.",
    ]
    return _wrap(
        f"A {week} dollar grocery week is {week * 4} dollars a month",
        f"${week * 4}",
        body,
        "The weekly amount is an example. National inflation figures belong to the Bureau of Labor Statistics, bls.gov. Your receipts are your own.",
    )


def _package(kind: str, spoken: str, title: str, source_lines: list[str], shot: str) -> str:
    if kind == "finance":
        marks = [
            "0:00 The number",
            "0:20 What the number includes",
            "3:30 Where the example fails",
            "5:30 What to do this week",
        ]
        footer = "Not personal financial advice."
    else:
        marks = ["The picture changes when the article changes."]
        footer = "Each picture belongs to the newsroom named with it. The words are that article's headline and feed summary. Not advice."
    description = [
        title,
        "",
        *marks,
        "",
        "Sources:",
        *source_lines,
        "",
        footer,
    ]
    return (
        f"TITLE\n{title}\n\n"
        f"OPENING SHOT, 8 seconds, no text\n{shot}\n\n"
        f"DESCRIPTION\n" + "\n".join(description) + "\n\n"
        f"SPOKEN SCRIPT\n{spoken}"
    )


def _review(when: datetime, finance: list[dict], news: str, used: list[dict], errors: list[str], video_note: str) -> str:
    lines = [
        f"# Chấm ngày {when.strftime('%Y-%m-%d')} giờ New York",
        "",
        "Tool này ra lời nói, ảnh đúng bài báo, và một video tin nếu ghép được. Chưa đăng.",
        "",
    ]
    fails = 0
    for index, item in enumerate(finance, start=1):
        problems = []
        if not (420 <= item["words"] <= 1400):
            problems.append(f"độ dài {item['words']} chữ, ngoài khoảng 420–1400, tức dưới khoảng 4 phút nói")
        if "not personal financial advice" not in item["spoken"].lower():
            problems.append("thiếu câu không phải lời khuyên")
        if "this week" not in item["spoken"].lower():
            problems.append("thiếu việc làm trong tuần")
        if not re.search(r"\d", item["title"]):
            problems.append("tiêu đề không có con số")
        status = "Đạt" if not problems else "Chưa đạt"
        if problems:
            fails += 1
        lines.append(f"- Tài chính {index}: {status}. {item['words']} chữ. {item['title']}")
        for problem in problems:
            lines.append(f"  - {problem}")
    news_problems = []
    if len(used) < 4:
        news_problems.append(f"chỉ ghép được {len(used)} bài có ảnh, dưới 4")
    missing_picture = [item["title"] for item in used if not item.get("image")]
    if missing_picture:
        news_problems.append("có bài không có ảnh")
    if errors:
        news_problems.append("một số nguồn RSS lỗi: " + "; ".join(errors))
    news_status = "Đạt" if not news_problems else "Chưa đạt"
    if news_problems:
        fails += 1
    lines.append(f"- Tin tức: {news_status}. {_words(news)} chữ. {len(used)} vấn đề, mỗi vấn đề một ảnh của đúng bài.")
    for problem in news_problems:
        lines.append(f"  - {problem}")
    for item in used:
        mark = "hai nguồn" if item["confirmed"] else "một nguồn"
        lines.append(f"  - {item['outlet']}: {item['title']} ({mark})")
    lines += [
        "",
        f"Kết luận máy: {'ba bài đủ để thu thử ở bản ngắn' if fails == 0 else 'chưa đủ để thu đủ ba bài'}.",
        "Bài tài chính đang khoảng 4 phút nói, chưa tới 8–12 phút của kế hoạch. Bản tin lia ảnh và chạy chữ đúng nhịp lời. Lời chỉ là tiêu đề, một câu tóm tắt, và tên báo.",
        "",
        "Giới hạn cố ý:",
        "- Ngân hàng bài tài chính có 6 bài. Hai bài một ngày, lặp lại sau 3 ngày. Đây không phải biên tập viên.",
        "- Bản tin không chép nguyên bài. Ảnh là ảnh tòa soạn gắn trong RSS. Lời chỉ là tiêu đề, tác giả và một câu trong phần tóm tắt.",
        "- AP và Reuters không có RSS công khai ổn định trong lần thử này. Nguồn đang dùng là NPR, New York Times và PBS NewsHour.",
        "- Phải nghe lại số trước khi thu. Tool không biết hóa đơn thật của người xem.",
        f"- {video_note}",
    ]
    return "\n".join(lines) + "\n"


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _media_duration(ffmpeg: str, path: Path) -> float:
    proc = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        raise RuntimeError(f"không đọc được độ dài của {path.name}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


async def _speak_timed(text: str, dest: Path) -> list[tuple[float, float, str]]:
    import edge_tts

    voice = edge_tts.Communicate(text, "en-US-AndrewNeural", rate="-4%", boundary="WordBoundary")
    audio = bytearray()
    words: list[tuple[float, float, str]] = []
    async for chunk in voice.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10_000_000
            end = start + chunk["duration"] / 10_000_000
            token = str(chunk["text"]).strip()
            if token:
                words.append((start, end, token))
    dest.write_bytes(bytes(audio))
    return words


def _cue_groups(words: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    groups: list[list[tuple[float, float, str]]] = []
    current: list[tuple[float, float, str]] = []
    width = 0
    for start, end, token in words:
        gap = start - current[-1][1] if current else 0
        glue = token.lower().strip(".,!?;:") in {"of", "the", "a", "an", "to", "and", "in", "on", "for", "with"}
        if current and not glue and (width + len(token) + 1 > 32 or len(current) >= 4 or gap > 0.4):
            groups.append(current)
            current = []
            width = 0
        current.append((start, end, token))
        width += len(token) + 1
    if current:
        groups.append(current)
    return groups


def _ass_clock(seconds: float) -> str:
    seconds = max(0.0, seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}:{minutes:02d}:{sec:05.2f}"


def _ass_text(token: str) -> str:
    return token.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _write_captions(
    path: Path,
    words: list[tuple[float, float, str]],
    outlet: str,
    index: int,
    total: int,
    duration: float,
) -> None:
    groups = _cue_groups(words)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Hook,Impact,78,&H0000FFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,5,0,2,70,70,150,1",
        "Style: Caption,Arial Black,58,&H00FFFFFF,&H00B0B0B0,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,0,2,80,80,78,1",
        "Style: Bug,Arial,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,40,40,28,1",
        "Style: Count,Arial,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,9,40,40,28,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    end = _ass_clock(duration)
    bug = _ass_text(outlet.upper())
    lines.append(f"Dialogue: 0,0:00:00.00,{end},Bug,,0,0,0,,{bug}")
    if index:
        lines.append(f"Dialogue: 0,0:00:00.00,{end},Count,,0,0,0,,{_ass_text(f'{index} / {total}')}")
    for number, group in enumerate(groups):
        style = "Hook" if number == 0 else "Caption"
        pieces = []
        for start, stop, token in group:
            centiseconds = max(1, int(round((stop - start) * 100)))
            pieces.append(f"{{\\kf{centiseconds}}}{_ass_text(token)} ")
        start = _ass_clock(group[0][0])
        stop = _ass_clock(group[-1][1] + 0.18)
        lines.append(f"Dialogue: 1,{start},{stop},{style},,0,0,0,,{''.join(pieces).strip()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _motion_clip(
    ffmpeg: str,
    image: Path,
    audio: Path,
    captions: Path,
    dest: Path,
    slide: int,
) -> None:
    duration = _media_duration(ffmpeg, audio) + 0.25
    if slide % 2:
        travel = f"(in_w-out_w)*(1-t/{duration:.2f})"
    else:
        travel = f"(in_w-out_w)*t/{duration:.2f}"
    ass = captions.as_posix().replace(":", "\\:")
    fonts = "C\\:/Windows/Fonts"
    motion = (
        "scale=1680:945:force_original_aspect_ratio=increase,crop=1680:945,"
        f"crop=1280:720:x='{travel}':y='(in_h-out_h)*0.46',setsar=1,"
        "drawbox=x=0:y=ih-188:w=iw:h=188:color=black@0.58:t=fill,"
        "drawbox=x=0:y=0:w=iw:h=68:color=black@0.50:t=fill,"
        f"ass='{ass}':fontsdir='{fonts}'"
    )
    proc = subprocess.run(
        [
            ffmpeg, "-y",
            "-loop", "1", "-i", str(image),
            "-i", str(audio),
            "-t", f"{duration:.2f}",
            "-vf", motion,
            "-map", "0:v:0", "-map", "1:a:0",
            "-r", "24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1",
            "-movflags", "+faststart",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not dest.exists():
        raise RuntimeError(proc.stderr[-700:])


def _build_news_video(folder: Path, when: datetime, used: list[dict]) -> Path:
    ffmpeg = _ffmpeg()
    work = folder / "anh"
    total = len(used)
    intro_card = dict(used[0])
    intro_card["outlet"] = "U.S. briefing"
    end_card = dict(used[0])
    end_card["outlet"] = "U.S. briefing"
    cards = [("intro", _intro_line(when, used), intro_card, 0)]
    cards += [(f"{index:02d}", item["spoken"], item, index + 1) for index, item in enumerate(used)]
    cards.append(("end", _close_line(), end_card, 0))

    async def voices() -> dict[str, list[tuple[float, float, str]]]:
        timed: dict[str, list[tuple[float, float, str]]] = {}
        for name, text, _item, _index in cards:
            timed[name] = await _speak_timed(text, work / f"{name}.mp3")
        return timed

    timed = asyncio.run(voices())
    pieces: list[Path] = []
    for slide, (name, _text, item, index) in enumerate(cards):
        captions = work / f"{name}.ass"
        video = work / f"{name}.mp4"
        _write_captions(captions, timed[name], item["outlet"], index, total, _media_duration(ffmpeg, work / f"{name}.mp3"))
        _motion_clip(ffmpeg, Path(item["image"]), work / f"{name}.mp3", captions, video, slide)
        pieces.append(video)
    listing = work / "list.txt"
    listing.write_text("".join(f"file '{piece.as_posix()}'\n" for piece in pieces), encoding="utf-8")
    out = folder / "vi-du-tin.mp4"
    proc = subprocess.run(
        [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(out),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:])
    return out


def main() -> int:
    when = datetime.now(NY)
    day = when.strftime("%Y-%m-%d")
    folder = OUT / day
    folder.mkdir(parents=True, exist_ok=True)
    groups, errors = _load_news()
    news, used = news_script(when, groups, folder)
    finance = finance_pair(when)
    shot_news = "Mỗi đoạn dùng ảnh mà tòa soạn đã gắn với đúng bài đó. Không vẽ cảnh thay thế."
    shot_money = "A kitchen table in morning light, one notebook, one pen, a coffee cup, slow push-in, no readable text, no face."
    sources: list[str] = []
    for index, item in enumerate(used, start=1):
        sources.append(f"{index}. {item['outlet']}: {item['title']}")
        sources.append(item["link"])
        for other in item["others"]:
            sources.append(f"Related, not read in full: {other['outlet']}: {other['title']}")
            sources.append(other["link"])
    video_note = "Chưa ghép video tin."
    if used:
        try:
            video = _build_news_video(folder, when, used)
            video_note = f"Video tin đã ghép: {video}"
        except Exception as exc:
            video_note = f"Chưa ghép được video tin: {exc}"
    files = {
        "finance-1.txt": _package("finance", finance[0]["spoken"], finance[0]["title"], [finance[0]["source"]], shot_money),
        "finance-2.txt": _package("finance", finance[1]["spoken"], finance[1]["title"], [finance[1]["source"]], shot_money),
        "news.txt": _package(
            "news",
            news,
            f"U.S. briefing, {when.strftime('%B')} {when.day}: {len(used)} stories, one picture each",
            sources,
            shot_news,
        ),
        "review.md": _review(when, finance, news, used, errors, video_note),
    }
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
        print(f"{folder / name}")
    print(files["review.md"])
    return 0 if "ba bài đủ để thu thử" in files["review.md"] else 1


if __name__ == "__main__":
    sys.exit(main())
