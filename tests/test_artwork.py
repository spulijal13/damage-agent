import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from damage_agent.artwork import artwork_path
from damage_agent.teams import catalog
from frontend.team_api import router


class ArtworkTests(unittest.TestCase):
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

    def test_number_fallback_prefers_standard_art(self):
        path = artwork_path({'name': 'Unmatched artwork name', 'num': 6})
        self.assertEqual(path.name, '0006 Charizard.png')
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
