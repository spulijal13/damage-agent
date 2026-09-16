import io
import math
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from damage_agent.agent import answer_question, prepare_damage_request, merge_slots, run_agent
from damage_agent.battle_builder import optimize_bulk, format_bulk_summary


class BulkTests(unittest.TestCase):
    def test_reference_example_and_breakpoints(self):
        result = optimize_bulk('Volcarona', 11, 1, True, stats_override={'hp': 85, 'def': 75, 'spd': 105})
        self.assertEqual(result['best'], [{'points': [10, 1, 0], 'stats': [170, 96, 125]}])
        self.assertEqual(len(result['ranges']), 23)
        row = next(r for r in result['ranges'] if r['points'] == [10, 1, 0])
        self.assertEqual(row['low'], .9728)
        self.assertAlmostEqual(row['high'], 1.0204931506849315)
        self.assertAlmostEqual(result['ranges'][0]['high'], .1294, places=4)
        self.assertAlmostEqual(result['ranges'][-1]['low'], 1.6189, places=4)
        text = format_bulk_summary(result)
        self.assertIn('HP 10 / Def 1 / SpD 0', text)
        self.assertIn('explicit overrides', text)
        self.assertIn('[0.9728, 1.0205]', text)

    def test_catalog_stats_are_not_silently_replaced_by_reference(self):
        result = optimize_bulk('Volcarona', 11)
        self.assertEqual(result['base_stats']['def'], 65)
        self.assertEqual(result['best'][0]['points'], [3, 8, 0])
        self.assertFalse(result['custom_base_stats'])

    def test_optimum_matches_independent_exhaustive_search(self):
        for budget in (0, 11, 33, 66):
            for bias in (0, .1, 1, 2, 100):
                result = optimize_bulk('Volcarona', budget, bias)
                base = result['base_stats']
                expected = min((bias / (base['def'] + 20 + y) + 1 / (base['spd'] + 20 + z)) /
                               (base['hp'] + 75 + x)
                               for x in range(33) for y in range(33) for z in [budget-x-y] if 0 <= z <= 32)
                self.assertAlmostEqual(result['score'], expected, places=15)
                for spread in result['best']:
                    self.assertEqual(sum(spread['points']), budget)
                    self.assertTrue(all(0 <= p <= 32 for p in spread['points']))

    def test_every_reported_interval_is_optimal_at_its_midpoint(self):
        for name, budget in [('Volcarona', 11), ('Blissey', 66), ('Mew', 32), ('Mew', 0)]:
            result = optimize_bulk(name, budget, show_ranges=True)
            self.assertEqual(result['ranges'][0]['low'], 0)
            self.assertIsNone(result['ranges'][-1]['high'])
            for row in result['ranges']:
                low, high = row['low'], row['high']
                bias = (low + high) / 2 if high is not None else low + 10
                hp, defense, spd = row['stats']
                expected = optimize_bulk(name, budget, bias)['score']
                self.assertAlmostEqual((bias / defense + 1 / spd) / hp, expected, places=15)

    def test_invalid_inputs_and_non_neutral_nature(self):
        for budget in (-1, 67, 1.5, True):
            with self.assertRaises(ValueError): optimize_bulk('Volcarona', budget)
        for bias in (-1, math.inf, math.nan, True, 'physical'):
            with self.assertRaises(ValueError): optimize_bulk('Volcarona', 11, bias)
        for name in ('Fake Pokemon', 'Shedinja'):
            with self.assertRaises(ValueError): optimize_bulk(name, 11)
        with self.assertRaises(ValueError): optimize_bulk('Volcarona', 11, nature='Bold')
        with self.assertRaises(ValueError): optimize_bulk('Volcarona', 11, stats_override={'def': 0})

    def test_missing_budget_clarifies_but_zero_is_valid(self):
        request = {'mode': 'bulk', 'bulk': {'name': 'Volcarona'}}
        self.assertEqual(prepare_damage_request(request, '')['mode'], 'clarify')
        request['bulk']['total_points'] = 0
        self.assertEqual(prepare_damage_request(request, '')['result']['best'][0]['points'], [0, 0, 0])

    def test_bulk_followups_and_mode_switch(self):
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('damage_agent.agent.parse_damage_slots', side_effect=[
                 {'mode': 'bulk', 'bulk': {'name': 'Volcarona', 'total_points': 11, 'base_stats': {'def': 75}}},
                 {'mode': 'bulk', 'bulk': {'bias': 0, 'show_ranges': True}},
                 {'mode': 'damage', 'attacker': {'name': 'Sneasler'}, 'defender': {'name': 'Primarina'}, 'move': 'Dire Claw'}]):
            answer, first = answer_question('Optimize Volcarona T=11 base Def=75')
            self.assertIn('HP 10 / Def 1 / SpD 0', answer)
            answer, second = answer_question('B=0 and show ranges', first)
            self.assertIn('HP 0 / Def 0 / SpD 11', answer)
            self.assertIn('| B range |', answer)
            self.assertEqual(second['slots']['bulk']['total_points'], 11)
            self.assertNotIn('bias', first['slots']['bulk'])
            answer, third = answer_question('Sneasler Dire Claw into Primarina', second)
            self.assertIn('HP damage', answer)
            self.assertEqual(third['slots']['mode'], 'damage')
        changed = merge_slots(first['slots'], {'mode': 'bulk', 'bulk': {'name': 'Mew'}})
        self.assertNotIn('base_stats', changed['bulk'])
        self.assertEqual(changed['bulk']['total_points'], 11)

    def test_cli_bulk_route(self):
        output = io.StringIO()
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('builtins.input', side_effect=['Optimize Volcarona T=11', 'quit']), \
             patch('damage_agent.agent.parse_damage_slots', return_value={
                 'mode': 'bulk', 'bulk': {'name': 'Volcarona', 'total_points': 11}}), redirect_stdout(output):
            run_agent()
        self.assertIn('weighted bulk', output.getvalue())
