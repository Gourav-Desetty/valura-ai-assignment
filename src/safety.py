import re
from dataclasses import dataclass

@dataclass
class Verdict:
    blocked: bool
    category: str | None
    message: str

BLOCKED_KEYWORDS = {
    "insider_trading":[
        "unannounced acquisition",
        "tip about earnings",
        "confidential merger",
        "before tomorrow's announcement",
        "before the call",
        "confidential news",
        "insider tip",
        "load up before",
        "i work at",
        "my friend at",
    ],
    "market_manipulation": [
        "pump up",
        "coordinated buying scheme",
        "wash trade",
        "move this stock",
        "create volume",
    ],
    "money_laundering":[
        "without reporting it",
        "structure deposits to avoid",
        "avoid the 10k reporting threshold",
        "layer my trades to obscure",
        "obscure the source",
        "from the tax authorities",
        "hide trading profits"
    ],
    "guaranteed_returns":[
        "guarantee me",
        "promise me my money",
        "my money will double",
        "100% certain to go up",
        "foolproof way to make",
    ],
    "reckless_advice":[
        "all my retirement savings in crypto",
        "take a margin loan to buy",
        "my entire emergency fund into options",
        "which stock to mortgage my house",
    ],
    "sanctions_evasion": [
        "bypass ofac sanctions",
        "shell company to bypass",
        "without it being traced",
        "sanctioned russian company",
        "invest in a sanctioned",
    ],
    "fraud": [
        "fake contract note",
        "draft a fake",
        "fabricate",
        "falsified document",
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

    for category, keywords in BLOCKED_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                return Verdict(
                    blocked=True,
                    category=category,
                    message=BLOCK_MESSAGES[category]
                )
    return Verdict(blocked=False, category=None, message="")