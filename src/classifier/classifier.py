from typing import TypedDict, Optional
from src.classifier.schema import Output
from src.classifier.graph import build_classifier_graph

def classify(
        query: str,
        prior_turns: Optional[list[str]] = None,
        llm=None,
    ) -> Output:

    classifier_graph = build_classifier_graph(llm=llm)

    result = classifier_graph.invoke({
        "query": query,
        "prior_turns": prior_turns or [],
        "messages": [],
        "raw_result": {},
        "output": None,
        "failed": False,
    })

    return result["output"]