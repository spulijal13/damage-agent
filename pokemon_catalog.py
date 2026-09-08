"""Parser names and local ability defaults from the bundled Pokédex."""

import json
from functools import lru_cache
from pathlib import Path

POKEDEX_PATH = Path(__file__).resolve().parent / "files" / "pokedex.json"


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


@lru_cache(maxsize=1)
def pokemon_names_json():
    """Omit stats, abilities, and other data irrelevant to name matching."""
    return json.dumps(sorted(pokemon_names()), ensure_ascii=False, separators=(",", ":"))
