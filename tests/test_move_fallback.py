import unittest
from damage_agent.teams import catalog, validate_member


class MoveFallbackTests(unittest.TestCase):
    def test_missing_learnset_allows_catalog_moves(self):
        choices = catalog()
        pokemon = next(p for p in choices['pokemon'] if not p['has_champions_learnset'])
        self.assertEqual(pokemon['moves'], choices['moves'])
        validate_member({'name': pokemon['name'], 'ability': pokemon['abilities'][0], 'move_1':'Surf'})

    def test_known_learnset_stays_restricted(self):
        pokemon = next(p for p in catalog()['pokemon'] if p['name']=='Charizard')
        self.assertTrue(pokemon['has_champions_learnset'])
        self.assertNotIn('Surf', pokemon['moves'])
        with self.assertRaises(ValueError):
            validate_member({'name':'Charizard', 'ability':'Blaze', 'move_1':'Surf'})
