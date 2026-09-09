"""Compact, human-readable CLI battle input summary."""

STAT_LABELS = {
    "hp": "HP", "atk": "Atk", "def": "Def",
    "spa": "SpA", "spd": "SpD", "spe": "Spe",
}


def format_battle_summary(battle):
    lines = [f"{battle['attacker']['name']} → {battle['defender']['name']} | {battle['move']}"]
    for role in ("attacker", "defender"):
        pokemon = battle[role]
        evs = pokemon.get("evs") or {}
        spread = " / ".join(
            f"{evs[key]} {label}" for key, label in STAT_LABELS.items()
            if evs.get(key, 0)
        ) or "0 in all stats"
        lines.extend([
            "",
            f"{role.title()}: {pokemon['name']}",
            f"  EVs: {spread}",
            f"  HP: {pokemon.get('current_hp_percent', 100)}% | "
            f"Ability: {pokemon.get('ability') or 'Default (calculator)'} | "
            f"Item: {pokemon.get('item') or 'None'}",
        ])
        conditions = []
        if pokemon.get("nature") and pokemon["nature"] != "Serious":
            conditions.append(f"Nature: {pokemon['nature']}")
        if pokemon.get("status"):
            conditions.append(f"Status: {pokemon['status']}")
        boosts = " / ".join(
            f"{value:+d} {STAT_LABELS[key]}"
            for key, value in (pokemon.get("boosts") or {}).items()
            if value and key in STAT_LABELS
        )
        if boosts:
            conditions.append(f"Boosts: {boosts}")
        if conditions:
            lines.append("  " + " | ".join(conditions))

    field = battle.get("field") or {}
    effects = []
    if field.get("weather"):
        effects.append(f"Weather: {field['weather']}")
    if field.get("terrain"):
        effects.append(f"Terrain: {field['terrain']}")
    for key, label in (("reflect", "Reflect"), ("light_screen", "Light Screen"),
                       ("aurora_veil", "Aurora Veil")):
        if field.get(key):
            effects.append(f"{label} (defender)")
    battle_type = "Singles" if field.get("is_double_battle") is False else "Doubles"
    lines.extend(["", f"Field: {battle_type} | " + (" | ".join(effects) or "No field effects")])
    if field.get("critical"):
        lines.append("Critical hit: Yes")
    return "\n".join(lines)
