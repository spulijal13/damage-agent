import json
import os
from pathlib import Path
from dotenv import load_dotenv

from battle_builder import (
    build_battle,
    ensure_default_doubles,
    validate_damage_slots,
)
from showdown_bridge import run_showdown_calc, explain_showdown_damage


def create_client():
    """Only require Gemini dependencies and credentials when starting the CLI."""

    load_dotenv(Path(__file__).resolve().with_name(".env"))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add it to .env or set it in your terminal.")
    from google import genai
    return genai.Client(api_key=api_key)


def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response.")
    return text[start:end + 1]


STAT_PROPERTIES = {
    "hp": {"type": "INTEGER", "nullable": True},
    "atk": {"type": "INTEGER", "nullable": True},
    "def": {"type": "INTEGER", "nullable": True},
    "spa": {"type": "INTEGER", "nullable": True},
    "spd": {"type": "INTEGER", "nullable": True},
    "spe": {"type": "INTEGER", "nullable": True},
}

BOOST_PROPERTIES = {
    "atk": {"type": "INTEGER", "nullable": True},
    "def": {"type": "INTEGER", "nullable": True},
    "spa": {"type": "INTEGER", "nullable": True},
    "spd": {"type": "INTEGER", "nullable": True},
    "spe": {"type": "INTEGER", "nullable": True},
}

POKEMON_SLOT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING", "nullable": True},
        "ability": {"type": "STRING", "nullable": True},
        "item": {"type": "STRING", "nullable": True},
        "nature": {"type": "STRING", "nullable": True},
        "status": {"type": "STRING", "nullable": True},
        "current_hp_percent": {"type": "NUMBER", "nullable": True},
        "spread": {
            "type": "OBJECT",
            "nullable": True,
            "properties": STAT_PROPERTIES,
        },
        "evs": {
            "type": "OBJECT",
            "nullable": True,
            "properties": STAT_PROPERTIES,
        },
        "boosts": {
            "type": "OBJECT",
            "nullable": True,
            "properties": BOOST_PROPERTIES,
        },
    },
}

DAMAGE_SLOT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "mode": {"type": "STRING", "enum": ["chat", "clarify", "damage"]},
        "message": {"type": "STRING", "nullable": True},
        "attacker": POKEMON_SLOT_SCHEMA,
        "defender": POKEMON_SLOT_SCHEMA,
        "move": {"type": "STRING", "nullable": True},
        "field": {
            "type": "OBJECT",
            "nullable": True,
            "properties": {
                "weather": {"type": "STRING", "nullable": True},
                "terrain": {"type": "STRING", "nullable": True},
                "critical": {"type": "BOOLEAN", "nullable": True},
                "reflect": {"type": "BOOLEAN", "nullable": True},
                "light_screen": {"type": "BOOLEAN", "nullable": True},
                "aurora_veil": {"type": "BOOLEAN", "nullable": True},
                "is_double_battle": {"type": "BOOLEAN", "nullable": True},
            },
        },
    },
    "required": ["mode"],
}

SYSTEM_PROMPT = """
You extract slots for a Pokemon damage-roll calculator.
Do not calculate damage. Do not convert stat points to EVs.
Do not fill IVs, default EVs, or a full Showdown Pokemon object.
Return JSON only.

Modes:
- chat: greeting or unrelated. Set message.
- clarify: damage question missing attacker, defender, or move. Set message.
- damage: fill attacker, defender, move, and any mentioned spreads.

Pokemon slots:
- name: Showdown form name. Mega Venusaur = Venusaur-Mega. Mega Charizard Y = Charizard-Mega-Y. Mega Charizard X = Charizard-Mega-X.
- spread: Champions stat points 0-32, only stats the user mentioned. Unmentioned stats omitted.
- evs: only if the user clearly asked for normal EVs. Do not fill both spread and evs.
- ability, item, nature, status, boosts, current_hp_percent: only if mentioned, on the Pokemon they belong to.

Champions points (not EVs):
- A number with a stat is points unless the user says EVs.
- max HP / max Atk / max SpA / max SpD / max Speed = 32 in that spread field.
- 14 in SpD = spread.spd 14. 17 in SpD = 17. no points in defense = spread.def 0.

Move: canonical move name after the attacker, or after "with".
"X Move against/into/vs Y" means attacker X, move, defender Y.
Never invent Pokemon or moves. Never parse "max attack" or a nature as a move.

Field, only if mentioned:
- crit / critical => critical true. no crit => critical false.
- sun, rain, sand, snow, terrains, reflect, light screen, aurora veil.
- singles / single battle / 1v1 singles => is_double_battle false.

Natures if described: spa raising = Modest, attack raising = Adamant, speed raising special = Timid, Jolly = Jolly.
Status codes: brn, par, psn, tox, slp, frz.
"""


def parse_damage_slots(user_question, client):
    from google.genai import types

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=DAMAGE_SLOT_SCHEMA,
            temperature=0.1,
        ),
    )

    cleaned = extract_json(response.text)
    request = json.loads(cleaned)
    if not isinstance(request, dict):
        raise ValueError("Model response must be a JSON object.")
    return request


def prepare_damage_request(extraction, user_question):
    mode = extraction.get("mode")
    if mode != "damage":
        return extraction

    valid, message = validate_damage_slots(extraction)
    if not valid:
        return {"mode": "clarify", "message": message}

    battle = build_battle(extraction)
    ensure_default_doubles(battle, user_question)
    return {"mode": "damage", "slots": extraction, "battle": battle}


def apply_common_corrections(request, user_question=""):
    """Turn Gemini slots into a calc-ready request, or clarify if slots are incomplete."""
    return prepare_damage_request(request, user_question)


def run_agent():
    client = create_client()
    print("Pokemon Damage Calc Agent using Google Gemini + Showdown Calc")
    print("Gemini fills attacker, defender, move, and spreads. Calc assembly is local.")
    print("Type a battle question. Type 'quit' to stop.")
    print()

    while True:
        user_question = input("Ask: ").strip()

        if user_question.lower() in ["quit", "exit", "q"]:
            print("Goodbye.")
            break

        if not user_question:
            continue

        try:
            extraction = parse_damage_slots(user_question, client)
            battle_request = prepare_damage_request(extraction, user_question)
            mode = battle_request.get("mode")

            if mode == "chat":
                print()
                print(battle_request.get("message", "Ask me a Pokemon damage question."))
                print()
                continue

            if mode == "clarify":
                print()
                print(battle_request.get("message", "I need more information before I can calculate this."))
                print()
                continue

            if mode == "damage":
                battle = battle_request["battle"]
                print()
                print("Parsed slots:")
                print(json.dumps(extraction, indent=2))
                print()
                print("Battle dictionary:")
                print(json.dumps(battle, indent=2))
                print()
                result = run_showdown_calc(battle)
                print("Result:")
                print(explain_showdown_damage(result))
                print()
                continue

            print()
            print("I could not understand the request mode.")
            print("Raw model output:")
            print(json.dumps(battle_request, indent=2))
            print()

        except Exception as e:
            print()
            print("Error:")
            print(e)
            print()


if __name__ == "__main__":
    run_agent()
