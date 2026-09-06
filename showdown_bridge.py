import json
import subprocess


def run_showdown_calc(battle):
    payload = {
        "gen": battle.get("gen", 9),
        "attacker": battle["attacker"],
        "defender": battle["defender"],
        "move": battle["move"],
        "field": battle.get("field", {}),
    }

    result = subprocess.run(
        ["node", "showdown_calc.js", json.dumps(payload)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        try:
            error_data = json.loads(result.stderr)
            raise RuntimeError(error_data.get("error", result.stderr))
        except Exception:
            raise RuntimeError(result.stderr)

    return json.loads(result.stdout)


def explain_showdown_damage(result):
    damage = result["damage"]
    min_damage = result["min_damage"]
    max_damage = result["max_damage"]

    lines = []

    lines.append(result["description"])
    lines.append("")
    lines.append("Result:")
    lines.append(f"Damage: {min_damage}–{max_damage} HP")
    lines.append("")
    lines.append("Showdown result:")
    lines.append(result["full_description"])
    lines.append("")
    lines.append("Damage rolls:")
    lines.append(", ".join(str(x) for x in damage))

    return "\n".join(lines)