from app.knowledge.visibility import filter_schema
from app.pipeline.state import PipelineState


def load_schema(state: PipelineState) -> dict[str, object]:
    schema = state["connector"].get_schema()
    visible_schema = filter_schema(schema, state["role"], state.get("permissions", []))
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
            columns.append(f"{column.name} {column.type}{suffix}")
        lines.append(f"{table.name}: {', '.join(columns)}")
    return {
        "dialect": state["connector"].dialect,
        "schema_text": "\n".join(lines),
        "schema_tables": [table.name for table in visible_schema.tables],
    }
