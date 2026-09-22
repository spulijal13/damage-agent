from damage_agent.pokemon_catalog import default_ability, base_stats
from fractions import Fraction
import math
from functools import lru_cache
from pathlib import Path
import json

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
BOOST_KEYS = ("atk", "def", "spa", "spd", "spe")
CHAMPIONS_MAX_POINTS_PER_STAT = 32


@lru_cache(maxsize=1)
def move_data():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/moves.json').read_text())


def apply_offensive_default(attacker, slot, move_name):
    """Default only the move's offensive investment; explicit zero stays zero."""
    move_id = ''.join(c for c in str(move_name).lower() if c.isalnum())
    move = move_data().get(move_id, {})
    # These attacks do not use the user's Attack or Special Attack investment.
    if move_id in ('bodypress', 'foulplay') or move.get('damage') or move.get('damageCallback'):
        return
    stat = {'Physical': 'atk', 'Special': 'spa'}.get(move.get('category'))
    spread = slot.get('spread') or slot.get('evs') or {}
    if stat and (not isinstance(spread, dict) or spread.get(stat) is None):
        attacker['evs'][stat] = CHAMPIONS_MAX_POINTS_PER_STAT

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
    """Return Champions stat points in @smogon/calc's `evs` API field."""
    evs = empty_stats()
    if not isinstance(slot, dict):
        return evs

    # Parser investments always use Champions units, even if labeled "evs".
    spread = slot.get("spread") or slot.get("evs") or {}
    for key, points in _int_map(spread, STAT_KEYS, default=0).items():
        evs[key] = min(CHAMPIONS_MAX_POINTS_PER_STAT, max(0, points))
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
    apply_offensive_default(attacker, extraction.get('attacker') or {}, extraction.get('move'))
    return {
        # @smogon/calc exposes Pokémon Champions as generation 0.
        "gen": 0 if extraction.get("gen") is None else extraction["gen"],
        "attacker": attacker,
        "defender": defender,
        "move": extraction.get("move"),
        "field": build_field(extraction.get("field"), attacker, defender),
    }


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
            f"  Champions points: {spread}",
            f"  HP: {pokemon.get('current_hp_percent', 100)}% | "
            f"Ability: {pokemon.get('ability') or 'Default (calculator)'} | "
            f"Item: {pokemon.get('item') or 'None'}",
        ])
        nature = pokemon.get('nature') or 'Serious'
        neutral = ' (neutral)' if nature in ('Serious', 'Hardy', 'Docile', 'Bashful', 'Quirky') else ''
        conditions = [f'Nature: {nature}{neutral}']
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


def optimize_bulk(name, total_points, bias=1, show_ranges=False, nature='Serious', stats_override=None):
    """Exact integer search for (B / Def + 1 / SpD) / HP; lower is better."""
    if type(total_points) is not int or not 0 <= total_points <= 66:
        raise ValueError('T must be a whole number from 0 to 66 Champions points.')
    if type(bias) not in (int, float) or not math.isfinite(bias) or bias < 0:
        raise ValueError('B must be a finite, nonnegative number; B=1 weights both sides equally.')
    if nature not in ('Serious', 'Hardy', 'Docile', 'Bashful', 'Quirky'):
        raise ValueError('This formula assumes a neutral nature. Use a neutral nature for weighted bulk optimization.')
    base = base_stats(name)
    if stats_override:
        if not isinstance(stats_override, dict) or any(
            k not in ('hp', 'def', 'spd') or type(v) is not int or not 1 <= v <= 255
            for k, v in stats_override.items()
        ):
            raise ValueError('Base HP, Defense and Sp. Defense overrides must be whole numbers from 1 to 255.')
        base.update(stats_override)
    if base['hp'] == 1:
        raise ValueError('This HP formula does not apply to Shedinja, whose HP stays at 1.')
    candidates = []
    for x in range(min(32, total_points) + 1):
        for y in range(min(32, total_points - x) + 1):
            z = total_points - x - y
            if not 0 <= z <= 32:
                continue
            hp, defense, spd = base['hp'] + 75 + x, base['def'] + 20 + y, base['spd'] + 20 + z
            candidates.append({'points': [x, y, z], 'stats': [hp, defense, spd],
                               'a': Fraction(1, hp * defense), 'c': Fraction(1, hp * spd)})
    weight = Fraction(str(bias))
    minimum = min(p['a'] * weight + p['c'] for p in candidates)
    best = [p for p in candidates if p['a'] * weight + p['c'] == minimum]
    result = {'name': name, 'total_points': total_points, 'bias': bias, 'nature': nature,
              'base_stats': base, 'custom_base_stats': bool(stats_override), 'score': float(minimum),
              'best': [{'points': p['points'], 'stats': p['stats']} for p in best]}
    if show_ranges:
        # Each spread is a line a*B+c. Build its lower envelope with exact
        # rational crossings, avoiding a sampled B grid and rounding errors.
        lines = {}
        for p in candidates:
            lines.setdefault((p['a'], p['c']), []).append(p)
        hull = []
        for (a, c), spreads in sorted(lines.items(), key=lambda pair: (-pair[0][0], pair[0][1])):
            if hull and hull[-1]['a'] == a:
                continue  # Same slope with a higher intercept is never optimal.
            start = None
            while hull:
                previous = hull[-1]
                start = (c - previous['c']) / (previous['a'] - a)
                if previous['start'] is None or start > previous['start']:
                    break
                hull.pop()
            hull.append({'a': a, 'c': c, 'spreads': spreads, 'start': start if hull else None})
        ranges = []
        for i, line in enumerate(hull):
            low = max(Fraction(0), line['start'] or Fraction(0))
            high = hull[i + 1]['start'] if i + 1 < len(hull) else None
            if high is not None and high < low:
                continue
            for p in line['spreads']:
                ranges.append({'points': p['points'], 'stats': p['stats'],
                               'low': float(low), 'high': float(high) if high is not None else None})
        result['ranges'] = ranges
    return result


def format_bulk_summary(result):
    if result.get('survival'):
        return format_survival_summary(result)
    x, y, z = result['best'][0]['points']
    hp, defense, spd = result['best'][0]['stats']
    lines = [f"**{result['name']} weighted bulk · T={result['total_points']} · B={result['bias']:g}**",
             f"Nature: {result['nature']} (neutral) · Level 50 · 31 IVs",
             f'**HP {x} / Def {y} / SpD {z} Champions points**',
             f'Stats: HP {hp} / Def {defense} / SpD {spd}',
             f"Objective: {result['score']:.10g} (lower is better)",
             'Minimized: (B / (base Def + 20 + y) + 1 / (base SpD + 20 + z)) / (base HP + 75 + x).',
             'x + y + z = T; 0–32 whole points per stat. B>1 favors physical bulk; B<1 favors special bulk.',
             'This is weighted stat bulk, not a guarantee of surviving a particular move.']
    base = result['base_stats']
    lines.insert(2, f"Base stats used: HP {base['hp']} / Def {base['def']} / SpD {base['spd']} "
                    f"({'explicit overrides' if result['custom_base_stats'] else 'bundled Pokédex'}).")
    if len(result['best']) > 1:
        lines.append('Equally optimal spreads (HP/Def/SpD): ' + ', '.join('/'.join(map(str, p['points'])) for p in result['best']))
    if 'ranges' in result:
        lines += ['', '| HP points | Def points | SpD points | HP | Def | SpD | B range |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for row in result['ranges']:
            high = '∞' if row['high'] is None else f"{row['high']:.4f}"
            values = [*row['points'], *row['stats'], f"[{row['low']:.4f}, {high}{')' if row['high'] is None else ']'}"]
            lines.append('| ' + ' | '.join(map(str, values)) + ' |')
        lines.append('B boundaries are rounded to four decimals; neighboring spreads tie at exact boundaries.')
    return '\n\n'.join(lines[:9]) + '\n' + '\n'.join(lines[9:])


def optimize_survival(bulk):
    """Find minimum defensive investment, then use weighted bulk to rank ties."""
    from damage_agent.showdown_bridge import run_calculator
    name = bulk.get('name')
    bias = bulk.get('bias') if bulk.get('bias') is not None else 1
    # Reuse the stat optimizer's species, budget and weight validation.
    optimize_bulk(name, 0, bias)
    if any(v is not None for v in (bulk.get('base_stats') or {}).values()):
        raise ValueError('Survival uses Smogon species stats. Clear custom base stats before checking attacks.')
    threats = bulk.get('threats') or []
    goal = bulk.get('goal') or 'minimum'
    if goal not in ('minimum', 'budget'):
        raise ValueError('Choose minimum points or best bulk within a budget.')
    if not isinstance(threats, list) or len(threats) > 6 or (not threats and goal == 'minimum'):
        raise ValueError('Name 1–6 threats, including each attacking Pokémon and move.')
    defender_slot = dict(bulk.get('defender') or {})
    defender_slot['name'] = name
    defender_slot['nature'] = bulk.get('nature') or defender_slot.get('nature') or 'Serious'
    spread = defender_slot.get('spread') or {}
    if any(type(v) is not int or not 0 <= v <= 32 for v in spread.values() if v is not None):
        raise ValueError('Fixed investments must be whole Champions points from 0 to 32.')
    reserved = sum(spread.get(s) or 0 for s in ('atk', 'spa', 'spe'))
    budget = 66 - reserved
    available = budget
    if goal == 'budget':
        budget = bulk.get('total_points')
        if type(budget) is not int or not 0 <= budget <= available:
            raise ValueError(f'Give a defensive budget from 0 to {available} Champions points.')
    probability = bulk.get('survival_percent') if bulk.get('survival_percent') is not None else 100
    if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 < probability <= 100:
        raise ValueError('Survival chance must be greater than 0 and at most 100 percent.')
    if available < 0:
        raise ValueError('Fixed offensive/speed investments exceed the legal 66-point total.')
    locked = {s: spread[s] for s in ('hp', 'def', 'spd') if spread.get(s) is not None}
    if sum(locked.values()) > budget:
        raise ValueError('Fixed investments exceed the legal 66-point total.')
    battles, hits = [], []
    for threat in threats:
        if not isinstance(threat, dict):
            raise ValueError('Each threat must specify an attacker and move.')
        attack = threat.get('attacker') or {}
        if not attack.get('name') or not threat.get('move'):
            raise ValueError('Each threat needs an attacking Pokémon and a move.')
        count = threat.get('hits') if threat.get('hits') is not None else (bulk['hits'] if bulk.get('hits') is not None else 1)
        if type(count) is not int or count not in (1, 2, 3):
            raise ValueError('Choose survival of 1, 2, or 3 consecutive uses of each attack.')
        battle = build_battle({'attacker': attack, 'defender': defender_slot,
                               'move': threat['move'], 'field': threat.get('field') or {}})
        defender = battle['defender']
        if defender['item'] in ('Focus Sash', 'Focus Band') or defender['ability'] in ('Sturdy', 'Disguise', 'Ice Face'):
            raise ValueError('This optimizer measures damage-based bulk; Focus Sash, Focus Band, Sturdy, Disguise and Ice Face survival effects are not supported. Choose another item/ability explicitly.')
        if ((defender['item'] or '').endswith('Berry') or defender['ability'] in ('Weak Armor', 'Stamina', 'Water Compaction', 'Seed Sower', 'Sand Spit')):
            raise ValueError('Repeated-hit optimization does not yet model consumed berries or reactive defensive/field changes. Choose another item/ability for probability analysis.')
        battles.append(battle)
        hits.append(count)
    feasible_budget = min(budget, sum(locked.values()) + 32 * (3-len(locked)))
    result = run_calculator({'operation': 'survival', 'battles': battles, 'budget': feasible_budget,
                             'bias': bias, 'locked': locked, 'hits': hits, 'goal': goal, 'survival_chance': probability / 100,
                             'defender': build_pokemon(defender_slot),
                             'current_hp_percent': build_pokemon(defender_slot)['current_hp_percent']}, timeout=300)
    result.update(survival=True, name=name, total_points=budget, bias=bias,
                  nature=defender_slot['nature'], battles=battles, locked=locked, reserved=reserved,
                  feasible_budget=feasible_budget, goal=goal, survival_percent=probability,
                  available=available, defender=build_pokemon(defender_slot))
    return result


def format_survival_summary(result):
    def spread(c):
        return ' / '.join(f'{value} {label}' for value, label in zip(c['points'], ('HP', 'Def', 'SpD')))

    def pokemon_summary(pokemon, points=None):
        investments = dict(pokemon['evs'])
        if points is not None:
            investments.update(zip(('hp', 'def', 'spd'), points))
        investment = ' / '.join(f'{v} {STAT_LABELS[k]}' for k, v in investments.items() if v) or '0'
        settings = [f"{pokemon['name']}: HP: {pokemon['current_hp_percent']}%",
                    f"Nature: {pokemon['nature']}", f"Ability: {pokemon.get('ability') or 'Default'}",
                    f"Item: {pokemon.get('item') or 'None'}", f"Spread: {investment} points"]
        if pokemon.get('status'):
            settings.append(f"Status: {pokemon['status']}")
        settings += [f'{STAT_LABELS[k]}: {v:+d}' for k, v in pokemon['boosts'].items() if v]
        return ' · '.join(settings)

    budget_mode = result['goal'] == 'budget'
    chosen = result['full_budget'] if budget_mode else result['minimum']
    shown = chosen or result['fallback']
    defender = result['defender']
    lines = [f"**{result['name']} · {result['nature']} nature**"]
    if chosen:
        lines += [f"**{spread(chosen)}** Champions points",
                  f"{'Best bulk within your budget' if budget_mode else 'Fewest points meeting your goal'}: "
                  f"**{chosen['total']} points** · {result['available']-chosen['total']} left for other stats"]
    else:
        lines.append(f"**No spread meets {result['survival_percent']:g}% survival against every threat.**")
        if shown:
            lines.append(f"Closest option: **{spread(shown)}** · weakest matchup: "
                         f"{100*shown['worst_probability']:.2f}% survival")
    if shown:
        stats = shown['stats']
        lines.append(f"Stats: {stats['hp']} HP · {stats['def']} Def · {stats['spd']} SpD")
    lines.append(pokemon_summary(defender, shown['points'] if shown else None))
    for battle in result['battles']:
        lines.append(pokemon_summary(battle['attacker']))
        effects = [f'{k}: {v}' for k, v in battle['field'].items() if v and k != 'is_double_battle']
        if effects:
            lines.append(f"{battle['attacker']['name']} field: " + ' · '.join(effects))
    if shown:
        if shown['reports']:
            lines.append('Damage on the first use (% of maximum HP; investments shown in Champions points):')
        for report in shown['reports']:
            ko_text = 'cannot KO within 3 uses'
            for uses, chance in enumerate(report['ko'], 1):
                if chance > 0:
                    label = 'OHKO' if uses == 1 else f'{uses}HKO'
                    ko_text = (f'guaranteed {label}' if chance == 1
                               else f'{100*chance:.2f}% chance to {label}')
                    break
            if report['starting_hp'] != stats['hp']:
                ko_text += f" from {report['starting_hp']}/{stats['hp']} starting HP"
            rolls = report['damage_rolls']
            percentages = ', '.join(f'{math.floor(1000*d/stats["hp"])/10:g}%' for d in rolls)
            lines.append(f"{report['damage_description']} -- {ko_text}\n"
                         f"Possible damage amounts: ({', '.join(map(str, rolls))})\n"
                         f"Possible damage percentages: ({percentages})\n"
                         f"**{100*report['survival_probability']:.2f}% survive {report['hits']} use(s)**\n"
                         f"KO by 1 / 2 / 3 uses: " + ' / '.join(f'{100*p:.2f}%' for p in report['ko']))
    minimum = result['minimum']
    if budget_mode and minimum and (not chosen or minimum['points'] != chosen['points']):
        lines.append(f"Cheapest alternative: **{spread(minimum)}** · {minimum['total']} points")
    formats = ['singles' if b['field'].get('is_double_battle') is False else 'doubles'
               for b in result['battles']]
    if len(set(formats)) > 1:
        calculation = 'Calculated in ' + ', '.join(
            f"{mode} for {b['attacker']['name']} ({b['move']})" for b, mode in zip(result['battles'], formats))
    else:
        calculation = f'Calculated in {formats[0]}' if formats else ''
    lines.append('Level 50' + (f' · {calculation}' if calculation else '') + '. Odds assume each attack lands, fixed attacker/field, '
                 'and no healing, residual damage, or other between-use effects. Threats are checked separately.')
    if result['cells'] and result['battles']:
        # Stored with the message, rendered locally; never sent back as LLM context.
        data = {'budget': result['feasible_budget'], 'cells': result['cells'],
                'threats': [f"{b['attacker']['name']} — {b['move']}" for b in result['battles']],
                'recommended': chosen['points'] if chosen else None,
                'minimum': minimum['points'] if minimum else None}
        lines.append('Explore how HP and Defense change KO odds below. Each cell spends the shown budget; the remainder goes into SpD.')
        lines.append('```bulk-heatmap\n' + json.dumps(data, separators=(',', ':')) + '\n```')
    return '\n\n'.join(lines)
