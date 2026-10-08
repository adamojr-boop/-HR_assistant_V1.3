from .database import Database
from .document_processor import DocumentProcessor
from .config import OPENAI_API_KEY
from langchain_openai import ChatOpenAI

# Inizializzazione dei componenti principali
db = Database()
processor = DocumentProcessor(db)
processor.sync_documents()
collection = db.get_collection()

# Configurazione del modello LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)

def get_database_stats() -> int:
    """Restituisce il numero totale di chunk presenti nel database."""
    return collection.count()

def reindex_database() -> int:
    """Forza la risincronizzazione dei documenti e restituisce il nuovo conteggio."""
    processor.sync_documents()
    return collection.count()

def ask_hr_assistant_stream(user_query: str):
    """Gestisce la ricerca nei CV (con n_results=25 per coprire tutti i profili) e restituisce lo streaming dal LLM."""
    results = collection.query(
        query_texts=[user_query], 
        n_results=25
    )
    
    retrieved_chunks = results.get("documents", [[]])[0]
    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else "Nessun documento trovato."

    prompt = f"""
Sei un assistente HR esperto, preciso e rigoroso. 
Analizza il contesto dei curriculum forniti per rispondere alla domanda dell'utente.

REGOLE FONDAMENTALI:
1. Basati ESCLUSIVAMENTE sulle informazioni presenti nel contesto. Non inventare mai dati che non compaiono nei testi.
2. Se l'utente chiede elenchi generali, panoramiche sui candidati, contatti o affinità, estrai le informazioni reali direttamente dai documenti (inclusi nomi, email, telefoni ed esperienze).
3. Se una richiesta specifica non trova riscontro nei documenti, segnalalo gentilmente.

Struttura la risposta in modo chiaro e leggibile per l'utente (puoi usare elenchi puntati per i profili, i contatti o le competenze richieste).

Contesto (Curriculum): {context}
Domanda: {user_query}
"""
    return llm.stream(prompt)