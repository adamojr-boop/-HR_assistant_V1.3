import chromadb
from pathlib import Path
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from hr_assistant.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL

class Database:
    def __init__(
        self,
        collection_name="hr_resumes_openai",
        persist_directory: str = "./chroma_db",
    ):
        """Inizializza un database ChromaDB persistente su disco per il vero recupero semantico."""
        self.persist_path = Path(persist_directory)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name=OPENAI_EMBEDDING_MODEL,
        )
        self._collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"embedding_model": OPENAI_EMBEDDING_MODEL},
        )

    def get_or_create_collection(self, name=None):
        if name and name != self._collection.name:
            return self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={"embedding_model": OPENAI_EMBEDDING_MODEL},
            )
        return self._collection

    def get_collection(self):
        return self._collection

    def add_chunks_with_ids(self, documents, metadatas, ids):
        self._collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def remove_document_by_source(self, source: str):
        self._collection.delete(where={"source": source})

    def get_tracked_files(self):
        result = self._collection.get(include=["metadatas"])
        tracked_files = {}

        for metadata in result["metadatas"] or []:
            source = metadata.get("source")
            if source:
                tracked_files[source] = {"hash": metadata.get("hash")}

        return tracked_files