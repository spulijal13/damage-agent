import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from damage_agent.artwork import ART_ROOT, artwork_path
from damage_agent.teams import catalog
from frontend.team_api import router


class ArtworkTests(unittest.TestCase):
    def test_shared_form_artwork(self):
        for number, names, filename in [
            (678, ['Meowstic-M-Mega', 'Meowstic-F-Mega'], '0678 Meowstic M Mega.png'),
            (801, ['Magearna-Mega', 'Magearna-Original-Mega'], '0801 Magearna Mega.png'),
            (801, ['Magearna', 'Magearna-Original'], '0801 Magearna.png'),
            (978, ['Tatsugiri-Curly-Mega', 'Tatsugiri-Droopy-Mega', 'Tatsugiri-Stretchy-Mega'], '0978 Tatsugiri Mega.png'),
            (978, ['Tatsugiri', 'Tatsugiri-Droopy', 'Tatsugiri-Stretchy'], '0978 Tatsugiri.png'),
        ]:
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(artwork_path({'name': name, 'num': number}).name, filename)

    def test_gender_can_fall_back_to_available_artwork(self):
        path = ART_ROOT / '0678 Meowstic.png'
        with patch('damage_agent.artwork.artwork_index', return_value={(678, 'meowstic'): path}):
            self.assertEqual(artwork_path({'name': 'Meowstic-F', 'num': 678}), path)

    def test_species_and_form_mapping(self):
        pokemon = {p['name']: p for p in catalog()['pokemon']}
        for name, filename in [
            ('Pikachu', '0025 Pikachu.png'),
            ('Charizard-Mega-Y', '0006 Charizard Mega Y.png'),
            ('Nidoran-F', '0029 Nidoran.png'),
            ('Nidoran-M', '0032 Nidoran.png'),
            ('Calyrex-Ice', '0898 Calyrex Ice Rider.png'),
            ('Basculegion-F', '0902 Basculegion Female.png'),
        ]:
            with self.subTest(name=name):
                self.assertEqual(artwork_path(pokemon[name]).name, filename)
                self.assertTrue(pokemon[name]['art_url'])

    def test_number_fallback_prefers_closest_name(self):
        base = ART_ROOT / '0006 Charizard.png'
        mega = ART_ROOT / 'Megas' / '0006 Charizard Mega.png'
        other = ART_ROOT / '0007 Charizard Mega Z.png'
        with patch('damage_agent.artwork.artwork_index', return_value={
            (6, 'charizard'): base, (6, 'charizardmega'): mega,
            (7, 'charizardmegaz'): other,
        }):
            self.assertEqual(artwork_path({'name': 'Charizard-Mega-Z', 'num': 6}), mega)
            self.assertEqual(artwork_path({'name': 'Charizard', 'num': 6}), base)
        self.assertIsNone(artwork_path({'name': 'Unknown', 'num': 99999}))

    def test_serves_png_and_rejects_unknown_id(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.get('/api/teams/art/pikachu')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(client.get('/api/teams/art/not-a-pokemon').status_code, 404)
