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

## Team builder (first iteration)

Start Chainlit using the existing command above, then select **Team builder** in
its top navigation. Create any number of named teams, rename/delete teams, and
add/edit/remove up to six Pokémon per team. Switching tabs keeps the chat and
unsaved Pokémon editor mounted. Click **Save Pokémon** to commit changes.

Selecting a species/form fills its base stats, types, and ability choices. The six
sliders allocate Champions points: 0–32 per stat and at most 66 total. The UI shows
species base stats separately from calculated level-50 stats (31 IVs), including
nature changes. Four move slots and an optional held item are available. Move and
item names come from the installed Smogon catalog; species learnsets and full
format legality are not checked. Incomplete move sets can be saved while building.

The shared library uses SQLite, independently of Gemini and chat sessions:

- `teams`: `team_id` primary key and `team_name`.
- `team_pokemon`: `pokemon_id` primary key; `team_id` foreign key with cascading
  deletion; species name/number, ability, nullable item, six species base stats,
  six `*_points` investments, nature, four nullable moves, and two types.
- SQL constraints reject duplicate Pokédex numbers (including alternate forms),
  duplicate held items within a team, fractional/out-of-range point values, and
  point totals above 66. Multiple Pokémon can have no held item.
- Base stats/types/numbers are derived on the server, not trusted from the browser.

The default database is `storage/teams.sqlite3`, excluded from Git and outside
public assets. Set `TEAM_DB_PATH` to override it. Saved teams survive local app
restarts. Back up this database for recovery. This iteration is a **shared workspace**,
with no account ownership or private per-user teams; all visitors can edit its teams.
It does not yet connect saved teams to battle memory or recommendations.

**Hosted persistence:** the existing free-service `render.yaml` does not provide a
persistent filesystem. `render.persistent.yaml` is an optional replacement blueprint
with paid compute and a persistent disk mounted at `/app/storage`. Use that storage
configuration before relying on hosted saves; do not deploy the team library with
an ephemeral database. No deployment or billing change is performed by this repo edit.
For other Docker hosts, mount a writable persistent volume at `/app/storage`.

**Artwork:** put supplied PNGs in `public/pokemon/`. See
`public/pokemon/README.md` for supported filenames. Artwork appears immediately on
selection and remains beside ability/item controls; missing PNGs use a placeholder.
Canonical IDs/names support distinct form art; numeric filenames provide a fallback.

Implementation: `damage_agent/teams.py` owns storage/validation,
`frontend/team_api.py` exposes the API ahead of Chainlit's SPA fallback, and
`public/navigation.js` adds the tabs. `public/teams.html`, `teams.css`, `teams.js`,
and `team-stats.js` implement the editor without an additional build step.

Additional stat-display verification:

```sh
node tests/test_team_stats.js
```

The supplied `Sugimori_Art/` folder is also supported directly and included in the
Docker image. `damage_agent/artwork.py` indexes numbered PNGs, prefers the main
collection over alternate versions, and maps form naming differences. Matched
images are served through `/api/teams/art/{pokemon_id}` and shown on selection and
saved team cards. When a form name does not match, artwork falls back to the same Pokédex
number, preferring the main species illustration. If that number has no artwork,
the existing `public/pokemon/` fallback and placeholder remain available. Restart Chainlit after adding artwork files.
