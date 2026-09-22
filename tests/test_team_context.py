import unittest
from damage_agent.team_context import resolve_team_references
from damage_agent.agent import merge_slots, prepare_damage_request


class TeamContextTests(unittest.TestCase):
    def setUp(self):
        self.member = dict(team_member_id=7, name='Primarina', ability='Torrent',
                           item=None, nature='Bold', spread={'hp': 32, 'atk': 0, 'def': 12, 'spa': 0, 'spd': 0, 'spe': 0})

    def resolve(self, patch):
        return resolve_team_references(patch, [self.member])

    def test_saved_build_replaces_old_same_species_and_preserves_zero(self):
        old = {'defender': dict(name='Primarina', item='Life Orb', status='brn',
                               boosts={'def': 6}, spread={'spa': 32}),
               'attacker': {'name': 'Sneasler'}, 'move': 'Dire Claw'}
        patch = self.resolve({'mode': 'damage', 'defender': {'team_member_id': 7}})
        slots = merge_slots(old, patch)
        battle = prepare_damage_request(slots, '', conversational=True)['battle']
        self.assertIsNone(battle['defender']['item'])
        self.assertIsNone(battle['defender']['status'])
        self.assertEqual(battle['defender']['boosts']['def'], 0)
        self.assertEqual(battle['defender']['evs']['spa'], 0)
        self.assertEqual(battle['defender']['evs']['hp'], 32)
        self.assertEqual(battle['defender']['nature'], 'Bold')
        followup = merge_slots(slots, {'defender': {'spread': {'hp': 11}}})
        self.assertEqual(followup['defender']['spread']['def'], 12)
        self.assertEqual(self.member['spread']['hp'], 32)

    def test_explicit_override_and_missing_member(self):
        patch = self.resolve({'attacker': {'team_member_id': 7, 'nature': 'Modest', 'spread': {'spa': 20}}})
        self.assertEqual(patch['attacker']['nature'], 'Modest')
        self.assertEqual(patch['attacker']['spread']['spa'], 20)
        self.assertEqual(patch['attacker']['spread']['atk'], 0)
        with self.assertRaises(ValueError):
            self.resolve({'attacker': {'team_member_id': 999}})
        with self.assertRaises(ValueError):
            self.resolve({'attacker': {'team_member_id': 7, 'name': 'Pikachu'}})

    def test_bulk_can_reallocate_defenses_and_load_threat(self):
        patch = self.resolve({'mode': 'bulk', 'bulk': {
            'defender': {'team_member_id': 7, 'optimize_saved_defenses': True},
            'threats': [{'attacker': {'team_member_id': 7}, 'move': 'Moonblast'}]}})
        old = {'bulk': {'name': 'Primarina', 'nature': 'Serious',
                        'defender': {'spread': {'hp': 32}, 'item': 'Life Orb'}}}
        bulk = merge_slots(old, patch)['bulk']
        self.assertEqual(bulk['nature'], 'Bold')
        self.assertNotIn('hp', bulk['defender']['spread'])
        self.assertEqual(bulk['defender']['spread']['spa'], 0)
        self.assertIsNone(bulk['defender']['item'])
        self.assertEqual(bulk['threats'][0]['attacker']['nature'], 'Bold')
