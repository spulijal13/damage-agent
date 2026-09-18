"""Parser names and local ability defaults from the bundled Pokédex."""

import json
import re
from functools import lru_cache
from pathlib import Path

POKEDEX_PATH = Path(__file__).resolve().parents[1] / "data" / "pokedex.json"


@lru_cache(maxsize=1)
def _pokemon_by_name():
    """Read once per process, preserving the file's ability order."""
    pokedex = json.loads(POKEDEX_PATH.read_text(encoding="utf-8"))
    return {entry["name"]: entry for entry in pokedex.values()}


@lru_cache(maxsize=1)
def pokemon_names():
    """Updating the Pokédex needs no generated file."""
    return frozenset(_pokemon_by_name())


def default_ability(name):
    """Use the first listed ability for the exact species/form, if available."""
    entry = _pokemon_by_name().get(name, {})
    return next(iter(entry.get("abilities", {}).values()), None)


def base_stats(name):
    entry = _pokemon_by_name().get(name, {})
    parent = _pokemon_by_name().get(entry.get('baseSpecies'), {})
    stats = entry.get('baseStats') or parent.get('baseStats')
    if not stats:
        raise ValueError('Choose a Pokémon with known base stats.')
    return dict(stats)


@lru_cache(maxsize=1)
def pokemon_names_json():
    """Omit stats, abilities, and other data irrelevant to name matching."""
    return json.dumps(sorted(pokemon_names()), ensure_ascii=False, separators=(",", ":"))


# Presentation labels; canonical names stay stable in storage and calculations.
GENDERED_SPECIES = {'Indeedee', 'Meowstic', 'Basculegion', 'Oinkologne'}


def gendered_name(name):
    if name in GENDERED_SPECIES:
        return name + '-M'
    if re.search(r'-(M|F)(?:-|$)', name):
        return name
    return None


def display_name(name):
    name = gendered_name(name) or name
    base, *suffixes = name.split('-')
    genders = [part for part in suffixes if part in ('M', 'F')]
    forms = [part for part in suffixes if part not in ('M', 'F')]
    species = '-'.join([base, *genders])
    return f"{' '.join(forms)} {species}" if forms else species
