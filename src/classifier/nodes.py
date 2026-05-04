import json
import os

from openai import OpenAI
# from google import genai as google_genai
from groq import Groq
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
            # test path - mock LLM
            state["raw_result"] = llm(state["messages"])
        else:
            # real path - OpenAI
            # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # response = client.chat.completions.create(
            #     model="gpt-4o-mini",
            #     messages=state['messages'],
            #     response_format={"type": "json_object"},  # forces valid JSON
            #     temperature=0,
            # )
            # state["raw_result"] = json.loads(
            #     response.choices[0].message.content
            # )
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=state["messages"],
                response_format={"type": "json_object"},
                temperature=0,
            )
            state["raw_result"] = json.loads(
                response.choices[0].message.content
            )

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