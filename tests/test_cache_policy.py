import unittest
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient
from frontend.cache_policy import FrontendCachePolicy


class CachePolicyTests(unittest.TestCase):
    def test_frontend_is_fresh_and_art_remains_cacheable(self):
        app = FastAPI()
        app.add_middleware(FrontendCachePolicy)

        @app.get('/{path:path}')
        def serve(path):
            return Response('content', headers={'Cache-Control': 'public, max-age=86400'})

        client = TestClient(app)
        for path in ['/', '/public/teams.html?v=20260914', '/public/teams.js',
                     '/public/teams.css', '/public/navigation.js', '/api/teams/catalog']:
            self.assertIn('no-store', client.get(path).headers['cache-control'])
        self.assertEqual(client.get('/api/teams/art/pikachu').headers['cache-control'], 'public, max-age=86400')
