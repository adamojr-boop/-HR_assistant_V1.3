import chainlit as cl
from assistant3.database import Database
from assistant3.document_processor import DocumentProcessor

db = Database()
processor = DocumentProcessor(db)

@cl.on_chat_start
async def start():
    """Inizializza la chat inviando i pulsanti di gestione del database."""
    actions = [
        cl.Action(
            name="db_stats",
            icon="bar-chart",
            label="Statistiche Database",
            value="db_stats"
        ),
        cl.Action(
            name="db_reindex",
            icon="refresh-cw",
            label="Reindex Database",
            value="db_reindex"
        ),
        cl.Action(
            name="db_clear",
            icon="trash-2",
            label="Svuota completamente il Database",
            value="db_clear"
        ),
    ]
    await cl.Message(
        content="**Informazioni del sistema:**", 
        actions=actions
    ).send()

@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    """Mostra le statistiche attuali del database ChromaDB."""
    collection = db.get_collection()
    count = collection.count() if collection else 0
    await cl.Message(content=f"📊 **Statistiche Database:** Il database contiene attualmente `{count}` chunk indicizzati.").send()

@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    """Sincronizza/reindicizza i file presenti nella cartella resumes."""
    processor.sync_documents()
    await cl.Message(content="🔄 **Reindex completato:** La cartella resumes è stata sincronizzata con successo nel database.").send()

@cl.action_callback("db_clear")
async def on_db_clear(action: cl.Action):
    """Svuota completamente la collezione del database."""
    db.delete_collection()
    await cl.Message(content="🗑️ **Database svuotato:** L'intera collezione è stata eliminata. È necessario lanciare il reindex per ricaricare i file.").send()

@cl.on_message
async def main(message: cl.Message):
    """Gestisce i messaggi di chat dell'utente (query RAG)."""
    
    await cl.Message(content=f"Hai scritto: {message.content}. (La logica di risposta RAG verrà collegata qui)").send()
    
#poetry run chainlit run app.py -w ---> Avvia L'app in Chainlit con interfaccia web