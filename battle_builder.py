from pokemon_catalog import default_ability

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
BOOST_KEYS = ("atk", "def", "spa", "spd", "spe")
CHAMPIONS_MAX_POINTS_PER_STAT = 32

def normalize_text(text):
    if text is None:
        return ""
    return str(text).lower().replace("-", " ").replace("_", " ").strip()


def empty_stats():
    return {key: 0 for key in STAT_KEYS}


def empty_ivs():
    return {key: 31 for key in STAT_KEYS}


def empty_boosts():
    return {key: 0 for key in BOOST_KEYS}


def champions_points_to_evs(points):
    try:
        points = int(points)
    except (TypeError, ValueError):
        return 0
    if points <= 0:
        return 0
    points = min(points, CHAMPIONS_MAX_POINTS_PER_STAT)
    return points * 8 - 4


def _int_map(source, keys, default=0):
    values = {key: default for key in keys}
    if not isinstance(source, dict):
        return values
    for key in keys:
        raw = source.get(key)
        if raw is None:
            continue
        try:
            values[key] = int(raw)
        except (TypeError, ValueError):
            continue
    return values


def resolve_evs(slot):
    evs = empty_stats()
    if not isinstance(slot, dict):
        return evs

    # Parser investments always use Champions units, even if labeled "evs".
    spread = slot.get("spread") or slot.get("evs") or {}
    for key, points in _int_map(spread, STAT_KEYS, default=0).items():
        evs[key] = champions_points_to_evs(points)
    return evs


def _ability_field_defaults(attacker_ability, defender_ability, field):
    ability_text = f"{normalize_text(attacker_ability)} {normalize_text(defender_ability)}"
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
    return field


def build_pokemon(slot):
    slot = slot if isinstance(slot, dict) else {}
    name = slot.get("name")
    ability = slot.get("ability")
    if ability is None:
        ability = default_ability(name)
    return {
        "name": name,
        "level": slot.get("level") or 50,
        "evs": resolve_evs(slot),
        "ivs": empty_ivs(),
        "nature": slot.get("nature") or "Serious",
        "ability": ability,
        "item": slot.get("item"),
        "boosts": _int_map(slot.get("boosts"), BOOST_KEYS, default=0),
        "status": slot.get("status"),
        "current_hp_percent": slot.get("current_hp_percent") if slot.get("current_hp_percent") is not None else 100,
    }


def build_field(slot, attacker, defender):
    slot = slot if isinstance(slot, dict) else {}
    field = {
        "weather": slot.get("weather"),
        "terrain": slot.get("terrain"),
        "critical": bool(slot.get("critical")),
        "reflect": bool(slot.get("reflect")),
        "light_screen": bool(slot.get("light_screen")),
        "aurora_veil": bool(slot.get("aurora_veil")),
        "is_double_battle": True if slot.get("is_double_battle") is None else bool(slot.get("is_double_battle")),
    }
    return _ability_field_defaults(attacker.get("ability"), defender.get("ability"), field)


def ensure_default_doubles(battle, user_question):
    question = normalize_text(user_question)
    is_singles = (
        "singles" in question
        or "single battle" in question
        or "1v1 singles" in question
    )
    battle.setdefault("field", {})["is_double_battle"] = not is_singles
    return battle


def validate_damage_slots(extraction):
    if not isinstance(extraction, dict):
        return False, "I need a battle with an attacker, defender, and move."
    attacker = extraction.get("attacker")
    defender = extraction.get("defender")
    if not isinstance(attacker, dict) or not isinstance(defender, dict):
        return False, "I need both the attacking and defending Pokemon."
    if not attacker.get("name"):
        return False, "I need the attacking Pokemon."
    if not defender.get("name"):
        return False, "I need the defending Pokemon."
    if not extraction.get("move"):
        return False, "I need the move name."
    return True, None


def build_battle(extraction):
    attacker = build_pokemon(extraction.get("attacker"))
    defender = build_pokemon(extraction.get("defender"))
    return {
        "gen": extraction.get("gen") or 9,
        "attacker": attacker,
        "defender": defender,
        "move": extraction.get("move"),
        "field": build_field(extraction.get("field"), attacker, defender),
    }
