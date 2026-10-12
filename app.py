import chainlit as cl
from hr_assistant import (
    ask_hr_assistant_stream,
    get_database_stats,
    processor,
    reindex_database,
)

@cl.on_chat_start
async def start():
    actions = [
        cl.Action(name="db_stats", value="stats", label="📊 Statistiche Database", payload={}),
        cl.Action(name="db_reindex", value="reindex", label="🔄 Reindex Database", payload={})
    ]
    
    await cl.Message(
        content="**Informazioni del sistema:**\nPuoi interrogare i CV qui sotto o usare i comandi rapidi:",
        actions=actions
    ).send()

@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    count = get_database_stats()
    await cl.Message(content=f"📊 **Statistiche Database:**\nChunk totali: `{count}`").send()

@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    count = reindex_database()
    await cl.Message(content=f"🔄 **Database Reindicizzato!**\nChunk totali attuali: `{count}`").send()

@cl.on_message
async def main(message: cl.Message):
    uploaded_files = [
        element for element in (message.elements or []) if isinstance(element, cl.File)
    ]
    saved_files = []
    rejected_files = []

    for uploaded_file in uploaded_files:
        try:
            saved_path = processor.save_uploaded_file(
                uploaded_file.path, uploaded_file.name
            )
            saved_files.append(saved_path.name)
        except ValueError as error:
            rejected_files.append(f"{uploaded_file.name}: {error}")

    if saved_files:
        chunk_count = reindex_database()
        await cl.Message(
            content=(
                f"File salvati in `resumes`: {', '.join(saved_files)}. "
                f"Chunk totali nel database: `{chunk_count}`."
            )
        ).send()

    if rejected_files:
        await cl.Message(
            content=(
                "File non salvati:\n"
                + "\n".join(f"- {error}" for error in rejected_files)
            )
        ).send()

    if not message.content.strip():
        return

    msg = cl.Message(content="")
    await msg.send()
    stream = ask_hr_assistant_stream(message.content)
    for chunk in stream:
        await msg.stream_token(chunk.content)
        
    # Finalizza il messaggio
    await msg.update()

    #Start Assistant ---> chainlit run app.py -w