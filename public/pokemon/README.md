Place Pokémon PNG artwork here. The team builder tries these filenames in order:

1. Catalog ID, e.g. `charizardmegay.png`
2. Exact canonical name, e.g. `Charizard-Mega-Y.png`
3. Pokédex number, e.g. `6.png`
4. Three-digit Pokédex number, e.g. `006.png`

Use the catalog ID or canonical name for distinct form artwork. Numeric filenames
are a fallback shared by forms. Missing artwork displays a placeholder.

The supplied `Sugimori_Art/` collection at the repository root is now preferred.
`damage_agent/artwork.py` matches its numbered filenames and form names; the team
API serves matched PNGs without copying the collection into this directory.
These filenames remain a fallback for artwork missing from the collection.
Restart Chainlit after adding artwork to refresh the cached index.
