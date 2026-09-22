import copy
import unittest
from unittest.mock import MagicMock, patch

from damage_agent.agent import (
    CONTEXT_TURNS, CONTEXT_MESSAGE_CHARS, prepare_damage_request,
    merge_slots, next_state, answer_question,
)


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.slots = {'mode': 'damage', 'attacker': {'name': 'Sneasler', 'spread': {'atk': 32}},
                      'defender': {'name': 'Primarina', 'item': 'Leftovers', 'spread': {'hp': 32}},
                      'move': 'Dire Claw', 'field': {'is_double_battle': False}}

    def test_followup_preserves_singles_and_points(self):
        updated = merge_slots(self.slots, {'field': {'critical': True}, 'defender': {'item': None}})
        battle = prepare_damage_request(updated, 'What if it crits?', conversational=True)['battle']
        self.assertFalse(battle['field']['is_double_battle'])
        self.assertTrue(battle['field']['critical'])
        self.assertEqual(battle['defender']['item'], 'Leftovers')
        self.assertEqual(battle['attacker']['evs']['atk'], 32)
        self.assertNotIn('critical', self.slots['field'])

    def test_move_changes_recompute_only_implicit_offensive_defaults(self):
        slots = {'mode': 'damage', 'attacker': {'name': 'Lucario'}, 'defender': {'name': 'Primarina'}, 'move': 'Close Combat'}
        physical = prepare_damage_request(slots, '', conversational=True)['battle']
        self.assertEqual(physical['attacker']['evs']['atk'], 32)
        updated = merge_slots(slots, {'move': 'Aura Sphere', 'mode': 'damage'})
        special = prepare_damage_request(updated, '', conversational=True)['battle']
        self.assertEqual(special['attacker']['evs']['spa'], 32)
        self.assertEqual(special['attacker']['evs']['atk'], 0)
        uninvested = merge_slots(updated, {'attacker': {'spread': {'spa': 0}, 'nature': 'Timid'}})
        followup = merge_slots(uninvested, {'field': {'critical': True}})
        battle = prepare_damage_request(followup, '', conversational=True)['battle']
        self.assertEqual(battle['attacker']['evs']['spa'], 0)
        self.assertEqual(battle['attacker']['nature'], 'Timid')

    def test_explicit_removal_and_false(self):
        updated = merge_slots(self.slots, {'clear': ['defender.item', 'attacker.spread.atk', 'field.weather'],
                                          'field': {'critical': False, 'reflect': True}})
        self.assertIsNone(updated['defender']['item'])
        self.assertEqual(updated['attacker']['spread']['atk'], 0)
        self.assertEqual(updated['field']['weather'], '')
        updated['attacker'] = {'name': 'Charizard-Mega-Y'}
        battle = prepare_damage_request(updated, 'no weather', conversational=True)['battle']
        self.assertEqual(battle['field']['weather'], '')  # Drought must not restore cleared sun.

    def test_species_replacement_and_new_battle(self):
        changed = merge_slots(self.slots, {'defender': {'name': 'Charizard'}})
        self.assertEqual(changed['defender'], {'name': 'Charizard'})
        fresh = merge_slots(self.slots, {'new_battle': True, 'attacker': {'name': 'Pikachu'}})
        self.assertNotIn('defender', fresh)
        self.assertNotIn('field', fresh)

    def test_partial_clarification_and_isolation(self):
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('damage_agent.agent.parse_damage_slots', side_effect=[
                 {'mode': 'clarify', 'attacker': {'name': 'Sneasler'}, 'move': 'Dire Claw', 'message': 'Who defends?'},
                 {'mode': 'damage', 'defender': {'name': 'Primarina'}}]):
            _, first = answer_question('Sneasler Dire Claw')
            original = copy.deepcopy(first)
            answer, second = answer_question('Primarina', first)
        self.assertIn('HP damage', answer)
        self.assertEqual(second['slots']['attacker']['name'], 'Sneasler')
        self.assertEqual(first, original)
        self.assertNotIn('defender', first['slots'])

    def test_failed_calculation_keeps_previous_state(self):
        state = {'slots': self.slots, 'history': []}
        original = copy.deepcopy(state)
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('damage_agent.agent.parse_damage_slots', return_value={'mode': 'damage', 'move': 'Not a move'}):
            with self.assertRaises(RuntimeError):
                answer_question('Bad move', state)
        self.assertEqual(state, original)

    def test_bounded_history(self):
        state = {}
        for i in range(20):
            state = next_state(state, self.slots, str(i), 'reply')
        self.assertEqual(len(state['history']), 12)
        self.assertEqual(state['history'][0]['content'], '14')
        self.assertEqual(state['slots'], self.slots)

    def test_context_caps_each_message_without_losing_battle(self):
        long_message = 'x' * (CONTEXT_MESSAGE_CHARS + 50)
        state = {}
        for _ in range(CONTEXT_TURNS + 2):
            state = next_state(state, self.slots, long_message, long_message)
        self.assertEqual(len(state['history']), 2 * CONTEXT_TURNS)
        self.assertTrue(all(len(m['content']) == CONTEXT_MESSAGE_CHARS for m in state['history']))
        self.assertEqual(state['slots']['defender']['item'], 'Leftovers')

    def test_explicit_new_battle_clears_old_history(self):
        state = {'slots': self.slots, 'history': [{'role': 'user', 'content': 'Previous battle'}]}
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('damage_agent.agent.parse_damage_slots', return_value={
                 'mode': 'clarify', 'new_battle': True, 'message': 'What is the new battle?'}):
            _, fresh = answer_question('Start a new battle', state)
        self.assertNotIn('attacker', fresh['slots'])
        self.assertEqual(len(fresh['history']), 2)
