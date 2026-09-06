from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"

POKEDEX_PATH = FILES_DIR / "pokedex.json"
MOVES_PATH = FILES_DIR / "moves.json"
TYPE_CHART_PATH = FILES_DIR / "single_vs_dual_type_effectiveness.csv"

ABILITIES_JS_PATH = FILES_DIR / "abilities.js"
ABILITIES_REFINED_PATH = FILES_DIR / "abilities_refined.csv"

ITEMS_JS_PATH = FILES_DIR / "items.js"
ITEMS_REFINED_PATH = FILES_DIR / "items_refined.csv"