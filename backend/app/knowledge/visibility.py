from collections.abc import Iterable

from app.connectors.base import SchemaModel, TableModel
from app.db.models import SchemaPermission


def filter_schema(
    schema: SchemaModel,
    role: str,
    permissions: Iterable[SchemaPermission],
) -> SchemaModel:
    if role == "admin":
        return schema.model_copy(deep=True)

    role_permissions = [permission for permission in permissions if permission.role == role]
    hidden_tables = {
        permission.table_name
        for permission in role_permissions
        if permission.column_name is None and not permission.visible
    }
    hidden_columns = {
        (permission.table_name, permission.column_name)
        for permission in role_permissions
        if permission.column_name is not None and not permission.visible
    }

    tables: list[TableModel] = []
    for table in schema.tables:
        if table.name in hidden_tables:
            continue
        visible_columns = [
            column
            for column in table.columns
            if (table.name, column.name) not in hidden_columns
        ]
        tables.append(table.model_copy(update={"columns": visible_columns}, deep=True))
    return SchemaModel(tables=tables)
