"""Names-only parser context derived from the bundled Pokédex."""

import json
from functools import lru_cache
from pathlib import Path

POKEDEX_PATH = Path(__file__).resolve().parent / "files" / "pokedex.json"


@lru_cache(maxsize=1)
def pokemon_names():
    """Read once per process; updating the Pokédex needs no generated file."""
    pokedex = json.loads(POKEDEX_PATH.read_text(encoding="utf-8"))
    return frozenset(entry["name"] for entry in pokedex.values())


@lru_cache(maxsize=1)
def pokemon_names_json():
    """Omit stats, abilities, and other data irrelevant to name matching."""
    return json.dumps(sorted(pokemon_names()), ensure_ascii=False, separators=(",", ":"))
