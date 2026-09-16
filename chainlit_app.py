"""Launch from the repository root: chainlit run chainlit_app.py -w."""

import logging
import chainlit as cl
from damage_agent.agent import answer_question
from frontend.team_api import register_routes
from frontend.chat_api import register_chat_routes

logger = logging.getLogger(__name__)


@cl.on_chat_start
async def start_chat():
    cl.user_session.set('conversation', {'slots': {}, 'history': []})
    await cl.Message(content=(
        "**What battle are we calculating?**\n\n"
        "Try: Basculegion with max attack and Adaptability using Aqua Jet "
        "into Mega Charizard Y with 32 HP EVs.\n\n"
        "Stat investments use Champions points (0–32). "
        "Follow up with changes like ‘what if it crits?’ Each chat remembers its own battle. "
        "Use New chat in the sidebar to start a separate conversation."
    )).send()


@cl.on_message
async def handle_message(message: cl.Message):
    question = message.content.strip()
    if not question:
        await cl.Message(content="Type a battle question to calculate damage.").send()
        return
    reply = cl.Message(content="Calculating…")
    await reply.send()
    try:
        reply.content, state = await cl.make_async(answer_question)(
            question, cl.user_session.get('conversation'))
        cl.user_session.set('conversation', state)
    except ValueError as exc:
        reply.content = f"I couldn't calculate that battle. {exc}"
    except Exception:
        logger.exception("Battle request failed")
        reply.content = (
            "I couldn't complete that calculation. Check the Pokémon and move names "
            "and try again. If it continues, check the server terminal for details."
        )
    await reply.update()


register_chat_routes()
register_routes()
