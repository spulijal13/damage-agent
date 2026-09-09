# Pokémon Damage Agent

## Setup and run

Requires Python 3.10+ and Node.js with npm.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
export GEMINI_API_KEY="your-key"
python -m damage_agent.agent
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

Gemini receives a compact JSON list of every canonical Pokémon/form name, derived
at runtime by `damage_agent/pokemon_catalog.py` from `data/pokedex.json`. It resolves clear
misspellings and alternate form wording as part of parsing, and is instructed to
ask for clarification when the intended species/form is ambiguous. Python checks
that returned names exist in the catalog; it does not maintain aliases or perform
fuzzy matching. Smogon still checks whether a name is supported by the calculator.
The catalog is cached per process: update the Pokédex and restart the CLI to refresh
it. Only names are sent to Gemini, not the full stats/abilities dataset; this adds
prompt tokens to each request. No separate generated data file needs maintaining.

The battle builder defaults to generation 9, level 50, 31 IVs, zero EVs, and a neutral
nature. Gemini interprets numeric stat investments as Champions points; Python converts them:
zero maps to zero EVs; positive points map to `8 * points - 4`. Python caps points at 32 per stat. The 66-point total budget is not currently
validated. All CLI investments use Champions points, even when called EVs:
"32 HP EVs" means 32 Champions points (252 calculator EVs). The summary and
Smogon result display converted calculator EVs. This is a generation 9 calculation backend, not a complete
Champions ruleset implementation.

Grounding is inferred by Smogon from species, ability, item, and field mechanics.
Explicit `grounded` overrides are rejected. The CLI prints its parsed battle so
you can inspect assumptions. Natural-language parsing can still make mistakes.

## Unfinished and reference code

| File | Status |
| --- | --- |
| `damage_agent/agent.py` | Active Gemini parser and CLI |
| `damage_agent/battle_builder.py` | Local battle defaults and Champions point conversion |
| `damage_agent/pokemon_catalog.py` | Names-only context derived from the bundled Pokédex |
| `damage_agent/showdown_bridge.py` | Active Python-to-Node bridge; callable without Gemini |
| `calculator/showdown_calc.js` | Active Smogon adapter |
| `legacy/optimizer.py` | Legacy, disconnected; imports missing `calculator.py` |
| `legacy/sequence_engine.py` | Legacy fixed-hit recovery/residual simulator used by the optimizer; not a full battle simulator |
| `data/pokedex.json` | Source for parser name catalog; damage data comes from Smogon |
| `legacy/paths.py` | Legacy data paths, including files absent from this checkout |

Bulk optimization and multi-turn survival planning are unsupported in the CLI.
Reconnecting them requires migrating the optimizer's calculator interface and
checking sequence mechanics. Retained legacy files are not a supported API.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
```

Tests exercise the local calculator bridge and parser postprocessing without a
Gemini API key or network calls. Live Gemini parsing is not covered.

## Chat frontend (Chainlit)

From the repository directory:

```sh
source .venv/bin/activate
pip install -r requirements.txt
npm ci
chainlit run chainlit_app.py -w --host 127.0.0.1
```

Open http://localhost:8000. The frontend uses the same `GEMINI_API_KEY` from
`.env` as the CLI. It includes a black theme, a chat composer, and visible message
history within the current session. Chats are not persisted across new sessions.
Each request still needs the full battle; previous messages are not sent to Gemini.
The existing CLI remains available through `python -m damage_agent.agent`.

## Repository layout

```text
Damage_Agent/
├── damage_agent/       # Gemini parser, battle assembly, summaries, Node bridge
├── frontend/           # Chainlit chat entry point
├── calculator/         # Smogon JavaScript adapter
├── data/               # Pokédex JSON
├── legacy/             # Disconnected optimizer and sequence simulator
├── tests/              # Existing unit tests
├── public/             # Chainlit theme and styles
├── .chainlit/          # Chainlit configuration
├── chainlit_app.py     # Thin launcher for the frontend
├── chainlit.md         # Chainlit welcome/help content
├── requirements.txt    # Python dependencies
└── package.json        # Node dependencies
```

Run commands from the repository root. Chainlit discovers `public/`, `.chainlit/`,
and `chainlit.md` there, so these frontend resources intentionally stay at the root.
Keep `.env` at the root as well.
