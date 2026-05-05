import re
from dataclasses import dataclass

@dataclass
class Verdict:
    blocked: bool
    category: str | None
    message: str

BLOCK_PATTERNS: dict[str, list[str]] = {
    "insider_trading": [
        r"i (work|worked) at .+ and know",
        r"my friend at \w+ gave me a tip",
        r"(confidential|non.public) (merger|acquisition|earnings|news)",
        r"(buy|sell|trade|load up).{0,30}before.{0,20}(announcement|call|report)",
        r"earnings before.{0,20}(announcement|call)",
        r"tip (about|on) earnings",
    ],
    "market_manipulation": [
        r"pump (up|the price)",
        r"wash trad(e|ing)",
        r"coordinated (buying|trading) scheme",
        r"move (this|the) stock",
        r"create (fake |false )?(volume|activity)",
    ],
    "money_laundering": [
        r"without reporting it",
        r"structure deposits.{0,20}avoid",
        r"avoid the 10k? reporting",
        r"(layer|obscure).{0,20}(source of|funds|trades)",
        r"hide (trading )?profits from",
    ],
    "guaranteed_returns": [
        r"guarantee me.{0,20}(return|profit)",
        r"promise me.{0,20}(double|return|profit)",
        r"100% (certain|sure|guaranteed).{0,20}(go up|return)",
        r"foolproof way to make",
    ],
    "reckless_advice": [
        r"(all|entire|everything).{0,30}(retirement|savings|emergency fund).{0,20}(crypto|options)",
        r"(entire|all).{0,20}emergency fund.{0,20}(options|crypto)",
        r"margin loan.{0,20}(buy|invest)",
        r"mortgage my house.{0,20}(stock|invest|buy)",
        r"put (all|everything).{0,20}(into|in) (crypto|options)",
    ],
    "sanctions_evasion": [
        r"bypass (ofac|sanctions)",
        r"shell company.{0,20}bypass",
        r"invest in.{0,20}sanctioned",
        r"without (it being )?traced",
    ],
    "fraud": [
        r"fake (contract|document|note)",
        r"(draft|create).{0,20}fake",
        r"fabricate.{0,20}(document|record|loss)",
    ],
}

BLOCK_MESSAGES = {
    "insider_trading": "This is insider trading and is illegal under securities law.",
    "market_manipulation": "I can't assist with artificially moving stock prices or creating fake trading volume.",
    "money_laundering": "I can't help with hiding money, avoiding reporting requirements, or concealing ",
    "guaranteed_returns": "I can't guarantee investment returns or promise profits. No investment is risk-free ",
    "reckless_advice": "I can't recommend putting all your savings into a single risky asset, taking margin ",
    "sanctions_evasion": "I can't help with bypassing OFAC sanctions or investing in sanctioned entities. ",
    "fraud": "I can't help create fake financial documents or falsified records."
}

def check(query: str) -> Verdict:
    query_lower = query.lower()

    for category, patterns in BLOCK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return Verdict(
                    blocked=True,
                    category=category,
                    message=BLOCK_MESSAGES[category],
                )

    return Verdict(blocked=False, category=None, message="")