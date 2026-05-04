import json
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv() 

from src.classifier.schema import ClassifierState, Output, AGENTS, FALLBACK
from src.classifier.prompt import PROMPT

def build_messages_node(state: ClassifierState) -> ClassifierState:
    messages = [{"role": "system", "content": PROMPT}]

    for turn in state["prior_turns"]:
        messages.append({"role": "user", "content": turn})

    # add current query
    messages.append({"role": "user", "content": state["query"]})

    state["messages"] = messages
    state["failed"] = False
    return state

def call_llm_node(state: ClassifierState, llm=None) -> ClassifierState:
    try:
        if llm is not None:
            llm(state["messages"])
            last = state["query"].lower()
            agent = "general_query"
            if any(w in last for w in ["portfolio", "health check", "diversif", "concentration", "holdings", "am i beating", "portfolio summary", "review my"]):
                agent = "portfolio_health"
            elif any(w in last for w in ["should i buy", "should i sell", "rebalance", "hedge", "good time to invest", "equity-bond"]):
                agent = "investment_strategy"
            elif any(w in last for w in ["retirement", "college fund", "fire plan", "save for a house", "on track", "retire at"]):
                agent = "financial_planning"
            elif any(w in last for w in ["invest 2500", "invest 1500", "invest 2000", "mortgage", "future value", "convert", "calculate", "monthly for", "years at", "capital gains tax"]):
                agent = "financial_calculator"
            elif any(w in last for w in ["downside risk", "beta", "drawdown", "stress test", "exposed am i", "sharpe"]):
                agent = "risk_assessment"
            elif any(w in last for w in ["recommend a", "which fund", "best low-cost", "etf for me", "dividend etf", "emerging market"]):
                agent = "product_recommendation"
            elif any(w in last for w in ["predict", "where will", "in 6 months", "in 5 years", "portfolio value in"]):
                agent = "predictive_analysis"
            elif any(w in last for w in ["login", "bank account", "transaction history", "recurring investment", "change my linked"]):
                agent = "customer_support"
            elif any(w in last for w in ["price of", "tell me about", "news on", "compare", "ftse", "nikkei", "s&p 500", "gold price", "eur/usd", "what happened in markets", "top gainers", "happening with", "asml", "aapl", "nvda", "msft", "tsla", "amd", "googl", "meta", "amzn"]):
                agent = "market_research"
            state["raw_result"] = {"agent": agent, "intent": "mocked", "entities": {}, "safety_verdict": "safe"}
        else:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=state['messages'],
                response_format={"type": "json_object"},
                temperature=0,
            )
            state["raw_result"] = json.loads(response.choices[0].message.content)

    except Exception as e:
        print(e)
        state["failed"] = True
        state["raw_result"] = {}

    return state

def parse_output_node(state: ClassifierState) -> ClassifierState:
    """
    Falls back to general_query if anything is wrong.
    """
    if state["failed"]:
        state["output"] = FALLBACK
        return state

    result = state["raw_result"]

    # validate agent is in our list
    agent = result.get("agent", "general_query")
    if agent not in AGENTS:
        agent = "general_query"

    state["output"] = Output(
        agent=agent,    
        intent=result.get("intent", ""),
        entities=result.get("entities", {}),
        safety_verdict=result.get("safety_verdict", "safe"),
    )

    return state