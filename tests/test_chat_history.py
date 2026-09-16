import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from frontend import chat_api
from frontend.chat_api import router, workspace, register_chat_routes
from frontend.team_api import FrontendCachePolicy
from damage_agent.agent import next_state, CONTEXT_TURNS


class ChatHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'CHAT_DB_PATH': self.temp.name + '/chats.sqlite3'})
        self.env.start()
        self.addCleanup(self.env.stop)
        app = FastAPI()
        app.add_middleware(FrontendCachePolicy)
        app.include_router(router)
        app.include_router(workspace)
        self.client = TestClient(app)

    def test_public_crud_and_persistence(self):
        response = self.client.post('/api/chats')
        self.assertEqual(response.status_code, 201)
        chat = response.json()
        self.assertNotIn('conversation', chat)
        path = '/api/chats/' + chat['id']
        self.assertEqual(self.client.get(path).json()['messages'], [])
        self.assertEqual(self.client.put(path, json={'title': 'Rain team'}).status_code, 200)
        self.assertEqual(chat_api.get_chat(chat['id'])['title'], 'Rain team')
        self.assertIn('no-store', self.client.get('/api/chats').headers['cache-control'])
        # Another client without any credentials sees the same shared library.
        other = TestClient(self.client.app)
        self.assertEqual(other.get('/api/chats').json()[0]['title'], 'Rain team')
        self.assertEqual(other.delete(path).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_followup_after_reopen_and_separate_chat_context(self):
        first = self.client.post('/api/chats').json()
        second = self.client.post('/api/chats').json()
        seen = []
        def parse(question, client, conversation):
            seen.append(conversation)
            if question == 'What if it crits?':
                return {'mode': 'damage', 'field': {'critical': True}}
            return {'mode': 'damage', 'attacker': {'name': 'Sneasler'},
                    'defender': {'name': 'Primarina'}, 'move': 'Dire Claw'}
        with patch('damage_agent.agent.create_client', return_value=MagicMock()), \
             patch('damage_agent.agent.parse_damage_slots', side_effect=parse):
            path = f"/api/chats/{first['id']}/messages"
            answer = self.client.post(path, json={'content': 'Sneasler Dire Claw into Primarina', 'revision': 0})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertIn('HP damage', answer.json()['messages'][1]['content'])
            reopened = TestClient(self.client.app).get(f"/api/chats/{first['id']}").json()
            answer = self.client.post(path, json={'content': 'What if it crits?', 'revision': reopened['revision']})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertEqual(len(answer.json()['messages']), 4)
            self.assertEqual(seen[1]['slots']['defender']['name'], 'Primarina')
            self.assertTrue(chat_api.get_chat(first['id'])['conversation']['slots']['field']['critical'])
            self.client.post(f"/api/chats/{second['id']}/messages", json={'content': 'Fresh battle', 'revision': 0})
            self.assertEqual(seen[2]['slots'], {})

    def test_failure_and_conflict_preserve_saved_turn(self):
        chat = chat_api.create_chat()
        state = {'slots': {'move': 'Surf'}, 'history': []}
        saved = chat_api.save_turn(chat['id'], 0, 'Question', 'Answer', state)
        with self.assertRaises(chat_api.ChatConflict):
            chat_api.save_turn(chat['id'], 0, 'Stale', 'Wrong', {})
        self.assertEqual(chat_api.get_chat(chat['id']), saved)
        path = f"/api/chats/{chat['id']}/messages"
        with patch('frontend.chat_api.answer_question', side_effect=RuntimeError('Unknown move')) as calc:
            self.assertEqual(self.client.post(path, json={'content': 'stale', 'revision': 0}).status_code, 409)
            calc.assert_not_called()
            self.assertEqual(self.client.post(path, json={'content': 'bad', 'revision': 1}).status_code, 422)
        self.assertEqual(chat_api.get_chat(chat['id']), saved)
        chat_api.delete_chat(chat['id'])
        with self.assertRaises(LookupError):
            chat_api.save_turn(chat['id'], 1, 'Late', 'Response', {})
        with chat_api.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM chat_messages').fetchone()[0], 0)

    def test_database_keeps_full_history_beyond_model_context(self):
        chat = chat_api.create_chat()
        state = {}
        for i in range(CONTEXT_TURNS + 4):
            state = next_state(state, {'attacker': {'name': 'Sneasler'}}, f'Question {i}', f'Answer {i}')
            chat_api.save_turn(chat['id'], i, f'Question {i}', f'Answer {i}', state)
        reopened = chat_api.get_chat(chat['id'])
        self.assertEqual(len(reopened['messages']), 2 * (CONTEXT_TURNS + 4))
        self.assertEqual(len(reopened['conversation']['history']), 2 * CONTEXT_TURNS)
        self.assertEqual(reopened['conversation']['slots']['attacker']['name'], 'Sneasler')

    def test_validation_and_cross_origin_writes(self):
        chat = chat_api.create_chat()
        path = f"/api/chats/{chat['id']}"
        self.assertEqual(self.client.put(path, json={'title': ' '}).status_code, 422)
        self.assertEqual(self.client.post(path + '/messages', json={'content': ' ', 'revision': 0}).status_code, 422)
        self.assertEqual(self.client.delete(path, headers={'origin': 'https://other.example'}).status_code, 403)
        self.assertEqual(self.client.get(path).status_code, 200)

    def test_registration_preserves_mounts_and_precedes_spa(self):
        app = FastAPI()
        app.mount('/unrelated', FastAPI())
        @app.get('/{path:path}')
        def fallback(path):
            return {'fallback': True}
        with patch('chainlit.server.app', app):
            register_chat_routes()
            register_chat_routes()
        self.assertEqual(sum(getattr(r, 'path', '') == '/api/chats' for r in app.routes), 2)
        self.assertTrue(any(getattr(r, 'path', '') == '/unrelated' for r in app.routes))
        client = TestClient(app)
        self.assertIn('/public/navigation.js', client.get('/').text)
        self.assertEqual(client.get('/api/chats').json(), [])
