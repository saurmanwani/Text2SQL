from langgraph.graph import END, START, StateGraph

from app.pipeline.nodes.execute_sql import execute_sql
from app.pipeline.nodes.followups import followups
from app.pipeline.nodes.generate_sql import generate_sql
from app.pipeline.nodes.handle_unanswerable import handle_unanswerable
from app.pipeline.nodes.load_schema import load_schema
from app.pipeline.nodes.summarize import summarize
from app.pipeline.nodes.validate_sql import validate_sql
from app.pipeline.state import PipelineState


def route_after_validation(state: PipelineState) -> str:
    if state.get("unanswerable"):
        return "handle_unanswerable"
    validation = state["validation"]
    if validation.ok:
        return "execute_sql"
    if validation.reason == "table_not_allowed":
        return "handle_unanswerable"
    if state.get("attempt", 0) < state["max_attempts"]:
        return "generate_sql"
    return "handle_unanswerable"


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("load_schema", load_schema)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("summarize", summarize)
    graph.add_node("generate_followups", followups)
    graph.add_node("handle_unanswerable", handle_unanswerable)

    graph.add_edge(START, "load_schema")
    graph.add_edge("load_schema", "generate_sql")
    graph.add_edge("load_schema", "generate_followups")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges("validate_sql", route_after_validation)
    graph.add_edge("execute_sql", "summarize")
    graph.add_edge("summarize", END)
    graph.add_edge("generate_followups", END)
    graph.add_edge("handle_unanswerable", END)
    return graph.compile()
