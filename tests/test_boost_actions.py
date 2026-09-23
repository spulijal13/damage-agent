import copy
import os
import unittest
from unittest.mock import patch

from damage_agent.agent import (answer_question, apply_boost_actions, create_client,
                                merge_slots, parse_damage_slots, prepare_damage_request)


def battle_state():
    return {'slots': {'mode': 'damage', 'move': 'Scald',
        'attacker': {'name': 'Milotic', 'ability': 'Competitive', 'item': 'Leftovers',
                     'nature': 'Bold', 'spread': {'hp': 32, 'def': 26, 'spd': 8, 'spa': 0},
                     'boosts': {'spa': 2, 'atk': -1}},
        'defender': {'name': 'Incineroar', 'ability': 'Intimidate', 'nature': 'Careful',
                     'spread': {'hp': 32, 'spd': 20}, 'boosts': {'spe': 1}}}, 'history': []}


class BoostActionTests(unittest.TestCase):
    def test_reset_is_consumed_and_preserves_build_and_other_pokemon(self):
        previous = battle_state()['slots']
        original = copy.deepcopy(previous)
        for role in ('attacker', 'defender'):
            with self.subTest(role=role):
                action = {role: {'reset_boosts': True}}
                result = merge_slots(previous, action)
                expected = copy.deepcopy(previous)
                expected[role]['boosts'] = dict.fromkeys(('atk', 'def', 'spa', 'spd', 'spe'), 0)
                self.assertEqual(result, expected)
                self.assertEqual(previous, original)
                self.assertEqual(action, {role: {'reset_boosts': True}})
                self.assertNotIn('reset_boosts', result[role])

    def test_omitted_false_null_and_empty_preserve_stages(self):
        previous = battle_state()['slots']
        for action in ({}, {'reset_boosts': False}, {'reset_boosts': None},
                       {'boosts': None}, {'boosts': {}}):
            self.assertEqual(merge_slots(previous, {'attacker': action}), previous)

    def test_individual_zero_and_reset_then_set(self):
        previous = battle_state()['slots']
        result = merge_slots(previous, {'attacker': {'boosts': {'spa': 0}}})
        self.assertEqual(result['attacker']['boosts'], {'spa': 0, 'atk': -1})
        result = merge_slots(previous, {'attacker': {
            'reset_boosts': True, 'boosts': {'spe': 1, 'spa': None}}})
        self.assertEqual(result['attacker']['boosts'], {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 1})
        # The action cannot persist and erase a later explicit change.
        result = merge_slots(result, {'attacker': {'boosts': {'spa': 2}}})
        self.assertEqual(result['attacker']['boosts']['spa'], 2)

    def test_nested_bulk_actions(self):
        previous = {'mode': 'bulk', 'bulk': {'name': 'Milotic',
            'defender': {'boosts': {'def': 2}, 'spread': {'hp': 32}},
            'threats': [{'attacker': {'name': 'Incineroar', 'boosts': {'atk': 2}}, 'move': 'Flare Blitz'}]}}
        result = merge_slots(previous, {'bulk': {'defender': {'reset_boosts': True}}})
        self.assertTrue(all(v == 0 for v in result['bulk']['defender']['boosts'].values()))
        self.assertEqual(result['bulk']['defender']['spread'], {'hp': 32})
        self.assertEqual(result['bulk']['threats'], previous['bulk']['threats'])
        threats = copy.deepcopy(previous['bulk']['threats'])
        threats[0]['attacker'] = {'name': 'Incineroar', 'reset_boosts': True}
        result = merge_slots(previous, {'bulk': {'threats': threats}})
        self.assertEqual(result['bulk']['threats'][0]['attacker']['boosts']['atk'], 0)

    def test_single_request_reset_and_invalid_action(self):
        slots = battle_state()['slots']
        slots['attacker']['reset_boosts'] = True
        slots['attacker'].pop('boosts')
        battle = prepare_damage_request(slots, '')['battle']
        self.assertEqual(battle['attacker']['boosts']['spa'], 0)
        for invalid in ('true', 1, {}):
            with self.assertRaises(ValueError):
                apply_boost_actions({'attacker': {'reset_boosts': invalid}})

    def test_milotic_reset_recalculates_and_persists(self):
        state = battle_state()
        with patch('damage_agent.agent.create_client'), patch(
                'damage_agent.agent.parse_damage_slots', side_effect=[
                    {'mode': 'damage', 'attacker': {'reset_boosts': True}},
                    {'mode': 'damage', 'field': {'is_double_battle': False}}]):
            answer, cleared = answer_question('remove the boosts on Milotic', state)
            self.assertIn('78–92 HP damage', answer)
            self.assertNotIn('Boosts: +2 SpA', answer)
            _, followup = answer_question('now in singles', cleared)
        self.assertEqual(followup['slots']['attacker'], cleared['slots']['attacker'])
        self.assertEqual(state['slots']['attacker']['boosts']['spa'], 2)


@unittest.skipUnless(os.environ.get('DAMAGE_AGENT_LIVE_PARSER_TESTS') == '1',
                     'Opt-in Gemini evaluation; requires credentials and network')
class LiveBoostParsingTests(unittest.TestCase):
    def test_natural_language_removals(self):
        cases = [
            ('remove the boosts on the Milotic', 'attacker', None),
            ('what if there are no boosts on the milotic', 'attacker', None),
            ('remov teh boosts on miltoic', 'attacker', None),
            ('reset the defender stat stages', 'defender', None),
            ('remove only the special attack boost on Milotic', 'attacker', 'spa'),
        ]
        # Isolate model interpretation from the user's saved team library.
        with patch('damage_agent.team_context.saved_roster', return_value=[]), create_client() as client:
            for question, role, stat in cases:
                with self.subTest(question=question):
                    state = battle_state()
                    response = parse_damage_slots(question, client, state)
                    self.assertEqual(response['mode'], 'damage', response)
                    if stat is None:
                        self.assertTrue((response.get(role) or {}).get('reset_boosts'), response)
                    merged = merge_slots(state['slots'], response)
                    expected = copy.deepcopy(state['slots'])
                    if stat:
                        expected[role]['boosts'][stat] = 0
                    else:
                        expected[role]['boosts'] = dict.fromkeys(('atk', 'def', 'spa', 'spd', 'spe'), 0)
                    self.assertEqual(merged, expected)
