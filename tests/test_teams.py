import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from damage_agent import teams
from frontend.team_api import router


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'TEAM_DB_PATH': self.tmp.name + '/teams.sqlite3'})
        self.env.start()
        self.team = teams.create_team('Rain offense')

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def member(self, name='Pikachu', ability='Static', **kwargs):
        return {'name': name, 'ability': ability, 'nature': 'Timid', **kwargs}

    def test_persistence_rename_edit_and_cascade(self):
        member_id = teams.save_member(self.team, self.member(hp_points=32, atk_points=32, spe_points=2))
        teams.rename_team(self.team, 'Rain revised')
        saved = teams.list_teams()[0]
        self.assertEqual(saved['team_name'], 'Rain revised')
        self.assertEqual(saved['pokemon'][0]['base_hp'], 35)
        self.assertIsNone(saved['pokemon'][0]['type_2'])
        teams.save_member(self.team, self.member(item='Life Orb', move_1='Thunderbolt'), member_id)
        self.assertEqual(teams.list_teams()[0]['pokemon'][0]['item'], 'Life Orb')
        teams.delete_team(self.team)
        with teams.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM team_pokemon').fetchone()[0], 0)

    def test_species_and_item_clauses(self):
        teams.save_member(self.team, self.member(item='Life Orb'))
        with self.assertRaisesRegex(ValueError, 'Pokédex'):
            teams.save_member(self.team, self.member())
        with self.assertRaisesRegex(ValueError, 'held item'):
            teams.save_member(self.team, self.member('Raichu', item='Life Orb'))
        other = teams.create_team('Another team')
        teams.save_member(other, self.member(item='Life Orb'))
        # Multiple item-less Pokémon are allowed.
        teams.save_member(self.team, self.member('Raichu'))
        teams.save_member(self.team, self.member('Bulbasaur', 'Overgrow'))

    def test_forms_share_species_clause(self):
        teams.save_member(self.team, self.member('Charizard', 'Blaze'))
        with self.assertRaisesRegex(ValueError, 'Pokédex'):
            teams.save_member(self.team, self.member('Charizard-Mega-Y', 'Drought'))

    def test_budget_and_catalog_validation(self):
        for change in ({'hp_points':33}, {'hp_points':-1}, {'hp_points':1.5},
                       {'hp_points':True}, {'hp_points':32, 'atk_points':32, 'spe_points':3},
                       {'ability':'Drought'}, {'item':'Made up'}, {'nature':'Fake'},
                       {'move_1':'Fake'}, {'move_1':'Protect', 'move_2':'Protect'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                teams.save_member(self.team, self.member(**change))

    def test_database_enforces_budget_foreign_key_and_item(self):
        member_id = teams.save_member(self.team, self.member(item='Life Orb'))
        second = teams.save_member(self.team, self.member('Raichu'))
        statements = [
            ('UPDATE team_pokemon SET hp_points=32, atk_points=32, spe_points=3 WHERE pokemon_id=?', member_id),
            ('UPDATE team_pokemon SET team_id=999 WHERE pokemon_id=?', member_id),
            ("UPDATE team_pokemon SET item='life orb' WHERE pokemon_id=?", second),
        ]
        for sql, value in statements:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError), teams.connection() as db:
                db.execute(sql, (value,))

    def test_six_members_and_missing_update(self):
        for name, ability in [('Pikachu','Static'),('Raichu','Static'),('Bulbasaur','Overgrow'),
                              ('Ivysaur','Overgrow'),('Venusaur','Overgrow'),('Charmander','Blaze')]:
            teams.save_member(self.team, self.member(name, ability))
        with self.assertRaisesRegex(ValueError, 'six'):
            teams.save_member(self.team, self.member('Charmeleon','Blaze'))
        with self.assertRaises(LookupError):
            teams.save_member(self.team, self.member(), 999)

    def test_api(self):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/teams', json={'team_name':'  '}).status_code, 422)
            result = client.post(f'/api/teams/{self.team}/pokemon', json=self.member())
            self.assertEqual(result.status_code, 201)
            self.assertEqual(client.get('/api/teams').json()[0]['pokemon'][0]['name'], 'Pikachu')
            self.assertEqual(client.get('/api/teams/catalog').status_code, 200)
            self.assertEqual(client.put('/api/teams/999', json={'team_name':'Missing'}).status_code, 404)
            self.assertEqual(client.post('/api/teams', headers={'Origin':'https://elsewhere.example'}, json={'team_name':'Bad'}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
