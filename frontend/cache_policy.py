"""Keep editable frontend files fresh without disabling artwork caching."""
from starlette.middleware.base import BaseHTTPMiddleware


class FrontendCachePolicy(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (path == '/' or path == '/api/teams/catalog'
                or (path.startswith('/public/') and path.endswith(('.html', '.js', '.css')))):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
