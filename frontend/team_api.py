"""Team endpoints registered ahead of Chainlit's SPA fallback."""
from urllib.parse import urlsplit

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from damage_agent import teams


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
    # Re-importing the Chainlit entry point during development must not duplicate routes.
    app.router.routes[:] = [route for route in app.router.routes
                            if not getattr(route, 'path', '').startswith('/api/teams')]
    app.router.routes[0:0] = router.routes
