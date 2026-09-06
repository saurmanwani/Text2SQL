from app.pipeline.state import PipelineState


def retrieve_examples(state: PipelineState) -> dict[str, object]:
    store = state.get("knowledge_store")
    if store is None:
        return {"examples": [], "grounded_on": []}
    examples = store.query_examples(
        state["connection_id"],
        state["question"],
        limit=3,
    )
    return {
        "examples": examples,
        "grounded_on": [int(example["id"]) for example in examples],
    }
