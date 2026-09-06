from functools import lru_cache


class LocalEmbeddings:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load_model().encode(texts, normalize_embeddings=True)
        return vectors.tolist()


@lru_cache
def get_embeddings() -> LocalEmbeddings:
    return LocalEmbeddings()
