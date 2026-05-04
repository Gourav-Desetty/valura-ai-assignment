from langgraph.graph import StateGraph, END

from src.classifier.schema import ClassifierState
from src.classifier.nodes import build_messages_node, call_llm_node, parse_output_node


def build_classifier_graph(llm=None):
    """
    Flow:
        build_messages → call_llm → parse_output → END
    """
    graph = StateGraph(ClassifierState)

    # add nodes
    graph.add_node("build_messages", build_messages_node)

    # bind llm to call_llm_node so mock can be injected in tests
    graph.add_node(
        "call_llm",
        lambda state: call_llm_node(state, llm=llm)
    )

    graph.add_node("parse_output", parse_output_node)

    # add edges - linear flow
    graph.set_entry_point("build_messages")
    graph.add_edge("build_messages", "call_llm")
    graph.add_edge("call_llm", "parse_output")
    graph.add_edge("parse_output", END)

    return graph.compile()