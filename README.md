# Pokémon Damage Agent

A command-line assistant that uses Gemini to parse battle questions and
`@smogon/calc` to calculate damage. Questions are independent; clarification
replies must restate the full battle.

## Setup and run

Requires Python 3.10+ and Node.js with npm.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
export GEMINI_API_KEY="your-key"
python agent.py
```

Example: `Sneasler Dire Claw into Primarina with max HP, no crit`
Type `quit` to exit. Questions are sent to Gemini; damage is calculated locally.

## Current support

- Direct damage, damage ranges, rolls, and calculator descriptions.
- Species/forms and moves available in the installed Smogon calculator.
- Levels, EVs, IVs, natures, abilities, items, boosts, and status.
- Critical hits, weather, terrain, Reflect, Light Screen, and Aurora Veil.
- Current HP percentages greater than zero and at most 100.
- Doubles by default; explicitly request singles to change that.

The parser defaults to generation 9, level 50, 31 IVs, zero EVs, and a neutral
nature. Its prompt interprets numeric stat investments as Champions points:
zero maps to zero EVs; positive points map to `8 * points - 4`. The prompt specifies
66 total points and 32 per stat. **Conversion and spread limits are currently
prompt instructions, not deterministic validation.** Explicit normal EV requests
are also accepted. This is a generation 9 calculation backend, not a complete
Champions ruleset implementation.

Grounding is inferred by Smogon from species, ability, item, and field mechanics.
Explicit `grounded` overrides are rejected. The CLI prints its parsed battle so
you can inspect assumptions. Natural-language parsing can still make mistakes.

## Unfinished and reference code

| File | Status |
| --- | --- |
| `agent.py` | Active Gemini parser and CLI |
| `showdown_bridge.py` | Active Python-to-Node bridge; callable without Gemini |
| `showdown_calc.js` | Active Smogon adapter |
| `optimizer.py` | Legacy, disconnected; imports missing `calculator.py` |
| `sequence_engine.py` | Legacy fixed-hit recovery/residual simulator used by the optimizer; not a full battle simulator |
| `files/pokedex.json` | Reference dataset; not read by the active calculator |
| `paths.py` | Legacy data paths, including files absent from this checkout |

Bulk optimization and multi-turn survival planning are unsupported in the CLI.
Reconnecting them requires migrating the optimizer's calculator interface and
checking sequence mechanics. Retained legacy files are not a supported API.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
```

Tests exercise the local calculator bridge and parser postprocessing without a
Gemini API key or network calls. Live Gemini parsing is not covered.
