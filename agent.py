import json
import os
import re

from google import genai
from google.genai import types

from showdown_bridge import (
    run_showdown_calc,
    explain_showdown_damage,
)


# ============================================================
# GEMINI CLIENT
# ============================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "Missing GEMINI_API_KEY.\n"
        "Run this in your terminal first:\n"
        'export GEMINI_API_KEY="paste_your_key_here"'
    )

client = genai.Client(api_key=api_key)


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_text(text):
    if text is None:
        return ""

    return (
        str(text)
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response.")

    return text[start:end + 1]


def is_optimization_mode(request):
    return request.get("mode") == "bulk_optimize"


def set_field_value(request, key, value):
    if request.get("mode") == "damage" and "battle" in request:
        request["battle"].setdefault("field", {})
        request["battle"]["field"][key] = value

    elif is_optimization_mode(request):
        request.setdefault("field", {})
        request["field"][key] = value


def ensure_default_doubles(request, user_question):
    q = normalize_text(user_question)

    is_singles = (
        "singles" in q
        or "single battle" in q
        or "1v1 singles" in q
    )

    set_field_value(request, "is_double_battle", not is_singles)

    return request


# ============================================================
# COMMON NAME CORRECTIONS
# ============================================================

MOVE_ALIASES = {
    "direclaw": "Dire Claw",
    "dire claw": "Dire Claw",
    "closecombat": "Close Combat",
    "close combat": "Close Combat",
    "close compbat": "Close Combat",
    "gunkshot": "Gunk Shot",
    "gunk shot": "Gunk Shot",
    "flamethrower": "Flamethrower",
    "earthquake": "Earthquake",
    "thunderbolt": "Thunderbolt",
    "icebeam": "Ice Beam",
    "ice beam": "Ice Beam",
    "heatwave": "Heat Wave",
    "heat wave": "Heat Wave",
    "lowkick": "Low Kick",
    "low kick": "Low Kick",
    "weatherball": "Weather Ball",
    "weather ball": "Weather Ball",
    "powergem": "Power Gem",
    "power gem": "Power Gem",
}

POKEMON_ALIASES = {
    "dire wolf": "Sneasler",
    "sneasler": "Sneasler",
    "primarina": "Primarina",
    "kingambit": "Kingambit",
    "kingabit": "Kingambit",
    "glimmora": "Glimmora",

    "mega venusaur": "Venusaur-Mega",
    "megavenusaur": "Venusaur-Mega",
    "venusaur mega": "Venusaur-Mega",
    "venusaur-mega": "Venusaur-Mega",

    "mega charizard y": "Charizard-Mega-Y",
    "megacharizardy": "Charizard-Mega-Y",
    "charizard mega y": "Charizard-Mega-Y",
    "charizard-mega-y": "Charizard-Mega-Y",

    "mega charizard x": "Charizard-Mega-X",
    "megacharizardx": "Charizard-Mega-X",
    "charizard mega x": "Charizard-Mega-X",
    "charizard-mega-x": "Charizard-Mega-X",
}

DEFAULT_ABILITY_BY_FORM = {
    "Venusaur-Mega": "Thick Fat",
    "Charizard-Mega-Y": "Drought",
    "Charizard-Mega-X": "Tough Claws",
    "Blastoise-Mega": "Mega Launcher",
    "Gengar-Mega": "Shadow Tag",
    "Kangaskhan-Mega": "Parental Bond",
    "Mawile-Mega": "Huge Power",
    "Metagross-Mega": "Tough Claws",
    "Salamence-Mega": "Aerilate",
    "Tyranitar-Mega": "Sand Stream",
    "Lucario-Mega": "Adaptability",
    "Gardevoir-Mega": "Pixilate",
    "Scizor-Mega": "Technician",
    "Swampert-Mega": "Swift Swim",
    "Sceptile-Mega": "Lightning Rod",
    "Diancie-Mega": "Magic Bounce",
    "Glimmora": "Toxic Debris",
}


def fix_pokemon_name(name):
    if not name:
        return name

    key = normalize_text(name)

    return POKEMON_ALIASES.get(key, name)


def fix_move_name(name):
    if not name:
        return name

    key = normalize_text(name)

    return MOVE_ALIASES.get(key, name)


def apply_default_abilities_to_battle(battle):
    attacker_name = battle["attacker"].get("name")
    defender_name = battle["defender"].get("name")

    if battle["attacker"].get("ability") is None:
        battle["attacker"]["ability"] = DEFAULT_ABILITY_BY_FORM.get(attacker_name)

    if battle["defender"].get("ability") is None:
        battle["defender"]["ability"] = DEFAULT_ABILITY_BY_FORM.get(defender_name)

    return battle


def apply_default_abilities_to_bulk_request(request):
    attacker_name = request["attacker"].get("name")
    defender_name = request["defender"].get("name")

    if request["attacker"].get("ability") is None:
        request["attacker"]["ability"] = DEFAULT_ABILITY_BY_FORM.get(attacker_name)

    if request["defender"].get("ability") is None:
        request["defender"]["ability"] = DEFAULT_ABILITY_BY_FORM.get(defender_name)

    return request


def apply_common_corrections(request, user_question):
    q = normalize_text(user_question)

    # Fix move names from user text.
    for alias, real_move in MOVE_ALIASES.items():
        if alias in q:
            if request.get("mode") == "damage" and "battle" in request:
                request["battle"]["move"] = real_move
            elif is_optimization_mode(request):
                request["move"] = real_move

    # Fix Pokemon names.
    if request.get("mode") == "damage" and "battle" in request:
        request["battle"]["attacker"]["name"] = fix_pokemon_name(
            request["battle"]["attacker"].get("name")
        )
        request["battle"]["defender"]["name"] = fix_pokemon_name(
            request["battle"]["defender"].get("name")
        )

        request["battle"]["move"] = fix_move_name(request["battle"].get("move"))
        request["battle"] = apply_default_abilities_to_battle(request["battle"])

    elif is_optimization_mode(request):
        request["attacker"]["name"] = fix_pokemon_name(
            request["attacker"].get("name")
        )
        request["defender"]["name"] = fix_pokemon_name(
            request["defender"].get("name")
        )

        request["move"] = fix_move_name(request.get("move"))
        request = apply_default_abilities_to_bulk_request(request)

    # Crit handling.
    if "crit" in q or "critical" in q:
        set_field_value(request, "critical", True)

    # Weather handling.
    if "under the sun" in q or "in sun" in q or " sun" in q:
        set_field_value(request, "weather", "Sun")

    if "rain" in q:
        set_field_value(request, "weather", "Rain")

    if "sandstorm" in q or "sand storm" in q:
        set_field_value(request, "weather", "Sand")

    if "snow" in q or "hail" in q:
        set_field_value(request, "weather", "Snow")

    # Ability-based field backup.
    # This is important for Mega Charizard Y Weather Ball.
    if request.get("mode") == "damage" and "battle" in request:
        battle = request["battle"]
        field = battle.setdefault("field", {})

        attacker_ability = normalize_text(battle["attacker"].get("ability"))
        defender_ability = normalize_text(battle["defender"].get("ability"))

        ability_text = f"{attacker_ability} {defender_ability}"

        if field.get("weather") is None:
            if "drought" in ability_text or "orichalcum pulse" in ability_text:
                field["weather"] = "Sun"
            elif "drizzle" in ability_text:
                field["weather"] = "Rain"
            elif "sand stream" in ability_text:
                field["weather"] = "Sand"
            elif "snow warning" in ability_text:
                field["weather"] = "Snow"

        if field.get("terrain") is None:
            if "electric surge" in ability_text or "hadron engine" in ability_text:
                field["terrain"] = "Electric"
            elif "grassy surge" in ability_text:
                field["terrain"] = "Grassy"
            elif "psychic surge" in ability_text:
                field["terrain"] = "Psychic"
            elif "misty surge" in ability_text:
                field["terrain"] = "Misty"

    # Item handling backup.
    if "chople" in q:
        if request.get("mode") == "damage" and "battle" in request:
            request["battle"]["defender"]["item"] = "Chople Berry"
        elif is_optimization_mode(request):
            request["defender"]["item"] = "Chople Berry"

    if "life orb" in q or "lifeorb" in q:
        if request.get("mode") == "damage" and "battle" in request:
            request["battle"]["attacker"]["item"] = "Life Orb"
        elif is_optimization_mode(request):
            request["attacker"]["item"] = "Life Orb"

    if "choice band" in q or "choiceband" in q:
        if request.get("mode") == "damage" and "battle" in request:
            request["battle"]["attacker"]["item"] = "Choice Band"
        elif is_optimization_mode(request):
            request["attacker"]["item"] = "Choice Band"

    if "choice specs" in q or "choicespecs" in q:
        if request.get("mode") == "damage" and "battle" in request:
            request["battle"]["attacker"]["item"] = "Choice Specs"
        elif is_optimization_mode(request):
            request["attacker"]["item"] = "Choice Specs"

    return request


# ============================================================
# VALIDATION
# ============================================================

def validate_damage_battle(battle):
    attacker_name = battle.get("attacker", {}).get("name")
    defender_name = battle.get("defender", {}).get("name")
    move_name = battle.get("move")

    if not attacker_name:
        return False, "I need the attacking Pokemon."

    if not defender_name:
        return False, "I need the defending Pokemon."

    if not move_name:
        return False, "I need the move name."

    return True, None


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a Pokemon damage calculator parsing agent.

Your job is to convert the user's request into valid JSON.

Return JSON only.
Do not include markdown.
Do not include explanations.
Do not calculate damage yourself.
The final damage will be calculated by the official Showdown damage calculator.

All calculations are for double battles by default.

Only set field.is_double_battle to false if the user clearly says singles, single battle, or 1v1 singles.

Pokemon Champions spread rules:
- All calculations use Pokemon Champions stat points by default.
- Total spread point limit is 66.
- Maximum points in one stat is 32.
- The JSON must use normal EV-equivalent numbers in the evs field.

Pokemon Champions Stat Point conversion:
- 0 points = 0 EV equivalent.
- For any value from 1 to 32, use this formula:
  EV equivalent = points * 8 - 4.
- Examples:
  1 point = 4 EV equivalent.
  4 points = 28 EV equivalent.
  8 points = 60 EV equivalent.
  14 points = 108 EV equivalent.
  16 points = 124 EV equivalent.
  17 points = 132 EV equivalent.
  32 points = 252 EV equivalent.
- If the user says "14 in SpD", set spd to 108.
- If the user says "17 in SpD", set spd to 132.
- If the user says "max SpD", set spd to 252.
- If the user says "max HP", set hp to 252.
- If the user says "max SpA", set spa to 252.
- If the user says "max Speed", set spe to 252.
- If the user says "no stat points in defense", set def to 0.
- If the user gives a number followed by a stat, treat that number as Champions Stat Points unless they clearly say normal EVs.

Use these modes:

1. chat

Use this when the user says hello or says something unrelated to Pokemon damage.

Return:
{
  "mode": "chat",
  "message": "Ask me a Pokemon damage question."
}

2. clarify

Use this when the user is asking for damage but did not provide enough information.

Return:
{
  "mode": "clarify",
  "message": "I need the move name before I can calculate this."
}

Use clarify mode if:
- attacker is missing
- defender is missing
- move is missing
- the request is too ambiguous

Never invent Pokemon names.
Never invent move names.

3. damage

Use this when the user asks for one specific damage calculation.

Return:
{
  "mode": "damage",
  "battle": {
    "gen": 9,
    "attacker": {
      "name": "Pokemon name",
      "level": 50,
      "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
      "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
      "nature": "Serious",
      "ability": null,
      "item": null,
      "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
      "status": null,
      "current_hp_percent": 100
    },
    "defender": {
      "name": "Pokemon name",
      "level": 50,
      "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
      "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
      "nature": "Serious",
      "ability": null,
      "item": null,
      "boosts": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
      "status": null,
      "current_hp_percent": 100,
      "grounded": true
    },
    "move": "Move name",
    "field": {
      "weather": null,
      "terrain": null,
      "critical": false,
      "reflect": false,
      "light_screen": false,
      "aurora_veil": false,
      "is_double_battle": true
    }
  }
}

General parsing rules:
- Default level is 50.
- Default IVs are 31.
- Default EVs are 0 unless stated.
- If the user says "crit" or "critical", set field.critical to true.
- If the user says "under the sun", "in sun", or "sun", set field.weather to "Sun".
- If the user says "rain", set field.weather to "Rain".
- If the user says "sand", set field.weather to "Sand".
- If the user says "snow", set field.weather to "Snow".
- If the user says "spa raising nature", use Modest.
- If the user says "attack raising nature", use Adamant.
- If the user says "speed raising nature" or "Timid", use Timid for special attackers.
- If the user says "Jolly", use Jolly.

Natural language battle parsing rules:
- When the user writes a Pokemon name followed by a move name, treat the Pokemon as the attacker and the move as the move being used.
- Example: "Mega Floette Moonblast" means attacker is "Floette-Mega" and move is "Moonblast".
- Example: "Mega Charizard Y Weather Ball" means attacker is "Charizard-Mega-Y" and move is "Weather Ball".
- Example: "Sneasler Dire Claw" means attacker is "Sneasler" and move is "Dire Claw".
- Do not treat the move name as part of the Pokemon name.
- Do not ask for the move if a valid move name appears right after the attacker name.
- If the user says "against", "into", "to", or "vs", the Pokemon after that word is usually the defender.
- Example: "Mega Floette Moonblast against Sneasler" means Floette-Mega uses Moonblast into Sneasler.
- Example: "Mega Charizard Y Heat Wave into Mega Venusaur" means Charizard-Mega-Y uses Heat Wave into Venusaur-Mega.
- If the user says "with [move name]" after the attacker, treat that as the move.
- Example: "Mega Floette with Moonblast against Sneasler" means Floette-Mega uses Moonblast into Sneasler.

Mega form parsing rules:
- "Mega Venusaur" must be returned as "Venusaur-Mega".
- "Mega Charizard Y" must be returned as "Charizard-Mega-Y".
- "Mega Charizard X" must be returned as "Charizard-Mega-X".
- Do not return names like "Mega Charizard Y" or "Mega Venusaur".
- Always return the exact Showdown-style form name.

Default ability rules:
- If the user does not mention Mega Venusaur's ability, use "Thick Fat".
- If the user does not mention Mega Charizard Y's ability, use "Drought".
- If the user does not mention Mega Charizard X's ability, use "Tough Claws".
- If the user does not mention Glimmora's ability, use "Toxic Debris".
- If the user mentions an ability, use the mentioned ability.

Move parsing rules:
- Heatwave means Heat Wave.
- Weatherball means Weather Ball.
- Powergem means Power Gem.
- Direclaw means Dire Claw.
- Close Combat means Close Combat.
- Never parse "max attack" as a move.
- Never parse "Jolly" as a move.

Item parsing rules:
- If the user mentions an item, place it on the Pokemon it describes.
- Chople means Chople Berry.
- Life Orb means Life Orb.
- Choice Band means Choice Band.
- Choice Specs means Choice Specs.

Return valid JSON only.
"""


# ============================================================
# GEMINI CALL
# ============================================================

def make_battle_dict(user_question):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\nUser question:\n{user_question}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    cleaned = extract_json(response.text)
    return json.loads(cleaned)


# ============================================================
# MAIN LOOP
# ============================================================

def run_agent():
    print("Pokemon Damage Calc Agent using Google Gemini + Showdown Calc")
    print("Pokemon Champions parsing: 66 total points, 32 max per stat, doubles by default.")
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
            battle_request = make_battle_dict(user_question)
            battle_request = apply_common_corrections(battle_request, user_question)
            battle_request = ensure_default_doubles(battle_request, user_question)

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

                valid, error_message = validate_damage_battle(battle)

                if not valid:
                    print()
                    print(error_message)
                    print()
                    continue

                print()
                print("Battle dictionary:")
                print(json.dumps(battle, indent=2))
                print()

                result = run_showdown_calc(battle)

                print("Result:")
                print(explain_showdown_damage(result))
                print()
                continue

            if mode == "bulk_optimize":
                print()
                print("Bulk optimization is not connected yet after switching to Showdown.")
                print("First confirm direct damage works. Then update optimizer.py to call run_showdown_calc().")
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