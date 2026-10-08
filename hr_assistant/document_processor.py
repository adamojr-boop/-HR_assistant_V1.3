import os
from markitdown import MarkItDown
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self, db, docs_dir="resumes"):
        self.db = db
        self.docs_dir = docs_dir
        self.md = MarkItDown()

    def load_documents(self):
        """Scansiona la cartella e converte i file in documenti LangChain usando MarkItDown."""
        all_documents = []
        
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)
            return all_documents

        for filename in os.listdir(self.docs_dir):
            file_path = os.path.join(self.docs_dir, filename)
            
            if os.path.isfile(file_path):
                try:
                    
                    result = self.md.convert(file_path)
                    
                    if result and result.text_content:
                        
                        doc = Document(
                            page_content=result.text_content,
                            metadata={"source": filename, "file_path": file_path}
                        )
                        all_documents.append(doc)
                        
                except Exception as e:
                    print(f"Errore nella conversione del file {filename} con MarkItDown: {e}")
                        
        return all_documents

    def sync_documents(self):
        """Sincronizza i documenti convertiti con il database vettoriale."""
        raw_docs = self.load_documents()
        if not raw_docs:
            return

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(raw_docs)

        # Aggiorna il database
        self.db.add_documents(docs)