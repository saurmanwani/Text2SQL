from app.knowledge.retrieval import select_relevant_schema
from app.knowledge.visibility import filter_schema
from app.pipeline.state import PipelineState


def load_schema(state: PipelineState) -> dict[str, object]:
    schema = state["connector"].get_schema()
    annotation_map = {
        (item.table_name, item.column_name): item.description
        for item in state.get("annotations", [])
    }
    for table in schema.tables:
        table.description = annotation_map.get((table.name, None), "")
        for column in table.columns:
            column.description = annotation_map.get((table.name, column.name), "")
    visible_schema = filter_schema(schema, state["role"], state.get("permissions", []))
    store = state.get("knowledge_store")
    if len(visible_schema.tables) > 15 and store is not None:
        retrieved = store.query_tables(
            state["connection_id"],
            state["question"],
            limit=8,
        )
        if retrieved:
            visible_schema = select_relevant_schema(visible_schema, retrieved)
    lines = []
    for table in visible_schema.tables:
        columns = []
        for column in table.columns:
            hints = []
            if column.primary_key:
                hints.append("pk")
            if column.foreign_key_targets:
                hints.append(f"fk->{','.join(column.foreign_key_targets)}")
            suffix = f" ({'; '.join(hints)})" if hints else ""
            description = f" — {column.description}" if column.description else ""
            columns.append(f"{column.name} {column.type}{suffix}{description}")
        table_description = f" — {table.description}" if table.description else ""
        lines.append(f"{table.name}{table_description}: {', '.join(columns)}")
    return {
        "dialect": state["connector"].dialect,
        "schema_text": "\n".join(lines),
        "schema_tables": [table.name for table in visible_schema.tables],
    }
