from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from assistant3.config import CHROMA_DIR, OPENAI_API_KEY

class Database:
    def __init__(self):
        """Inizializza gli embedding di OpenAI e il vector store ChromaDB."""
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=self.embeddings
        )

    def get_collection(self):
        """Restituisce la collezione sottostante di ChromaDB (utile per conteggi e statistiche)."""
        try:
            return self.vectorstore._collection
        except Exception:
            return None

    def delete_collection(self):
        """Elimina interamente la collezione dal database."""
        try:
            self.vectorstore.delete_collection()
        except Exception:
            pass