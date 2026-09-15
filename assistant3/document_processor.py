import os
import hashlib
from pathlib import Path
from langchain_community.document_loaders import UnstructuredFileLoader
from assistant3.config import RESUMES_DIR
from assistant3.database import Database
from assistant3.semantic_chunking import SemanticChunkerProcessor

def calculate_file_hash(file_path: Path) -> str:
    """Calcola l'hash SHA-256 del contenuto del file per tracciarne le modifiche."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_text_from_file(file_path: Path) -> str:
    """Estrae il testo da qualsiasi formato supportato da Unstructured (PDF, DOCX, TXT, ecc.)."""
    try:
        loader = UnstructuredFileLoader(str(file_path))
        docs = loader.load()
        return "\n".join([doc.page_content for doc in docs])
    except Exception as e:
        print(f"[ERROR] Impossibile estrarre il testo dal file {file_path.name}: {e}")
        return ""

class DocumentProcessor:
    def __init__(self, db: Database):
        self.collection = db.get_collection()

    @staticmethod
    def get_document_metadata(file_path: str, file_hash: str) -> dict:
        """Estrae i metadati di base per il singolo documento."""
        return {
            "source": os.path.basename(file_path),
            "file_hash": file_hash
        }

    def sync_documents(self):
        """Sincronizza la cartella resumes/ con ChromaDB supportando formati multipli."""
        print(f"\n[DEBUG] Controllo cartella resumes in corso...")
        print(f"[DEBUG] Percorso assoluto cercato: {RESUMES_DIR.resolve()}")
        
        if not RESUMES_DIR.exists():
            print(f"[DEBUG] La cartella non esiste. La creo adesso...")
            RESUMES_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] Cartella creata, ma è vuota.")
            return
        
        # Estensioni supportate in modo esteso
        supported_extensions = {".txt", ".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".csv", ".md"}
        local_files = {
            f.name: f for f in RESUMES_DIR.iterdir() 
            if f.is_file() and f.suffix.lower() in supported_extensions
        }
        print(f"[DEBUG] File compatibili trovati nella cartella: {list(local_files.keys())}")
        
        local_file_names = set(local_files.keys())

        existing_data = self.collection.get(include=["metadatas"])
        existing_metadatas = existing_data.get("metadatas", [])
        existing_ids = existing_data.get("ids", [])

        db_files_info = {}
        file_to_chunk_ids = {}

        for chunk_id, meta in zip(existing_ids, existing_metadatas):
            if meta and "source" in meta:
                source = meta["source"]
                file_hash = meta.get("file_hash", "")
                db_files_info[source] = file_hash
                file_to_chunk_ids.setdefault(source, []).append(chunk_id)

        db_file_names = set(db_files_info.keys())

        added_files = local_file_names - db_file_names
        removed_files = db_file_names - local_file_names
        
        common_files = local_file_names.intersection(db_file_names)
        updated_files = set()
        for filename in common_files:
            file_path = local_files[filename]
            current_hash = calculate_file_hash(file_path)
            if current_hash != db_files_info.get(filename):
                updated_files.add(filename)

        files_to_remove = removed_files.union(updated_files)
        for filename in files_to_remove:
            ids_to_delete = file_to_chunk_ids.get(filename, [])
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)

        files_to_add = added_files.union(updated_files)
        for filename in files_to_add:
            file_path = local_files[filename]
            current_hash = calculate_file_hash(file_path)
            
            content = extract_text_from_file(file_path)
            if not content.strip():
                print(f"[WARNING] Il file '{filename}' è vuoto o non leggibile.")
                continue

            chunks = SemanticChunkerProcessor.chunk_it(content)
            print(f"[DEBUG] File '{filename}' suddiviso in {len(chunks)} chunk semantici.")

            documents = []
            ids = []
            metadata_list = []

            for idx, chunk in enumerate(chunks):
                if chunk and not chunk.isspace():
                    chunk_id = f"{filename}_chunk_{idx}"
                    documents.append(chunk)
                    ids.append(chunk_id)
                    metadata_list.append(self.get_document_metadata(str(file_path), current_hash))

            if documents:
                self.collection.add(
                    documents=documents,
                    ids=ids,
                    metadatas=metadata_list
                )
                print(f"[DEBUG] Salvati con successo {len(documents)} chunk per il file '{filename}'.\n")