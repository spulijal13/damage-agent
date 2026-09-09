from calculator import (
    calc_damage_advanced,
    get_move,
    champions_points_to_evs,
    empty_evs,
    empty_ivs,
    empty_boosts,
    CHAMPIONS_TOTAL_POINTS,
    CHAMPIONS_MAX_POINTS_PER_STAT,
)

from legacy.sequence_engine import simulate_hit_sequence, choose_damage_from_rolls


def get_defensive_stat_for_move(move_name):
    move = get_move(move_name)

    if move["category"] == "Physical":
        return "def", ["Bold", "Impish", "Hardy", "Relaxed"]

    if move["category"] == "Special":
        return "spd", ["Calm", "Careful", "Hardy", "Sassy"]

    return None, []


def spread_meets_goal(result, goal):
    max_hp = result["defender_hp"]
    rolls = result["rolls"]

    hits = goal.get("hits", 1)
    damage_roll = goal.get("damage_roll", "max")
    recovery = goal.get("recovery", [])
    residual = goal.get("residual_damage", [])
    success_condition = goal.get("success_condition", "survive_after_final_hit")

    chosen_damage = choose_damage_from_rolls(rolls, damage_roll)

    sequence = simulate_hit_sequence(
        max_hp=max_hp,
        damage_per_hit=chosen_damage,
        hits=hits,
        recovery_effects=recovery,
        residual_effects=residual,
        apply_end_of_turn_after_final_hit=goal.get("apply_end_of_turn_after_final_hit", False),
    )

    if success_condition == "survive_after_final_hit":
        passed = sequence["survived"]

    elif success_condition == "faint_by_final_hit":
        passed = not sequence["survived"]

    else:
        raise ValueError(f"Unsupported success condition: {success_condition}")

    return passed, sequence, chosen_damage


def optimize_bulk_goal(
    attacker_info,
    defender_name,
    move_name,
    field,
    goal,
    defender_ability=None,
    defender_item=None,
    defender_status=None,
    defender_current_hp_percent=100,
    level=50,
    nature_options=None,
    max_total_points=CHAMPIONS_TOTAL_POINTS,
    max_points_per_stat=CHAMPIONS_MAX_POINTS_PER_STAT,
    return_mode="best",
    top_n=20,
    max_results=500,
):
    defensive_stat, default_natures = get_defensive_stat_for_move(move_name)

    if defensive_stat is None:
        return {
            "message": f"{move_name} does not deal direct damage.",
            "spreads": [],
            "best": None,
        }

    nature_options = nature_options or default_natures

    passing_spreads = []
    failing_spreads = []

    for nature in nature_options:
        for hp_points in range(0, max_points_per_stat + 1):
            for defensive_points in range(0, max_points_per_stat + 1):
                total_points = hp_points + defensive_points

                if total_points > max_total_points:
                    continue

                hp_ev = champions_points_to_evs(hp_points, max_points_per_stat)
                defensive_ev = champions_points_to_evs(defensive_points, max_points_per_stat)

                evs = empty_evs()
                evs["hp"] = hp_ev
                evs[defensive_stat] = defensive_ev

                defender_info = {
                    "name": defender_name,
                    "level": level,
                    "evs": evs,
                    "ivs": empty_ivs(),
                    "nature": nature,
                    "ability": defender_ability,
                    "item": defender_item,
                    "boosts": empty_boosts(),
                    "status": defender_status,
                    "current_hp_percent": defender_current_hp_percent,
                    "grounded": True,
                }

                battle = {
                    "attacker": attacker_info,
                    "defender": defender_info,
                    "move": move_name,
                    "field": field,
                }

                damage_result = calc_damage_advanced(battle)

                if "message" in damage_result:
                    continue

                passed, sequence, chosen_damage = spread_meets_goal(damage_result, goal)

                defensive_points_key = defensive_stat + "_points"
                defensive_ev_key = defensive_stat + "_ev"

                spread = {
                    "nature": nature,
                    "hp_points": hp_points,
                    defensive_points_key: defensive_points,
                    "total_points": total_points,
                    "hp_ev": hp_ev,
                    defensive_ev_key: defensive_ev,
                    "defender_hp": damage_result["defender_hp"],
                    "damage_min": damage_result["min_damage"],
                    "damage_max": damage_result["max_damage"],
                    "damage_percent_min": damage_result["min_percent"],
                    "damage_percent_max": damage_result["max_percent"],
                    "rolls": damage_result["rolls"],
                    "chosen_damage": chosen_damage,
                    "goal_passed": passed,
                    "sequence": sequence,
                }

                if passed:
                    passing_spreads.append(spread)
                else:
                    failing_spreads.append(spread)

    defensive_points_key = defensive_stat + "_points"

    passing_spreads.sort(
        key=lambda x: (
            x["total_points"],
            x["hp_points"],
            x.get(defensive_points_key, 0),
            x["nature"],
        )
    )

    failing_spreads.sort(
        key=lambda x: (
            x["total_points"],
            x["hp_points"],
            x.get(defensive_points_key, 0),
            x["nature"],
        )
    )

    if return_mode == "best":
        selected = passing_spreads[:1]
    elif return_mode == "top_n":
        selected = passing_spreads[:top_n]
    elif return_mode == "all":
        selected = passing_spreads[:max_results]
    else:
        selected = passing_spreads[:top_n]

    return {
        "mode": return_mode,
        "ruleset": "Pokemon Champions",
        "attacker": attacker_info["name"],
        "defender": defender_name,
        "move": move_name,
        "defensive_stat": defensive_stat,
        "goal": goal,
        "total_passing_spreads": len(passing_spreads),
        "total_failing_spreads": len(failing_spreads),
        "showing": len(selected),
        "spreads": selected,
        "best": passing_spreads[0] if passing_spreads else None,
        "assumptions": {
            "level": level,
            "max_total_points": max_total_points,
            "max_points_per_stat": max_points_per_stat,
            "point_conversion": "EV equivalent = points * 8 - 4, except 0 points = 0 EV",
            "field": field,
            "defender_item": defender_item,
            "defender_ability": defender_ability,
        },
    }


def explain_bulk_optimization(result):
    if result.get("best") is None:
        lines = []

        lines.append(
            f"No spread found for {result.get('defender')} that meets the goal "
            f"against {result.get('attacker')} {result.get('move')}."
        )

        lines.append("")
        lines.append("This means one of these is probably happening:")
        lines.append("The attack is too strong for the allowed 66-point spread.")
        lines.append("The selected natures are not enough.")
        lines.append("A defensive item, ability, screen, or recovery may be needed.")
        lines.append("The move may be a crit, super effective, or boosted too heavily.")

        return "\n".join(lines)

    defensive_stat = result["defensive_stat"]
    defensive_points_key = "def_points" if defensive_stat == "def" else "spd_points"
    defensive_ev_key = "def_ev" if defensive_stat == "def" else "spd_ev"
    defensive_label = "Def" if defensive_stat == "def" else "SpD"

    goal = result["goal"]

    lines = []

    lines.append(
        f"{result['defender']} bulk optimization vs {result['attacker']} {result['move']}"
    )
    lines.append("")

    # Answer first
    lines.append("Best spread found:")

    best = result["best"]

    lines.append(
        f"{best['nature']} nature, {best['hp_points']} HP / "
        f"{best[defensive_points_key]} {defensive_label} points "
        f"({best['total_points']} total points)"
    )

    lines.append(
        f"EV equivalent: {best['hp_ev']} HP / "
        f"{best[defensive_ev_key]} {defensive_label}"
    )

    lines.append("")

    # Practical outcome
    lines.append("What happens:")
    lines.append(
        f"Damage per hit: {best['damage_min']}–{best['damage_max']} HP"
    )
    lines.append(
        f"Using the {goal.get('damage_roll', 'max')} roll of "
        f"{best['chosen_damage']} per hit, final HP is "
        f"{best['sequence']['final_hp']}."
    )

    lines.append("")

    # Goal info
    lines.append("Goal checked:")
    lines.append(f"Goal: {goal.get('success_condition')} over {goal.get('hits', 1)} hit(s)")
    lines.append(f"Damage roll used: {goal.get('damage_roll', 'max')}")
    lines.append(f"Recovery: {goal.get('recovery', [])}")
    lines.append(f"Residual damage: {goal.get('residual_damage', [])}")

    lines.append("")

    # Other spreads if requested
    if result["mode"] in ["top_n", "all"]:
        lines.append(f"Other passing spreads shown: {result['showing']}")

        for spread in result["spreads"]:
            lines.append("")
            lines.append(
                f"{spread['nature']} {spread['hp_points']} HP / "
                f"{spread[defensive_points_key]} {defensive_label} points "
                f"({spread['total_points']} total points)"
            )
            lines.append(
                f"EV equivalent: {spread['hp_ev']} HP / "
                f"{spread[defensive_ev_key]} {defensive_label}"
            )
            lines.append(
                f"Damage: {spread['damage_min']}–{spread['damage_max']} HP"
            )
            lines.append(
                f"Final HP after sequence: {spread['sequence']['final_hp']}"
            )

    lines.append("")

    # Put assumptions lower
    lines.append("Assumptions:")
    for key, value in result["assumptions"].items():
        lines.append(f"{key}: {value}")

    lines.append("")

    # Percentages near the end
    lines.append("Percent damage:")
    lines.append(
        f"{best['damage_percent_min']}%–{best['damage_percent_max']}%"
    )

    lines.append("")

    # Sequence last
    lines.append("Sequence:")
    for step in best["sequence"]["log"]:
        lines.append(f"  {step}")

    lines.append("")

    # Rolls very last
    lines.append("Damage rolls:")
    lines.append(", ".join(str(x) for x in best["rolls"]))

    return "\n".join(lines)
