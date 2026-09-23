import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from damage_agent.agent import build_system_prompt, parse_damage_slots, prepare_damage_request
from damage_agent.parser_catalog import parser_catalog, parser_catalog_json, validate_parser_names
from damage_agent.showdown_bridge import run_showdown_calc


class ParserCatalogTests(unittest.TestCase):
    def test_names_match_both_calculator_datasets(self):
        source = json.loads(subprocess.run(['node', '-e', '''
            const {Generations}=require('@smogon/calc');
            console.log(JSON.stringify(Object.fromEntries(
              ['moves','items','abilities','natures'].map(k=>[k,
                [...new Set([0,9].flatMap(n=>[...Generations.get(n)[k]].map(x=>x.name)))].sort()
              ]))));
        '''], check=True, capture_output=True, text=True).stdout)
        catalog = parser_catalog()
        for key, names in source.items():
            self.assertEqual(set(catalog[key]), set(names) | ({'No Ability'} if key == 'abilities' else set()))
        self.assertIn('Accelerock', catalog['moves'])
        self.assertIn('Aura Guard', catalog['abilities'])
        self.assertIn(parser_catalog_json(), build_system_prompt())

    def test_parser_receives_catalog_and_canonical_result_reaches_calculator(self):
        client = MagicMock()
        client.models.generate_content.return_value.text = json.dumps({
            'mode': 'damage', 'attacker': {'name': 'Lycanroc-Dusk',
                'item': 'Life Orb', 'ability': 'Tough Claws', 'nature': 'Adamant'},
            'defender': {'name': 'Salamence-Mega'}, 'move': 'Accelerock',
            'field': {'weather': 'Sand'},
        })
        question = 'adamnt lycanroc dusk with life obr and tugh claws accelrock into mega salamence in snad'
        with patch('damage_agent.team_context.saved_roster', return_value=[]):
            # Both CLI and conversational callers use the same vocabulary.
            for conversation in (None, {'slots': {}, 'history': []}):
                request = parse_damage_slots(question, client, conversation)
                config = client.models.generate_content.call_args.kwargs['config']
                self.assertIn(parser_catalog_json(), config.system_instruction)
                self.assertEqual(client.models.generate_content.call_args.kwargs['contents'], question)
                battle = prepare_damage_request(request, question)['battle']
                self.assertEqual(battle['attacker']['evs']['atk'], 32)
                result = run_showdown_calc(battle)
                self.assertEqual(result['move'], 'Accelerock')
                self.assertGreater(result['max_damage'], 0)

    def test_invalid_model_names_are_rejected_in_nested_slots(self):
        for key in ('item', 'ability', 'nature', 'status'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                validate_parser_names({'bulk': {'defender': {key: 'Invented value'}}})
        for key in ('weather', 'terrain'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                validate_parser_names({'bulk': {'threats': [{'field': {key: 'Invented value'}}]}})
        with self.assertRaisesRegex(ValueError, 'move'):
            validate_parser_names({'bulk': {'threats': [{'move': 'Invented move'}]}})

    def test_unresolved_model_spelling_is_not_silently_accepted(self):
        client = MagicMock()
        client.models.generate_content.return_value.text = json.dumps({'mode': 'damage', 'move': 'Accelrock'})
        with patch('damage_agent.team_context.saved_roster', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'move'):
                parse_damage_slots('Use Accelrock', client)

    def test_clarifications_and_removals_preserve_valid_partial_slots(self):
        request = {'mode': 'clarify', 'message': 'Which move did you mean?',
                   'attacker': {'name': 'Lycanroc-Dusk', 'ability': 'No Ability',
                                'item': None, 'status': ''},
                   'move': None, 'field': {'weather': '', 'terrain': None},
                   'clear': ['defender.item']}
        self.assertEqual(validate_parser_names(request), request)
