from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.connectors.base import SchemaModel
from app.db.models import SchemaAnnotation, VerifiedExample
from app.knowledge.embeddings import LocalEmbeddings, get_embeddings
from app.settings import get_settings


class KnowledgeStore:
    def __init__(
        self,
        persist_directory: str,
        embeddings: LocalEmbeddings | None = None,
    ) -> None:
        import chromadb

        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embeddings = embeddings or get_embeddings()

    def reindex_schema(
        self,
        connection_id: int,
        schema: SchemaModel,
        annotations: list[SchemaAnnotation],
    ) -> None:
        name = f"schema_{connection_id}"
        self._reset_collection(name)
        collection = self.client.get_or_create_collection(name)
        annotation_map = {
            (item.table_name, item.column_name): item.description for item in annotations
        }
        documents: list[str] = []
        identifiers: list[str] = []
        metadata: list[dict[str, str]] = []
        for table in schema.tables:
            table_description = annotation_map.get((table.name, None), "")
            column_text = ", ".join(f"{column.name} {column.type}" for column in table.columns)
            documents.append(f"{table.name}: {column_text}. {table_description}".strip())
            identifiers.append(f"table:{table.name}")
            metadata.append({"table": table.name, "kind": "table"})
            for column in table.columns:
                description = annotation_map.get((table.name, column.name), "")
                if description:
                    documents.append(
                        f"{table.name}.{column.name} {column.type}: {description}"
                    )
                    identifiers.append(f"column:{table.name}:{column.name}")
                    metadata.append(
                        {"table": table.name, "column": column.name, "kind": "column"}
                    )
        if documents:
            collection.upsert(
                ids=identifiers,
                documents=documents,
                metadatas=metadata,
                embeddings=self.embeddings.embed(documents),
            )

    def query_tables(self, connection_id: int, question: str, limit: int = 8) -> list[str]:
        collection = self.client.get_or_create_collection(f"schema_{connection_id}")
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=self.embeddings.embed([question]),
            n_results=min(limit, collection.count()),
            include=["metadatas"],
        )
        tables: list[str] = []
        for item in (result.get("metadatas") or [[]])[0]:
            if item and (table := item.get("table")) and table not in tables:
                tables.append(str(table))
        return tables

    def upsert_example(self, example: VerifiedExample) -> None:
        collection = self.client.get_or_create_collection(
            f"examples_{example.connection_id}"
        )
        document = f"Question: {example.question}\nSQL: {example.sql}"
        collection.upsert(
            ids=[str(example.id)],
            documents=[document],
            metadatas=[{"question": example.question, "sql": example.sql}],
            embeddings=self.embeddings.embed([example.question]),
        )

    def query_examples(
        self,
        connection_id: int,
        question: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        collection = self.client.get_or_create_collection(f"examples_{connection_id}")
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=self.embeddings.embed([question]),
            n_results=min(limit, collection.count()),
            include=["metadatas"],
        )
        ids = (result.get("ids") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [
            {"id": int(identifier), **(metadata or {})}
            for identifier, metadata in zip(ids, metadatas, strict=False)
        ]

    def delete_example(self, connection_id: int, example_id: int) -> None:
        collection = self.client.get_or_create_collection(f"examples_{connection_id}")
        collection.delete(ids=[str(example_id)])

    def _reset_collection(self, name: str) -> None:
        with suppress(ValueError):
            self.client.delete_collection(name)


@lru_cache
def get_knowledge_store() -> KnowledgeStore:
    return KnowledgeStore(get_settings().chroma_persist_directory)
