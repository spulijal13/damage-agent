import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from damage_agent.teams import catalog
from frontend.team_api import router


class MoveDetailsTests(unittest.TestCase):
    def test_details_include_all_display_fields(self):
        moves = catalog()['move_details']
        move = moves['aquajet']
        self.assertEqual([move[k] for k in ['pp', 'type', 'basePower', 'accuracy', 'category', 'priority']],
                         [20, 'Water', 40, 100, 'Physical', 1])
        self.assertTrue(move['desc'])
        self.assertIs(moves['aerialace']['accuracy'], True)
        self.assertEqual(moves['protect']['basePower'], 0)

    def test_icons_serve_images_and_reject_unknown_types(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        for element in ['Water', 'Fire', 'Electric']:
            response = client.get('/api/teams/type-icons/' + element)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(client.get('/api/teams/type-icons/unknown').status_code, 404)
