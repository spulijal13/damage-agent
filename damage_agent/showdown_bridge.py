import json
import subprocess
from pathlib import Path

CALCULATOR_PATH = Path(__file__).resolve().parents[1] / "calculator" / "showdown_calc.js"


def run_showdown_calc(battle):
    payload = {
        "gen": battle.get("gen", 9),
        "attacker": battle["attacker"],
        "defender": battle["defender"],
        "move": battle["move"],
        "field": battle.get("field", {}),
    }

    result = subprocess.run(
        ["node", str(CALCULATOR_PATH), json.dumps(payload)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        try:
            error_data = json.loads(result.stderr)
        except json.JSONDecodeError:
            raise RuntimeError(result.stderr.strip() or "Showdown calculation failed.") from None
        raise RuntimeError(error_data.get("error", result.stderr))

    return json.loads(result.stdout)


def explain_showdown_damage(result):
    damage = result["damage"]
    min_damage = result["min_damage"]
    max_damage = result["max_damage"]

    lines = [result["full_description"], "", f"Damage: {min_damage}–{max_damage} HP", ""]
    if damage and isinstance(damage[0], list):
        lines.append("Damage rolls by hit:")
        lines.extend(f"Hit {i}: " + ", ".join(map(str, rolls))
                     for i, rolls in enumerate(damage, 1))
    else:
        lines.extend(["Damage rolls:", ", ".join(map(str, damage))])
    return "\n".join(lines)
