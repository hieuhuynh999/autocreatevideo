"""Giờ công khai theo giờ miền Đông, và một bài tiền mỗi ngày.

Tin Mỹ là một video gộp báo trong ngày. Bài còn lại là tiền, nhà hoặc kinh tế.
Hai Short cắt từ hai video đó. Máy chủ hẹn giờ, không để Chrome mở cả ngày.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
START = datetime(2026, 11, 6, tzinfo=NY)

# Giờ người xem Mỹ đang mở YouTube. Tin vào buổi sáng, Short tin lúc nghỉ trưa,
# bài tiền trước giờ xem tối, Short tiền trong khung Short buổi tối.
SLOTS = (
    ("tin", 8, 0),
    ("short-tin", 12, 0),
    ("tien", 16, 0),
    ("short-tien", 20, 0),
)


def public_times(when: datetime) -> dict[str, datetime]:
    day = when.astimezone(NY).replace(hour=0, minute=0, second=0, microsecond=0)
    return {name: day.replace(hour=hour, minute=minute) for name, hour, minute in SLOTS}


def row_for(when: datetime) -> dict:
    day = when.astimezone(NY).date()
    index = (day - START.date()).days
    if index < 0:
        index = 0
    row = ROWS[index % len(ROWS)]
    return {"date": day.isoformat(), **row}


def _say(fact: str, counted: str, left_out: str, fails: str, week: str, source: str) -> list[str]:
    return [
        f"Here is the number. {fact}",
        "This video is one example for a household in the United States. It is not your lease, your statement, or your tax bill.",
        counted,
        left_out,
        f"The source for the rule is {source}.",
        fails,
        f"This week, {week}",
        "This is not personal financial advice.",
    ]


ROWS = [
    {"key": "emergency"},
    {"key": "split"},
    {"key": "card"},
    {"key": "fund"},
    {"key": "extra"},
    {"key": "grocery"},
    {
        "title": "The 2026 401(k) employee limit is 24,500 dollars",
        "number": "$24,500",
        "source": "Internal Revenue Service, IR-2025-111. The monthly figure is 24,500 divided by 12.",
        "body": _say(
            "The 2026 employee limit for a 401(k) is 24,500 dollars. Spread over twelve months, that is about 2,042 dollars a month.",
            "That 24,500 dollars is money the employee elects to defer. It is the IRS employee limit for 2026, up from 23,500 dollars in 2025.",
            "It does not include money the employer adds, and it is not the higher catch-up amount for workers age 50 and older.",
            "The example fails when the paycheck cannot spare 2,042 dollars. The legal limit is a ceiling, not a bill you must pay.",
            "open last year's 401(k) statement and write the employee deferral next to 24,500 dollars. Do not raise the deferral in the same hour if rent is already late.",
            "the Internal Revenue Service notice IR-2025-111",
        ),
    },
    {
        "title": "The 2026 IRA limit is 7,500 dollars",
        "number": "$7,500",
        "source": "Internal Revenue Service, 2026 IRA contribution limits.",
        "body": _say(
            "The 2026 limit for a traditional or Roth IRA is 7,500 dollars. Divided by twelve, that is 625 dollars a month.",
            "The 7,500 dollars is the combined cap for your traditional and Roth IRAs in 2026, unless you are 50 or older.",
            "A rollover does not count toward this 7,500 dollar cap. The workplace 401(k) limit is a different cap.",
            "The example fails when taxable compensation for the year is under 7,500 dollars. You cannot contribute more than that compensation.",
            "divide 7,500 by the number of paychecks you have left in the year. That is the deposit to compare with 625 dollars a month.",
            "the Internal Revenue Service page on IRA contribution limits for 2026",
        ),
    },
    {
        "title": "A 2026 401(k) allows 17,000 dollars more than an IRA",
        "number": "$17,000",
        "source": "Internal Revenue Service, 2026 employee deferral limit and IRA limit.",
        "body": _say(
            "In 2026 the employee 401(k) limit is 24,500 dollars and the IRA limit is 7,500 dollars. The difference is 17,000 dollars.",
            "Both numbers are IRS ceilings for 2026. They are not a suggestion to contribute the full amount.",
            "The 17,000 dollar gap is the difference between two legal caps. It is not a return, and it is not money an employer has promised.",
            "The comparison fails if you have no workplace plan. Then the IRA cap is the one that applies, and the 24,500 dollar figure is not available.",
            "write the two caps on one line, 24,500 and 7,500, and circle the account you actually have.",
            "the Internal Revenue Service limits for 2026",
        ),
    },
    {
        "title": "At age 50 the 2026 401(k) catch-up is 8,000 dollars",
        "number": "$8,000",
        "source": "Internal Revenue Service, IR-2025-111. 24,500 plus 8,000 is 32,500.",
        "body": _say(
            "For 2026, a worker age 50 or older can add an 8,000 dollar catch-up on top of the 24,500 dollar employee limit. The total is 32,500 dollars.",
            "The 8,000 dollars is the catch-up the IRS listed for most 401(k) plans in 2026. The plan itself has to allow it.",
            "Ages 60 through 63 have a higher catch-up, 11,250 dollars, which is a different video. Employer money is also outside the 32,500 dollar employee total.",
            "The example fails under age 50. The extra 8,000 dollars is not available, and the employee ceiling stays 24,500 dollars.",
            "check the plan's catch-up line before changing a deferral. Age on December 31 of 2026 is the age that counts.",
            "Internal Revenue Service notice IR-2025-111",
        ),
    },
    {
        "title": "At ages 60 to 63 the 2026 catch-up is 11,250 dollars",
        "number": "$11,250",
        "source": "Internal Revenue Service, IR-2025-111, SECURE 2.0 higher catch-up.",
        "body": _say(
            "In 2026, a worker who is 60, 61, 62, or 63 can have a 401(k) catch-up of 11,250 dollars, instead of the 8,000 dollar catch-up used at other ages over 50.",
            "The 11,250 dollars replaces the 8,000 dollar catch-up for those four ages. It still sits on top of the 24,500 dollar employee limit when the plan allows it.",
            "It is not an extra 11,250 dollars on top of the 8,000. It is the higher of the two catch-up figures for those ages.",
            "The example fails at age 59 or age 64. Outside 60 through 63, the catch-up named for 2026 goes back to 8,000 dollars for ages 50 and older.",
            "read the age band on the plan notice before you type a deferral. The band is 60, 61, 62, and 63.",
            "Internal Revenue Service notice IR-2025-111",
        ),
    },
    {
        "title": "The 2026 defined-contribution cap is 72,000 dollars",
        "number": "$72,000",
        "source": "Internal Revenue Service, 2026 annual additions limit. Catch-up is outside this cap.",
        "body": _say(
            "For 2026, the annual additions cap on a defined-contribution plan is 72,000 dollars. That cap can include employee deferrals other than catch-up, plus employer money.",
            "The 72,000 dollar figure is the IRS overall additions limit for 2026. It is larger than the 24,500 dollar employee deferral because the employer can add money.",
            "Catch-up contributions are not part of this 72,000 dollar cap. A worker age 50 or older does not add the catch-up into the 72,000 and then call it over the line.",
            "The example fails when one employer’s plan, plus a related employer, is not the situation you have. The cap is per employer group, and your own notice controls.",
            "find the employer contribution on the last statement and add it to your own deferral, excluding catch-up. Compare that sum with 72,000 dollars.",
            "the Internal Revenue Service annual-additions limit for 2026",
        ),
    },
    {
        "title": "The 2026 SIMPLE IRA employee limit is 17,000 dollars",
        "number": "$17,000",
        "source": "Internal Revenue Service, 2026 SIMPLE IRA deferral limit.",
        "body": _say(
            "In 2026 the employee deferral limit for a SIMPLE IRA is generally 17,000 dollars.",
            "That 17,000 dollars is the employee cap the IRS listed for a SIMPLE IRA in 2026. It is not the 24,500 dollar cap used for a regular 401(k).",
            "The age-50 catch-up for a SIMPLE plan is a separate IRS figure. This video’s 17,000 dollars is the base employee limit.",
            "The example fails if the workplace plan is a regular 401(k). Then 17,000 dollars is the wrong ceiling, and the 401(k) limit is the one to read.",
            "look at the plan title on the statement. If it says SIMPLE, write 17,000 dollars next to last year’s employee deferral.",
            "the Internal Revenue Service SIMPLE IRA limit for 2026",
        ),
    },
    {
        "title": "Twenty percent down on a 300,000 dollar home is 60,000 dollars",
        "number": "$60,000",
        "source": "Consumer Financial Protection Bureau. Twenty percent of 300,000 is arithmetic. Mortgage insurance usually applies under 20 percent down.",
        "body": _say(
            "Twenty percent of a 300,000 dollar home price is 60,000 dollars.",
            "The 60,000 dollars is the down payment in this example. The Consumer Financial Protection Bureau says a down payment under 20 percent usually means you pay mortgage insurance.",
            "Closing costs are extra. They are not inside the 60,000 dollars.",
            "The example fails when the home price is not 300,000 dollars. Twenty percent of a different price is a different amount of cash.",
            "multiply the price you are actually considering by 0.20. Put that cash figure next to the 60,000 dollar example.",
            "the Consumer Financial Protection Bureau’s guide on down payments and mortgage insurance",
        ),
    },
    {
        "title": "Three percent down on a 300,000 dollar home is 9,000 dollars",
        "number": "$9,000",
        "source": "Consumer Financial Protection Bureau. Three percent of 300,000 is arithmetic. Some conventional loans can be 3 percent down.",
        "body": _say(
            "Three percent of a 300,000 dollar home price is 9,000 dollars.",
            "The Consumer Financial Protection Bureau says many loans need at least 3 percent down, and some conventional loans can be as low as 3 percent.",
            "The 9,000 dollars is not the full cash to close. Closing costs, often estimated at 2 to 5 percent of the price, sit on top.",
            "The example fails under 20 percent down, because mortgage insurance is then usually added to the monthly bill. A 3 percent down payment does not remove that cost.",
            "write 9,000 dollars, then add a closing-cost range of 6,000 to 15,000 dollars on this same 300,000 dollar price, and see the cash the example still leaves out.",
            "the Consumer Financial Protection Bureau’s down-payment guide",
        ),
    },
    {
        "title": "An FHA-style 3.5 percent down payment on 300,000 dollars is 10,500 dollars",
        "number": "$10,500",
        "source": "Consumer Financial Protection Bureau. FHA loans can be 3.5 percent down. 3.5 percent of 300,000 is 10,500.",
        "body": _say(
            "Three and a half percent of a 300,000 dollar home price is 10,500 dollars.",
            "The Consumer Financial Protection Bureau says an FHA loan can require as little as 3.5 percent down. FHA mortgage insurance is charged on FHA loans.",
            "The 10,500 dollars is the down payment in the example, not the upfront mortgage-insurance premium and not the closing costs.",
            "The example fails if you do not qualify for the 3.5 percent FHA option. A different loan has a different minimum.",
            "ask the loan estimate which down payment it used. Compare that cash figure with 10,500 dollars only if the price is 300,000 dollars.",
            "the Consumer Financial Protection Bureau’s description of FHA down payments",
        ),
    },
    {
        "title": "Closing costs of 2 to 5 percent on a 300,000 dollar home are 6,000 to 15,000 dollars",
        "number": "$6,000–$15,000",
        "source": "Consumer Financial Protection Bureau. Closing costs are typically 2 to 5 percent of the price, not including the down payment.",
        "body": _say(
            "On a 300,000 dollar home, 2 percent is 6,000 dollars and 5 percent is 15,000 dollars.",
            "The Consumer Financial Protection Bureau says closing costs typically fall in that 2 to 5 percent range, and the down payment is not part of it.",
            "The range covers lender charges, third-party fees, and some prepaid items. Your loan estimate is the list that replaces the range.",
            "The example fails in a county with a large transfer tax, or with a different price. The percent is a planning range, not your invoice.",
            "when a loan estimate arrives, add every buyer-paid line except the down payment. See whether the sum sits between 6,000 and 15,000 dollars.",
            "the Consumer Financial Protection Bureau’s closing-cost range",
        ),
    },
    {
        "title": "One point on a 300,000 dollar loan is 3,000 dollars",
        "number": "$3,000",
        "source": "Consumer Financial Protection Bureau. A point is a percent of the loan amount, paid up front.",
        "body": _say(
            "One percent of a 300,000 dollar loan is 3,000 dollars. That is one discount point in this example.",
            "The Consumer Financial Protection Bureau describes points as a charge, calculated as a percentage of the loan amount, that you can pay up front.",
            "The 3,000 dollars is cash at closing in the example. It is not the monthly principal and interest.",
            "The example fails when the loan amount is not 300,000 dollars, or when the lender’s point is not one percent. The loan estimate shows the points in dollars.",
            "find the points line on a loan estimate and divide it by the loan amount. See whether it matches the 3,000 dollars on 300,000.",
            "the Consumer Financial Protection Bureau’s explanation of points",
        ),
    },
    {
        "title": "A 300,000 dollar loan at 7.18 percent costs about 2,032 dollars a month",
        "number": "$2,032",
        "source": "Freddie Mac Primary Mortgage Market Survey, November 5, 2026, 30-year fixed average 7.18 percent. Payment is principal and interest on 300,000 dollars for 30 years.",
        "body": _say(
            "A 300,000 dollar loan for 30 years at 7.18 percent a year costs about 2,032 dollars a month in principal and interest.",
            "Freddie Mac’s survey for November 5, 2026 put the average 30-year fixed rate at 7.18 percent. The survey describes borrowers who put 20 percent down and have excellent credit.",
            "The 2,032 dollars leaves out property tax, home insurance, and mortgage insurance. Those are added on a real bill.",
            "The example fails if your rate is not 7.18 percent or the loan is not 300,000 dollars. A rate from last week is already a different average.",
            "write your own rate and loan amount beside 7.18 percent and 300,000 dollars. Do not treat 2,032 dollars as the payment you will see.",
            "Freddie Mac’s Primary Mortgage Market Survey dated November 5, 2026",
        ),
    },
    {
        "title": "The same 300,000 dollar loan for 15 years at 6.57 percent is about 2,625 dollars a month",
        "number": "$593",
        "source": "Freddie Mac, November 5, 2026: 15-year average 6.57 percent, 30-year average 7.18 percent. Payments are principal and interest on 300,000 dollars.",
        "body": _say(
            "The same 300,000 dollar loan for 15 years at 6.57 percent costs about 2,625 dollars a month. That is about 593 dollars a month more than the 30-year payment at 7.18 percent, about 2,032 dollars.",
            "Both rates are Freddie Mac averages for November 5, 2026. The 15-year loan ends sooner, so each month pays more principal.",
            "Neither figure includes tax or insurance. The 593 dollar gap is principal and interest only.",
            "The example fails if you cannot pay the higher month. A shorter loan that misses payments is not a saving.",
            "compare the two monthly figures with the cash left after rent-sized bills. If 2,625 dollars does not fit, the 15-year example is not your loan.",
            "Freddie Mac’s Primary Mortgage Market Survey dated November 5, 2026",
        ),
    },
    {
        "title": "A monthly mortgage bill has four parts",
        "number": "4",
        "source": "Consumer Financial Protection Bureau: principal, interest, mortgage insurance, and property tax plus homeowners insurance.",
        "body": _say(
            "A monthly mortgage payment can contain four parts: principal, interest, mortgage insurance, and the tax and insurance the lender escrows.",
            "The Consumer Financial Protection Bureau separates those parts. Principal and interest are the cost of the loan. Tax and homeowners insurance are the cost of owning the house.",
            "Mortgage insurance is usually there when the down payment is under 20 percent. It is not one of the four parts on every loan.",
            "The count of four fails when there is no mortgage insurance and no escrow. The bill can then show fewer lines, and the tax is still owed somewhere else.",
            "open one mortgage statement and label each line with one of the four names. Any line you cannot label is the one to ask the servicer about.",
            "the Consumer Financial Protection Bureau’s list of mortgage costs",
        ),
    },
    {
        "title": "A 4,000 dollar gross paycheck sends 306 dollars to Social Security and Medicare",
        "number": "$306",
        "source": "Employee FICA rates: 6.2 percent Social Security plus 1.45 percent Medicare, which is 7.65 percent. 7.65 percent of 4,000 is 306.",
        "body": _say(
            "On a 4,000 dollar gross paycheck, 7.65 percent is 306 dollars. That is 6.2 percent for Social Security and 1.45 percent for Medicare, the employee share.",
            "Gross means the pay before those taxes. This 4,000 dollar figure is not the take-home paycheck used in the 50, 30, 20 example.",
            "The extra 0.9 percent Medicare tax on high earners is not inside the 306 dollars. A 4,000 dollar paycheck does not reach that extra tax by itself.",
            "The example fails above the Social Security wage base, where the 6.2 percent stops for the rest of the year. The 1.45 percent Medicare tax does not use that same base.",
            "read the Social Security and Medicare lines on one pay stub and add them. See how far they sit from 306 dollars on a 4,000 dollar gross.",
            "the employee Social Security and Medicare tax rates",
        ),
    },
    {
        "title": "Six months of a 3,000 dollar bill is 18,000 dollars",
        "number": "$18,000",
        "source": "Consumer Financial Protection Bureau emergency-savings guidance. Six times 3,000 is arithmetic, for seasonal or uneven work.",
        "body": _say(
            "If the bills you must pay are 3,000 dollars a month, six months of those bills is 18,000 dollars.",
            "Three months would be 9,000 dollars. The six-month figure is the larger target for work that stops for part of the year, or for a job where one missed paycheck hits immediately.",
            "Restaurants, trips, and a new phone stay out of the 3,000 dollar month. The Consumer Financial Protection Bureau tells people to start with an amount they can reach.",
            "The example fails when 18,000 dollars is so large that nothing is saved. One month, 3,000 dollars, is the first target in that case.",
            "list rent, food at home, utilities, insurance, and debt minimums. If the work is seasonal, multiply that sum by six and compare it with 18,000 dollars.",
            "the Consumer Financial Protection Bureau’s emergency-savings guidance",
        ),
    },
    {
        "title": "The first emergency target can be one month, 3,000 dollars",
        "number": "$3,000",
        "source": "Consumer Financial Protection Bureau. One month of a 3,000 dollar example, before the 9,000 dollar target.",
        "body": _say(
            "One month of a 3,000 dollar necessary-bill example is 3,000 dollars. That is the first target when three months, 9,000 dollars, is too far away.",
            "The 3,000 dollars uses the same bills as the larger fund: rent or the mortgage, food cooked at home, utilities, insurance, and debt minimums.",
            "It is not a full emergency fund. It is the step in front of the 9,000 dollar example.",
            "The example fails if those necessary bills are not 3,000 dollars. Your list replaces the example before you move any money.",
            "add the five lines. If the total is near 3,000 dollars, move the first 50 dollars to a separate savings account only if the debt minimums are already paid.",
            "the Consumer Financial Protection Bureau’s note to start with an amount you can reach",
        ),
    },
    {
        "title": "Fifty dollars a month for ten years is 6,000 dollars of deposits",
        "number": "$6,000",
        "source": "Arithmetic: 50 dollars times 120 months. No investment return is included.",
        "body": _say(
            "Fifty dollars a month for ten years is 120 deposits. Fifty times 120 is 6,000 dollars of your own money.",
            "The 6,000 dollars counts only what you put in. It is the smaller version of the 200 dollar example, which is 24,000 dollars of deposits over the same 120 months.",
            "No interest, no fund, and no seven percent illustration is inside the 6,000 dollars. Adding a return would be a different number, and it would be a guess.",
            "The example fails when fifty dollars is taken from a credit-card minimum. The minimum stays paid. The fifty dollars has to be money that is actually free.",
            "set a transfer for the day after payday only at a number you can keep for six months. If that number is 50 dollars, the ten-year deposit total in this example is 6,000 dollars.",
            "the deposit arithmetic, 50 times 120",
        ),
    },
    {
        "title": "A 25 dollar minimum on a 1,000 dollar card cuts about 8 dollars of principal",
        "number": "$8.33",
        "source": "Example only: 1,000 dollars at 20 percent a year. One month of interest is about 16.67 dollars. A 25 dollar minimum leaves about 8.33 dollars of principal.",
        "body": _say(
            "On a 1,000 dollar balance at 20 percent a year, one month of interest is about 16 dollars and 67 cents. A 25 dollar minimum then reduces the balance by about 8 dollars and 33 cents.",
            "Twenty percent divided by twelve is the month rate in the example. One thousand times that month rate is about 16.67 dollars.",
            "The 25 dollar minimum is the example’s required payment, not a minimum printed on your statement. Your statement wins.",
            "The example fails when the APR is not 20 percent. A 14 percent card and a 29 percent card do not leave 8.33 dollars of principal on a 25 dollar payment.",
            "write your balance, your APR, and your minimum. Divide the APR by twelve, multiply by the balance, and subtract that interest from the minimum.",
            "the card’s own Truth in Lending disclosure. The 20 percent and the 25 dollars are an example",
        ),
    },
    {
        "title": "Adding 100 dollars to a 25 dollar minimum knocks about 108 dollars off the balance",
        "number": "$108",
        "source": "Same example: 1,000 dollars at 20 percent. Interest about 16.67 dollars. A 125 dollar payment leaves about 108 dollars of principal.",
        "body": _say(
            "In the same example, you pay the 25 dollar minimum and add 100 dollars. After about 16 dollars and 67 cents of interest, about 108 dollars comes off the 1,000 dollar balance.",
            "The payment in the example is 125 dollars. The interest is still balance times 20 percent divided by twelve.",
            "The extra 100 dollars is extra. It does not replace the minimum on this card or on any other card.",
            "The example fails if paying the extra 100 dollars means skipping a minimum somewhere else. A missed minimum can trigger a penalty rate.",
            "put the extra amount, even if it is smaller than 100 dollars, on autopay only after every minimum is already covered.",
            "the same example APR of 20 percent. Your statement is the rate to use",
        ),
    },
    {
        "title": "Rent of 1,800 dollars leaves 200 dollars inside a 2,000 dollar needs slice",
        "number": "$200",
        "source": "The 50/30/20 illustration on a 4,000 dollar take-home paycheck. Needs are 2,000 dollars. 2,000 minus 1,800 is 200.",
        "body": _say(
            "On a 4,000 dollar take-home paycheck, the needs slice in the 50, 30, 20 example is 2,000 dollars. Rent of 1,800 dollars leaves 200 dollars for food, utilities, and insurance.",
            "Take-home means after taxes. The 1,800 dollar rent is an example of a bill that almost fills the needs slice.",
            "Wants stay in the 1,200 dollar slice of that same paycheck. They do not get the 200 dollars that were meant for food and power.",
            "The poster fails in this city. When rent is 1,800 dollars, pretending the remaining needs still fit is the mistake. Wants have to shrink, or the housing cost has to.",
            "write rent on the first line and subtract it from half of take-home pay. If the remainder looks like 200 dollars, the example has already told you the split does not fit.",
            "the 50/30/20 household illustration. It is not the tax code",
        ),
    },
    {
        "title": "Four supermarket receipts divided by four are your grocery week",
        "number": "4",
        "source": "Your receipts. The Bureau of Labor Statistics publishes the national price indexes, which are not this personal average.",
        "body": _say(
            "Add the last four supermarket receipts and divide by four. That quotient is your grocery week. A 150 dollar example week is 600 dollars in a four-week month, and it is only an example.",
            "Restaurant meals stay out of the four receipts. They hide the grocery line.",
            "The national inflation index from the Bureau of Labor Statistics is not the average of your four receipts. One is the country’s price measure. The other is the bill you can change.",
            "The example fails when a receipt mixes clothes, medicine, and food. Pull the food lines out before you divide.",
            "label the note with the four-receipt average. The next time a briefing mentions prices, compare it with that note.",
            "your own supermarket receipts, with the national index left to the Bureau of Labor Statistics",
        ),
    },
    {
        "title": "Mortgage insurance usually starts when the down payment is under 60,000 dollars on a 300,000 dollar home",
        "number": "$60,000",
        "source": "Consumer Financial Protection Bureau. Under 20 percent down, mortgage insurance is typically required. Twenty percent of 300,000 is 60,000.",
        "body": _say(
            "On a 300,000 dollar home, 20 percent down is 60,000 dollars. Under that cash amount, mortgage insurance is typically added.",
            "The Consumer Financial Protection Bureau says borrowers who put down less than 20 percent usually pay mortgage insurance. FHA loans charge it as well.",
            "The insurance protects the lender. It is added to closing costs, the monthly payment, or both. It is not part of the home’s price.",
            "The 60,000 dollar line fails when the price is not 300,000 dollars. Recompute 20 percent of the price on the contract before you assume the insurance disappears.",
            "on the loan estimate, look for a mortgage-insurance line. If the down payment is under 20 percent, expect that line to be filled in.",
            "the Consumer Financial Protection Bureau’s explanation of mortgage insurance",
        ),
    },
]
