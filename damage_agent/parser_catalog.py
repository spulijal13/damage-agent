"""Canonical parser vocabulary; spelling resolution belongs to the LLM."""
import json
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def parser_catalog():
    script = Path(__file__).resolve().parents[1] / 'calculator/parser_catalog.js'
    result = subprocess.run(['node', str(script)], capture_output=True, text=True,
                            check=True, timeout=30)
    catalog = json.loads(result.stdout)
    # Supported field values and the explicit ability-removal sentinel.
    catalog['abilities'] = sorted(set(catalog['abilities']) | {'No Ability'})
    catalog['weather'] = ['Sand', 'Sun', 'Rain', 'Hail', 'Snow', 'Harsh Sunshine',
                          'Heavy Rain', 'Strong Winds']
    catalog['terrain'] = ['Electric', 'Grassy', 'Psychic', 'Misty']
    catalog['status'] = ['brn', 'par', 'psn', 'tox', 'slp', 'frz']
    return catalog


@lru_cache(maxsize=1)
def parser_catalog_json():
    return json.dumps(parser_catalog(), ensure_ascii=False, separators=(',', ':'))


def validate_parser_names(request):
    """Reject invented output before calculation; do not fuzzy-match locally."""
    catalog = parser_catalog()
    categories = {'move': 'moves', 'item': 'items', 'ability': 'abilities',
                  'nature': 'natures', 'weather': 'weather',
                  'terrain': 'terrain', 'status': 'status'}

    def visit(value):
        if isinstance(value, list):
            for entry in value:
                visit(entry)
        elif isinstance(value, dict):
            for key, entry in value.items():
                if key in categories and entry is not None:
                    # Empty strings represent removal of optional conditions.
                    if entry == '' and key in ('item', 'ability', 'weather', 'terrain', 'status'):
                        continue
                    if not isinstance(entry, str) or entry not in catalog[categories[key]]:
                        raise ValueError(f'I could not resolve the {key} {entry!r} to the supported catalog. Please clarify which {key} you mean.')
                visit(entry)

    visit(request)
    return request
