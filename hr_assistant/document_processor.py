import os
import tempfile
import hashlib
from zipfile import ZipFile
from typing import List, Tuple, Dict, Any
from markitdown import MarkItDown
from langchain_core.documents import Document
from hr_assistant.semantic_chunking import SemanticChunkerProcessor

class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {
        ".pdf": "document",
        ".docx": "document",
        ".doc": "document",
        ".txt": "document",
        ".md": "document",
        ".zip": "archive"
    }

    def __init__(self, db, docs_dir="resumes"):
        self.db = db
        self.docs_dir = docs_dir
        self.md_converter = MarkItDown()

    def get_document_metadata(self, file_path: str) -> Dict[str, Any]:
        """Estrae i metadati di base e calcola l'hash del file per il tracciamento."""
        stat = os.stat(file_path)
        file_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
        
        return {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "size": stat.st_size,
            "hash": file_hash.hexdigest(),
            "modified_time": stat.st_mtime
        }

    def _process_zip_file(self, file_path: str) -> List[Tuple[str, str]]:
        """Processa il contenuto dei file ZIP estraendoli temporaneamente."""
        results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        sub_file_path = os.path.join(root, file)
                        ext = os.path.splitext(file)[1].lower()
                        if ext in self.SUPPORTED_EXTENSIONS:
                            content = self._convert_to_markdown(sub_file_path)
                            if content:
                                results.append((file, content))
        return results

    def _convert_to_markdown(self, file_path: str) -> str:
        """Converte qualsiasi file supportato in Markdown usando MarkItDown."""
        try:
            result = self.md_converter.convert(file_path)
            return result.text_content if result else ""
        except Exception as e:
            print(f"Errore nella conversione del file {file_path}: {str(e)}")
            return ""

    def process_single_document(self, file_path: str) -> Tuple[List[str], List[Dict], List[str]]:
        """Processa un singolo documento (o archivio ZIP) in chunk semantici pronti per il vector DB."""
        documents = []
        metadatas = []
        ids = []

        extension = os.path.splitext(file_path)[1].lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(extension)

        if not file_type:
            return [], [], []

        content = ""
        if file_type == "archive":
            zip_contents = self._process_zip_file(file_path)
            for filename, zip_content in zip_contents:
                if zip_content:
                    content += f"\n\nFile: {filename}\n{zip_content}"
        else:
            content = self._convert_to_markdown(file_path)

        if not content:
            return [], [], []

        # Applicazione del Semantic Chunking basato sul modulo del professore
        chunks = SemanticChunkerProcessor.chunk_it(content)

        base_filename = os.path.basename(file_path)
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source": base_filename, "file_path": file_path, "chunk_index": i})
            ids.append(f"{base_filename}_chunk_{i}")

        return documents, metadatas, ids

    def sync_documents(self):
        """Sincronizzazione intelligente dei documenti basata su aggiunte, aggiornamenti e rimozioni."""
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)
            return

        current_files = {}
        for f in os.listdir(self.docs_dir):
            ext = os.path.splitext(f)[1].lower()
            if ext in self.SUPPORTED_EXTENSIONS:
                full_path = os.path.join(self.docs_dir, f)
                if os.path.isfile(full_path):
                    current_files[f] = self.get_document_metadata(full_path)

        existing_files = {}
        if hasattr(self.db, "get_tracked_files"):
            existing_files = self.db.get_tracked_files()

        files_to_add = set(current_files.keys()) - set(existing_files.keys())
        files_to_remove = set(existing_files.keys()) - set(current_files.keys())
        
        files_to_update = {
            f for f in (set(current_files.keys()) & set(existing_files.keys()))
            if current_files[f]["hash"] != existing_files[f].get("hash")
        }

        if not hasattr(self.db, "get_tracked_files"):
            files_to_add = set(current_files.keys())
            files_to_update = set()
            files_to_remove = set()

        for filename in files_to_remove:
            if hasattr(self.db, "remove_document_by_source"):
                self.db.remove_document_by_source(filename)

        for action, filenames in [("add", files_to_add), ("update", files_to_update)]:
            for filename in filenames:
                file_path = current_files[filename]["file_path"]
                
                if action == "update" and hasattr(self.db, "remove_document_by_source"):
                    self.db.remove_document_by_source(filename)

                docs, metas, ids = self.process_single_document(file_path)
                if docs:
                    # Inserimento sicuro e compatibile con qualsiasi interfaccia del Database custom
                    if hasattr(self.db, "add_chunks_with_ids"):
                        self.db.add_chunks_with_ids(docs, metas, ids)
                    elif hasattr(self.db, "add_documents"):
                        self.db.add_documents([Document(page_content=d, metadata=m) for d, m in zip(docs, metas)])
                    else:
                        for d, m, i in zip(docs, metas, ids):
                            if hasattr(self.db, "add_chunk"):
                                self.db.add_chunk(d, m, i)