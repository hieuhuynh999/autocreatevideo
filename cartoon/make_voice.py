"""Giọng Anh cho hai phim ngắn. Không ghi đè kịch bản nguồn của repo hoạt hình."""

import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent / "remotion" / "public"
VOICE = "en-US-AndrewNeural"
LINES = {
    "card.mp3": (
        "Here is the number. A one thousand dollar card at twenty percent a year costs about two hundred dollars "
        "in interest if the balance never falls. Divide that rate by twelve. The first month of interest on one "
        "thousand dollars is about sixteen dollars and sixty seven cents. Suppose the minimum payment is twenty "
        "five dollars. About sixteen dollars of it is interest. Only about eight dollars reduces what you owe. "
        "Next month the balance is still near one thousand dollars. That is the trap. Now pay the twenty five "
        "dollars, and add one hundred dollars. About one hundred eight dollars reduces the balance after interest. "
        "The balance falls toward the high eight hundreds. Same card. Same rate. The extra hundred is the whole plot. "
        "This week, read the APR on your own statement. Write one month of interest: balance, times your APR, "
        "divided by twelve. This is not personal financial advice, and it is not a promise about your card."
    ),
    "fund.mp3": (
        "Here is the number you control. Two hundred dollars a month for ten years is twenty four thousand dollars "
        "of your own money. Nobody has to promise a return for that sentence to be true. Two hundred times one "
        "hundred twenty months is twenty four thousand. If a fund averaged seven percent a year, compounded monthly, "
        "those deposits would grow to about thirty four thousand six hundred dollars. That second number is a labeled "
        "hypothetical, not a forecast. Markets do not owe you seven percent. Some years are negative. An index fund "
        "owns a wide list of companies. One stock means one company can cut the account in half. The deposit math "
        "stays the same. If two hundred dollars is more than the paycheck allows, fifty dollars a month for ten years "
        "is six thousand dollars of deposits. This week, set the transfer for the day after payday, for an amount you "
        "can keep. This is not personal financial advice, and it is not a projection of your account."
    ),
}


async def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, text in LINES.items():
        dest = ROOT / name
        await edge_tts.Communicate(text, VOICE, rate="-4%").save(str(dest))
        print(dest, len(text.split()))


if __name__ == "__main__":
    asyncio.run(main())
