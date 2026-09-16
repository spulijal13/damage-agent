"""Team endpoints registered ahead of Chainlit's SPA fallback."""
from urllib.parse import urlsplit

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from damage_agent.artwork import artwork_path
from damage_agent import teams


class FrontendCachePolicy(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (path == '/' or path == '/api/teams/catalog' or path.startswith('/api/chats')
                or (path.startswith('/public/') and path.endswith(('.html', '.js', '.css')))):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response


def same_origin(request: Request):
    if request.method in ('POST', 'PUT', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.headers.get('host'):
            raise HTTPException(403, 'Cross-origin writes are not allowed.')


router = APIRouter(prefix='/api/teams', dependencies=[Depends(same_origin)])


def call(fn, *args):
    try:
        return fn(*args)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get('/type-icons/{type_name}')
def get_type_icon(type_name: str):
    allowed = {'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting',
               'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost',
               'Dragon', 'Dark', 'Steel', 'Fairy', 'Stellar'}
    if type_name not in allowed:
        raise HTTPException(404, 'Type icon not found.')
    path = teams.ROOT / 'images/type_icons' / f'{type_name}_icon_SV.png'
    if not path.is_file():
        raise HTTPException(404, 'Type icon not found.')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'public, max-age=86400'})


@router.get('/art/{pokemon_id}')
def get_art(pokemon_id: str):
    pokemon = next((p for p in teams.catalog()['pokemon'] if p['id'] == pokemon_id), None)
    path = artwork_path(pokemon) if pokemon else None
    if not path or not path.is_file():
        raise HTTPException(404, 'Artwork not found.')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'public, max-age=86400'})


@router.get('/catalog')
def get_catalog():
    return teams.catalog()


@router.get('')
def get_teams():
    return teams.list_teams()


@router.post('', status_code=201)
def create_team(data: dict = Body(...)):
    return {'team_id': call(teams.create_team, data.get('team_name'))}


@router.put('/{team_id}')
def rename_team(team_id: int, data: dict = Body(...)):
    call(teams.rename_team, team_id, data.get('team_name'))
    return {'ok': True}


@router.delete('/{team_id}')
def delete_team(team_id: int):
    call(teams.delete_team, team_id)
    return {'ok': True}


@router.post('/{team_id}/pokemon', status_code=201)
def add_pokemon(team_id: int, data: dict = Body(...)):
    return {'pokemon_id': call(teams.save_member, team_id, data)}


@router.put('/{team_id}/pokemon/{pokemon_id}')
def update_pokemon(team_id: int, pokemon_id: int, data: dict = Body(...)):
    return {'pokemon_id': call(teams.save_member, team_id, data, pokemon_id)}


@router.delete('/{team_id}/pokemon/{pokemon_id}')
def delete_pokemon(team_id: int, pokemon_id: int):
    call(teams.delete_member, team_id, pokemon_id)
    return {'ok': True}


def register_routes():
    from chainlit.server import app
    if not getattr(app.state, 'frontend_cache_policy_installed', False):
        app.add_middleware(FrontendCachePolicy)
        app.state.frontend_cache_policy_installed = True
    # Re-importing the Chainlit entry point during development must not duplicate routes.
    app.router.routes[:] = [route for route in app.router.routes
                            if not getattr(route, 'path', '').startswith('/api/teams')]
    app.router.routes[0:0] = router.routes
