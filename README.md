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

The battle builder defaults to generation 9, level 50, 31 IVs, and a Serious (neutral)
nature for both Pokémon, always displayed in the battle summary. The attacker defaults
to 32 Champions points in Attack for physical moves or Special Attack for special
moves, unless that stat was explicitly specified (including zero). Other unspecified
stats, including the defender's, remain zero. Moves that use neither offensive stat
(Body Press, Foul Play, fixed-damage and status moves) do not receive this default.
Defaults are recalculated for the current move on follow-ups, while explicit
investments and natures persist. Gemini interprets numeric stat investments as Champions points; Python converts them:
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

The legacy attack-specific optimizer and multi-turn survival planning remain
unsupported. Reconnecting them requires migrating the optimizer's calculator
interface and checking sequence mechanics. Retained legacy files are not a supported API.

## Weighted bulk optimization

Chat and CLI support the stat-based objective:

```text
minimize (B / (base Def + 20 + y) + 1 / (base SpD + 20 + z)) / (base HP + 75 + x)
subject to x + y + z = T, with integer x, y, z between 0 and 32.
```

`x`, `y`, and `z` are HP, Defense, and Special Defense Champions points.
Supply a Pokémon and a total defensive budget `T` (0–66). `B` defaults to 1:
larger values favor physical bulk; smaller values favor special bulk; zero
optimizes special bulk alone. The formula assumes level 50, 31 IVs, and a neutral
nature. Non-neutral natures and Shedinja's exceptional HP are rejected rather
than silently calculated with the wrong formula. This score is not a guarantee
of surviving any particular attack and does not model items, abilities, or field effects.

Examples:

- `Optimize Volcarona bulk with T=11 and B=1`
- `Now use B=2`
- `Show the optimal spreads for all B ranges`
- `Use base HP 85, base Defense 75, base SpD 105, T=11, B=1 and show B ranges`

The supplied reference uses Volcarona base Defense 75; the bundled Pokédex has
65. With the reference's explicit base stats, the optimum at B=1 is 10 HP / 1 Def /
0 SpD, giving 170 HP / 96 Def / 125 SpD. Its B interval is [0.9728, 1.020493...].
With the bundled stats the optimum is 3 HP / 8 Def / 0 SpD. Every result displays
its base stats and whether explicit overrides were used. Changing species clears
old base-stat overrides; `use catalog base stats` also clears them.

`damage_agent/battle_builder.py` performs the exhaustive integer search and
computes B intervals from exact rational line intersections. Gemini only extracts
the inputs. `damage_agent/agent.py` routes bulk requests and preserves their inputs
for follow-ups independently of damage battle inputs. The chat renders B-range
tables; tied optima at the requested B are reported, and table boundaries are
rounded to four decimals.

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
history with **New chat** and a sidebar for reopening, renaming, searching by title, and
deleting saved chats. Each chat keeps its own battle slots and the last six turns
for follow-up questions and clarification answers. Gemini returns changes to that
battle; Python merges them before recalculating. Starting a new chat clears context.
The existing CLI remains available through `python -m damage_agent.agent`.

Chat history lives in `storage/chats.sqlite3` (override with `CHAT_DB_PATH`). It is
a **public shared library with no login**: all visitors can read, continue, rename,
and delete its chats. Chat context is isolated per conversation, not per visitor.
Existing chats from before persistence was enabled cannot be recovered.

The app uses a custom chat sidebar because Chainlit's built-in history requires
authentication. Chainlit still hosts the application with the same startup command.
`public/workspace.html` and `navigation.js` keep the chat and team-builder pages
mounted across tab switches. `public/chats.html`, `chats.js`, and `chats.css` implement
the chat UI; `frontend/chat_api.py` owns `/api/chats` and SQLite storage,
committing messages and battle context atomically. Concurrent changes return a conflict
instead of overwriting a newer turn. Failed calculations leave the saved context intact.
Follow-up parsing, context, and merging live in `damage_agent/agent.py`; the CLI
continues to use standalone requests.

Hosted chat history needs persistent storage just like teams; the optional Render
persistent-disk blueprint covers both default databases. Back up both databases.
No separate database service or authentication secret is needed.

### Chat context limits

- SQLite retains all saved messages until you delete the chat.
- Each Gemini request includes the current structured battle, the latest **six
  user/assistant exchanges** (12 messages), and the new question, alongside the
  parser instructions and Pokémon names catalog.
- Each message in the recent context is capped at **8,000 characters**. These are
  application limits, configured by `CONTEXT_TURNS` and `CONTEXT_MESSAGE_CHARS`
  in `damage_agent/agent.py`, not Gemini's model context-window limits.
- Current battle fields survive when their original messages leave the six-turn
  window. Earlier conversation details and previous battle variants are not
  automatically retrieved from SQLite. The parser is instructed to ask for missing
  details rather than invent them. A new chat or explicit new battle clears context.
- There is no turn count that guarantees hallucinations will begin or cannot happen.
  Parsing can be wrong on any turn; the damage arithmetic still runs locally in
  Smogon. The displayed battle summary lets you check the interpreted assumptions.

## Repository layout

```text
Damage_Agent/
├── damage_agent/       # Parser/context, battle assembly/summary, catalog, team logic, Node bridge
├── frontend/           # Chat API + SQLite; team API + shared HTTP middleware
├── calculator/         # Smogon JavaScript adapter
├── data/               # Pokédex JSON
├── legacy/             # Disconnected optimizer and sequence simulator
├── tests/              # Existing unit tests
├── public/             # Chainlit theme and styles
├── .chainlit/          # Chainlit configuration
├── chainlit_app.py     # Chainlit launch, lifecycle handlers, route registration
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

The supplied `images/pokemon_art/` folder is also supported directly and included in the
Docker image. `damage_agent/artwork.py` indexes numbered PNGs, prefers the main
collection over alternate versions, and maps form naming differences. Matched
images are served through `/api/teams/art/{pokemon_id}` and shown on selection and
saved team cards. When a form name does not match, artwork falls back to the same Pokédex
number, preferring the main species illustration. If that number has no artwork,
the existing `public/pokemon/` fallback and placeholder remain available. Restart Chainlit after adding artwork files.

Selecting a move now displays its base PP, type icon, category, base power,
accuracy, priority, and short description, with an expandable full description.
Details are served from the bundled Showdown snapshot `data/moves.json`; see
`data/moves-source.md` for provenance. No live request is made when selecting moves.
Type PNGs are served from `images/type_icons/` and also appear in move suggestions.

Champions learnsets are read from `data/champions_learnsets.json`. There is no
startup fetch or timed refresh. To deliberately download, validate, and atomically
replace this file, run `python -m damage_agent.champions_learnsets`. Failed updates
preserve the previous file. The future admin panel can call `refresh_learnsets()`;
no public update endpoint is exposed. Newly loaded catalogs use the updated file;
refresh an already-open team builder to see it. For updates made locally, commit
and deploy the changed JSON to keep it across Render deployments. Updating the
file on free Render only changes that running instance's ephemeral filesystem.
