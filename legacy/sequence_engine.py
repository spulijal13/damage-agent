import math


def choose_damage_from_rolls(rolls, damage_roll="max"):
    if not rolls:
        return 0

    damage_roll = str(damage_roll).lower()

    if damage_roll == "max":
        return max(rolls)

    if damage_roll == "min":
        return min(rolls)

    if damage_roll in ["average", "avg", "mean"]:
        return math.floor(sum(rolls) / len(rolls))

    return max(rolls)


def apply_recovery(current_hp, max_hp, recovery_name, berry_used=False):
    if recovery_name is None:
        return current_hp, berry_used

    key = str(recovery_name).lower().replace(" ", "").replace("-", "")

    if key in ["leftovers", "blacksludge", "grassyterrain"]:
        current_hp += math.floor(max_hp / 16)

    elif key == "sitrusberry":
        if not berry_used and current_hp > 0 and current_hp <= math.floor(max_hp / 2):
            current_hp += math.floor(max_hp / 4)
            berry_used = True

    elif key == "oranberry":
        if not berry_used and current_hp > 0 and current_hp <= math.floor(max_hp / 2):
            current_hp += 10
            berry_used = True

    current_hp = min(current_hp, max_hp)
    return current_hp, berry_used


def apply_residual_damage(current_hp, max_hp, residual_name, toxic_counter=1):
    if residual_name is None:
        return current_hp, toxic_counter

    key = str(residual_name).lower().replace(" ", "").replace("-", "")

    if key in ["sandstorm", "hail", "snowchip"]:
        current_hp -= math.floor(max_hp / 16)

    elif key == "burn":
        current_hp -= math.floor(max_hp / 16)

    elif key == "poison":
        current_hp -= math.floor(max_hp / 8)

    elif key in ["toxic", "badlypoisoned"]:
        current_hp -= math.floor(max_hp * toxic_counter / 16)
        toxic_counter += 1

    elif key == "saltcure":
        current_hp -= math.floor(max_hp / 8)

    current_hp = max(current_hp, 0)
    return current_hp, toxic_counter


def simulate_hit_sequence(
    max_hp,
    damage_per_hit=None,
    damage_rolls=None,
    hits=1,
    damage_roll="max",
    recovery_effects=None,
    residual_effects=None,
    recovery=None,
    residual_damage=None,
    starting_hp_percent=100,
    apply_end_of_turn_after_final_hit=False,
):
    recovery_effects = recovery_effects if recovery_effects is not None else recovery
    residual_effects = residual_effects if residual_effects is not None else residual_damage

    recovery_effects = recovery_effects or []
    residual_effects = residual_effects or []

    if damage_per_hit is None:
        damage_per_hit = choose_damage_from_rolls(damage_rolls or [], damage_roll)

    current_hp = math.floor(max_hp * starting_hp_percent / 100)

    berry_used = False
    toxic_counter = 1
    log = []

    for hit_number in range(1, hits + 1):
        log.append(f"Before hit {hit_number}: {current_hp}/{max_hp} HP")

        current_hp -= damage_per_hit
        current_hp = max(current_hp, 0)

        log.append(f"Hit {hit_number}: took {damage_per_hit} damage, now at {current_hp}/{max_hp} HP")

        if current_hp <= 0:
            log.append(f"Fainted after hit {hit_number}.")
            break

        is_final_hit = hit_number == hits

        if is_final_hit and not apply_end_of_turn_after_final_hit:
            continue

        for recovery_name in recovery_effects:
            before = current_hp
            current_hp, berry_used = apply_recovery(
                current_hp=current_hp,
                max_hp=max_hp,
                recovery_name=recovery_name,
                berry_used=berry_used,
            )
            log.append(f"{recovery_name}: healed from {before} to {current_hp} HP")

        for residual_name in residual_effects:
            before = current_hp
            current_hp, toxic_counter = apply_residual_damage(
                current_hp=current_hp,
                max_hp=max_hp,
                residual_name=residual_name,
                toxic_counter=toxic_counter,
            )
            log.append(f"{residual_name}: dropped from {before} to {current_hp} HP")

            if current_hp <= 0:
                log.append(f"Fainted after {residual_name}.")
                break

        if current_hp <= 0:
            break

    return {
        "max_hp": max_hp,
        "starting_hp": math.floor(max_hp * starting_hp_percent / 100),
        "final_hp": current_hp,
        "ending_hp": current_hp,
        "hits_requested": hits,
        "damage_per_hit": damage_per_hit,
        "recovery": recovery_effects,
        "residual_damage": residual_effects,
        "survived": current_hp > 0,
        "survived_sequence": current_hp > 0,
        "fainted": current_hp <= 0,
        "log": log,
    }