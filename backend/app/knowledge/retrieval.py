from app.connectors.base import SchemaModel


def select_relevant_schema(
    schema: SchemaModel,
    retrieved_tables: list[str],
    *,
    full_schema_threshold: int = 15,
    max_tables: int = 10,
) -> SchemaModel:
    if len(schema.tables) <= full_schema_threshold:
        return schema

    by_name = {table.name: table for table in schema.tables}
    selected = [name for name in retrieved_tables if name in by_name]
    for table_name in list(selected):
        for column in by_name[table_name].columns:
            for target in column.foreign_key_targets:
                linked_table = target.partition(".")[0]
                if linked_table in by_name and linked_table not in selected:
                    selected.append(linked_table)
    return SchemaModel(tables=[by_name[name] for name in selected[:max_tables]])
