"""Survival integration checks; run explicitly with unittest discovery."""
import unittest
from unittest.mock import patch

from damage_agent.agent import prepare_damage_request, merge_slots
from damage_agent.battle_builder import optimize_survival, format_survival_summary
from damage_agent.showdown_bridge import run_showdown_calc


class SurvivalTests(unittest.TestCase):
    def request(self, hits=1):
        return {'name': 'Blissey', 'survival': True,
                'threats': [{'attacker': {'name': 'Dragonite'},
                             'move': 'Dragon Rage'}], 'hits': hits}

    def test_bulk_routes_to_survival(self):
        with patch('damage_agent.agent.optimize_survival', return_value={'survival': True}) as optimize:
            bulk = self.request()
            result = prepare_damage_request({'mode': 'bulk', 'bulk': bulk}, '')
            self.assertEqual(result['mode'], 'bulk')
            optimize.assert_called_once_with(bulk)

    def test_old_stat_budget_does_not_limit_survival(self):
        bulk = self.request()
        bulk['total_points'] = 0
        with patch('damage_agent.showdown_bridge.run_calculator', return_value={}) as calc:
            optimize_survival(bulk)
            self.assertEqual(calc.call_args.args[0]['budget'], 66)

    def test_missing_threats_clarifies(self):
        bulk = self.request()
        bulk['threats'] = []
        result = prepare_damage_request({'mode': 'bulk', 'bulk': bulk}, '')
        self.assertEqual(result['mode'], 'clarify')
        self.assertIn('threat', result['message'])

    def test_followup_preserves_nested_defender_investments(self):
        old = {'mode': 'bulk', 'bulk': {**self.request(), 'defender': {
            'spread': {'spe': 12, 'hp': 4}, 'item': 'Leftovers'}}}
        new = merge_slots(old, {'mode': 'bulk', 'bulk': {
            'hits': 3, 'defender': {'spread': {'hp': 8, 'spe': None}}}})
        self.assertEqual(new['bulk']['defender']['spread'], {'spe': 12, 'hp': 8})
        self.assertEqual(new['bulk']['threats'], old['bulk']['threats'])
        self.assertEqual(old['bulk']['hits'], 1)

    def test_species_change_clears_fixed_defender(self):
        old = {'bulk': {**self.request(), 'defender': {'spread': {'hp': 32}}}}
        new = merge_slots(old, {'mode': 'bulk', 'bulk': {'name': 'Primarina'}})
        self.assertNotIn('defender', new['bulk'])

    def test_fixed_damage_one_two_three_uses(self):
        for hits in (1, 2, 3):
            with self.subTest(hits=hits):
                result = optimize_survival(self.request(hits))
                chosen = result['minimum']
                self.assertEqual(chosen['total'], 0)
                report = chosen['reports'][0]
                damage = run_showdown_calc(result['battles'][0])['max_damage']
                self.assertEqual(report['max_rolls'], [damage] * hits)
                self.assertEqual(report['remaining_hp'], report['starting_hp'] - hits * damage)
                self.assertIn('Fewest points', format_survival_summary(result))

    def test_exact_ko_is_not_survival(self):
        bulk = self.request()
        bulk.update(name='Magikarp', total_points=0, hits=1,
                    defender={'current_hp_percent': 53, 'spread': {'hp': 0, 'def': 0, 'spd': 0}})
        bulk['threats'][0]['move'] = 'Seismic Toss'
        result = optimize_survival(bulk)
        self.assertIsNone(result['minimum'])
        self.assertFalse(result['reference']['reports'][0]['survives'])

    def test_locked_spread_need_not_spend_entire_budget(self):
        bulk = self.request()
        bulk['defender'] = {'spread': {'hp': 0, 'def': 0, 'spd': 0}}
        result = optimize_survival(bulk)
        self.assertEqual(result['minimum']['total'], 0)

    def test_invalid_uses_rejected(self):
        with self.assertRaisesRegex(ValueError, '1, 2, or 3'):
            optimize_survival(self.request(0))

    def test_budget_heatmap_and_fixed_damage_probabilities(self):
        bulk = self.request()
        bulk.update(goal='budget', total_points=2)
        result = optimize_survival(bulk)
        self.assertEqual(result['full_budget']['total'], 2)
        self.assertEqual(len(result['cells']), 6)
        self.assertEqual(result['full_budget']['reports'][0]['ko'], [0, 0, 0])
        self.assertIn('```bulk-heatmap', format_survival_summary(result))
        self.assertNotIn('B=', format_survival_summary(result))

    def test_general_budget_supports_nature_without_threats(self):
        result = optimize_survival({'name': 'Sylveon', 'goal': 'budget',
                                   'total_points': 4, 'nature': 'Bold'})
        self.assertEqual(result['full_budget']['total'], 4)
        self.assertEqual(result['full_budget']['reports'], [])

    def test_calculator_style_damage_rolls_and_champions_units(self):
        result = optimize_survival({
            'name': 'Lycanroc-Dusk',
            'defender': {'spread': {'hp': 0, 'def': 0, 'spd': 0}},
            'threats': [{'attacker': {'name': 'Charizard-Mega-Y', 'nature': 'Modest',
                                     'spread': {'spa': 11}}, 'move': 'Solar Beam'}],
        })
        report = result['fallback']['reports'][0]
        expected = [222, 224, 226, 230, 232, 234, 238, 240,
                    242, 246, 248, 250, 254, 256, 258, 262]
        self.assertEqual(report['damage_rolls'], expected)
        summary = format_survival_summary(result)
        self.assertIn('11+ SpA Charizard-Mega-Y Solar Beam vs. 0 HP / 0 SpD '
                      'Lycanroc-Dusk: 222-262 (148 - 174.6%) -- guaranteed OHKO', summary)
        self.assertIn('Possible damage amounts: (' + ', '.join(map(str, expected)) + ')', summary)
        self.assertIn('Possible damage percentages: (148%, 149.3%', summary)

    def test_damage_percent_uses_max_hp_while_ko_uses_starting_hp(self):
        result = optimize_survival({
            'name': 'Magikarp',
            'defender': {'current_hp_percent': 53, 'spread': {'hp': 0, 'def': 0, 'spd': 0}},
            'threats': [{'attacker': {'name': 'Dragonite'}, 'move': 'Seismic Toss'}],
        })
        summary = format_survival_summary(result)
        self.assertIn('guaranteed OHKO from 50/95 starting HP', summary)
        self.assertIn('Possible damage amounts: (50)', summary)
        self.assertIn('Possible damage percentages: (52.6%)', summary)

    def test_nature_changes_defense_and_damage(self):
        bulk = {'name': 'Primarina', 'defender': {'spread': {'hp': 0, 'def': 0, 'spd': 0}},
                'threats': [{'attacker': {'name': 'Sneasler'}, 'move': 'Dire Claw'}]}
        neutral = optimize_survival(bulk)
        bold = optimize_survival({**bulk, 'nature': 'Bold'})
        neutral_spread = neutral['minimum'] or neutral['reference']
        bold_spread = bold['minimum'] or bold['reference']
        self.assertGreater(bold_spread['stats']['def'], neutral_spread['stats']['def'])
        self.assertLess(bold_spread['reports'][0]['max_damage'], neutral_spread['reports'][0]['max_damage'])


if __name__ == '__main__':
    unittest.main()
