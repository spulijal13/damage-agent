"""Persistent shared team library. Stat investments are Champions points, not EVs."""
from damage_agent.artwork import artwork_path

import json
import os
import sqlite3
import subprocess
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ('hp', 'atk', 'spa', 'def', 'spd', 'spe')


@lru_cache(maxsize=1)
def catalog():
    pokedex = json.loads((ROOT / 'data/pokedex.json').read_text())
    choices = json.loads(subprocess.run(
        ['node', str(ROOT / 'calculator/team_catalog.js')],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout)
    by_name = {p['name']: p for p in pokedex.values()}
    # Cosmetic forms inherit their species data in the bundled Showdown dataset.
    pokedex = {key: {**by_name.get(p.get('baseSpecies'), {}), **p}
               for key, p in pokedex.items()}
    choices['pokemon'] = [
        {'name': p['name'], 'id': key, 'num': p['num'],
         'types': p['types'], 'base_stats': p['baseStats'],
         'abilities': list(dict.fromkeys(p['abilities'].values())),
         'default_item': p.get('requiredItem') if p.get('forme', '').startswith('Mega') else None}
        for key, p in pokedex.items() if p.get('num', 0) > 0
    ]
    for pokemon in choices['pokemon']:
        pokemon['art_url'] = f"/api/teams/art/{pokemon['id']}" if artwork_path(pokemon) else None
    return choices


SCHEMA = '''
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT NOT NULL CHECK(length(trim(team_name)) BETWEEN 1 AND 100)
);
CREATE TABLE IF NOT EXISTS team_pokemon (
    pokemon_id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    pokedex_number INTEGER NOT NULL,
    ability TEXT NOT NULL,
    item TEXT COLLATE NOCASE CHECK(item IS NULL OR length(trim(item)) > 0),
    base_hp INTEGER NOT NULL, base_atk INTEGER NOT NULL,
    base_spa INTEGER NOT NULL, base_def INTEGER NOT NULL,
    base_spd INTEGER NOT NULL, base_spe INTEGER NOT NULL,
    hp_points INTEGER NOT NULL CHECK(typeof(hp_points) = 'integer' AND hp_points BETWEEN 0 AND 32),
    atk_points INTEGER NOT NULL CHECK(typeof(atk_points) = 'integer' AND atk_points BETWEEN 0 AND 32),
    spa_points INTEGER NOT NULL CHECK(typeof(spa_points) = 'integer' AND spa_points BETWEEN 0 AND 32),
    def_points INTEGER NOT NULL CHECK(typeof(def_points) = 'integer' AND def_points BETWEEN 0 AND 32),
    spd_points INTEGER NOT NULL CHECK(typeof(spd_points) = 'integer' AND spd_points BETWEEN 0 AND 32),
    spe_points INTEGER NOT NULL CHECK(typeof(spe_points) = 'integer' AND spe_points BETWEEN 0 AND 32),
    nature TEXT NOT NULL,
    move_1 TEXT, move_2 TEXT, move_3 TEXT, move_4 TEXT,
    type_1 TEXT NOT NULL, type_2 TEXT,
    UNIQUE(team_id, pokedex_number),
    UNIQUE(team_id, item),
    CHECK(hp_points + atk_points + spa_points + def_points + spd_points + spe_points <= 66)
);
'''


@contextmanager
def connection():
    path = Path(os.environ.get('TEAM_DB_PATH', str(ROOT / 'storage/teams.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript(SCHEMA)
    try:
        with db:
            yield db
    finally:
        db.close()


def team_name(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        raise ValueError('Team name must contain 1–100 characters.')
    return value.strip()


def require_team(db, team_id):
    if not db.execute('SELECT 1 FROM teams WHERE team_id=?', (team_id,)).fetchone():
        raise LookupError('Team not found.')


def list_teams():
    with connection() as db:
        teams = [dict(row) for row in db.execute('SELECT * FROM teams ORDER BY team_id DESC')]
        for team in teams:
            team['pokemon'] = [dict(row) for row in db.execute(
                'SELECT * FROM team_pokemon WHERE team_id=? ORDER BY pokemon_id', (team['team_id'],))]
        return teams


def create_team(name):
    with connection() as db:
        return db.execute('INSERT INTO teams(team_name) VALUES (?)', (team_name(name),)).lastrowid


def rename_team(team_id, name):
    with connection() as db:
        require_team(db, team_id)
        db.execute('UPDATE teams SET team_name=? WHERE team_id=?', (team_name(name), team_id))


def delete_team(team_id):
    with connection() as db:
        require_team(db, team_id)
        db.execute('DELETE FROM teams WHERE team_id=?', (team_id,))


def validate_member(data):
    choices = catalog()
    species = next((p for p in choices['pokemon'] if p['name'] == data.get('name')), None)
    if species is None:
        raise ValueError('Select a Pokémon from the catalog.')
    ability = data.get('ability')
    if ability not in species['abilities']:
        raise ValueError('Select an ability available to this Pokémon.')
    item = data.get('item') or None
    if item is not None and item not in choices['items']:
        raise ValueError('Select an item from the catalog, or leave it empty.')
    nature = data.get('nature', 'Serious')
    if not isinstance(nature, str) or nature not in {n['name'] for n in choices['natures']}:
        raise ValueError('Select a valid nature.')
    points = [data.get(f'{s}_points', 0) for s in STATS]
    if any(type(p) is not int or not 0 <= p <= 32 for p in points) or sum(points) > 66:
        raise ValueError('Use 0–32 whole points per stat and at most 66 across all six stats.')
    moves = [data.get(f'move_{i}') or None for i in range(1, 5)]
    if any(m is not None and (not isinstance(m, str) or m not in choices['moves']) for m in moves):
        raise ValueError('Select moves from the catalog.')
    nonempty = [m for m in moves if m]
    if len(nonempty) != len(set(nonempty)):
        raise ValueError('Choose different moves in each slot.')
    return [species['name'], species['num'], ability, item,
            *[species['base_stats'][s] for s in STATS], *points, nature, *moves,
            species['types'][0], species['types'][1] if len(species['types']) > 1 else None]


def save_member(team_id, data, pokemon_id=None):
    values = validate_member(data)
    columns = ['name', 'pokedex_number', 'ability', 'item',
               *[f'base_{s}' for s in STATS], *[f'{s}_points' for s in STATS],
               'nature', 'move_1', 'move_2', 'move_3', 'move_4', 'type_1', 'type_2']
    try:
        with connection() as db:
            require_team(db, team_id)
            if pokemon_id is None:
                # Lock before counting so simultaneous additions cannot exceed six.
                db.execute('BEGIN IMMEDIATE')
                count = db.execute('SELECT count(*) FROM team_pokemon WHERE team_id=?', (team_id,)).fetchone()[0]
                if count >= 6:
                    raise ValueError('A team can contain up to six Pokémon.')
                return db.execute(
                    f"INSERT INTO team_pokemon(team_id,{','.join(columns)}) VALUES ({','.join('?' for _ in range(len(columns)+1))})",
                    [team_id, *values]).lastrowid
            result = db.execute(
                f"UPDATE team_pokemon SET {','.join(c+'=?' for c in columns)} WHERE team_id=? AND pokemon_id=?",
                [*values, team_id, pokemon_id])
            if not result.rowcount:
                raise LookupError('Pokémon not found on this team.')
            return pokemon_id
    except sqlite3.IntegrityError as exc:
        if 'pokedex_number' in str(exc):
            raise ValueError('This Pokédex number is already on the team, including alternate forms.') from None
        if 'team_pokemon.item' in str(exc):
            raise ValueError('That held item is already used on this team.') from None
        raise


def delete_member(team_id, pokemon_id):
    with connection() as db:
        result = db.execute('DELETE FROM team_pokemon WHERE team_id=? AND pokemon_id=?', (team_id, pokemon_id))
        if not result.rowcount:
            raise LookupError('Pokémon not found on this team.')
