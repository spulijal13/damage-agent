"""Chat frontend: chainlit run chainlit_app.py -w"""

import logging

import chainlit as cl

from damage_agent.agent import create_client, parse_damage_slots, prepare_damage_request
from damage_agent.battle_summary import format_battle_summary
from damage_agent.showdown_bridge import run_showdown_calc, explain_showdown_damage

logger = logging.getLogger(__name__)


def answer_question(question):
    # Keep credentials and calculator execution on the server.
    with create_client() as client:
        slots = parse_damage_slots(question, client)
    request = prepare_damage_request(slots, question)
    if request.get("mode") in ("chat", "clarify"):
        return request.get("message") or "Include the attacker, defender, and move in your question."
    if request.get("mode") != "damage":
        return "I couldn't understand that battle. Please include both Pokémon and the move."

    battle = request["battle"]
    result = run_showdown_calc(battle)
    summary = format_battle_summary(battle)
    # Preserve the compact summary's line breaks without displaying raw JSON.
    summary = summary.replace("\n", "  \n")
    return (
        f"**{result['min_damage']}–{result['max_damage']} HP damage**\n\n"
        f"{summary}\n\n---\n\n{explain_showdown_damage(result)}"
    )


@cl.on_chat_start
async def start_chat():
    await cl.Message(content=(
        "**What battle are we calculating?**\n\n"
        "Try: Basculegion with max attack and Adaptability using Aqua Jet "
        "into Mega Charizard Y with 32 HP EVs.\n\n"
        "Stat investments use Champions points (0–32). "
        "Include the full battle in each message."
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
        reply.content = await cl.make_async(answer_question)(question)
    except ValueError as exc:
        reply.content = f"I couldn't calculate that battle. {exc}"
    except Exception:
        logger.exception("Battle request failed")
        reply.content = (
            "I couldn't complete that calculation. Check the Pokémon and move names "
            "and try again. If it continues, check the server terminal for details."
        )
    await reply.update()
