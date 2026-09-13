# Move detail source

`moves.json` is a display-data snapshot fetched from
https://play.pokemonshowdown.com/data/moves.json on 2026-09-12.

It contains move names, base PP, type, base power, accuracy, category, priority,
short/full descriptions, and flags for variable/fixed damage. `accuracy: true`
means no accuracy check, not 100%. These are Showdown's default move values,
not a claim of Champions-specific move legality. Damage calculations still use
`@smogon/calc`; the snapshot only supplies display details. Refresh it deliberately
when updating the calculator's data version.
