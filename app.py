import chainlit as cl
from hr_assistant import get_database_stats, reindex_database, ask_hr_assistant_stream

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
    msg = cl.Message(content="")
    await msg.send()
    stream = ask_hr_assistant_stream(message.content)
    for chunk in stream:
        await msg.stream_token(chunk.content)
        
    # Finalizza il messaggio
    await msg.update()