"""Shared chat endpoints, available without login just like the team library."""
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from damage_agent.agent import answer_question, CONTEXT_MESSAGE_CHARS
from frontend.team_api import same_origin

ROOT = Path(__file__).resolve().parents[1]


class ChatConflict(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    path = Path(os.environ.get('CHAT_DB_PATH', ROOT / 'storage/chats.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
            conversation TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY, chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS chat_messages_chat ON chat_messages(chat_id, id);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def title(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        raise ValueError('Chat name must contain 1–100 characters.')
    return value.strip()


def require_chat(db, chat_id):
    row = db.execute('SELECT * FROM chats WHERE id=?', (chat_id,)).fetchone()
    if row is None:
        raise LookupError('Chat not found.')
    return row


def list_chats():
    with connection() as db:
        return [dict(row) for row in db.execute(
            'SELECT id, title, created_at, updated_at FROM chats ORDER BY updated_at DESC, id')]


def create_chat(name='New chat'):
    chat_id, timestamp = str(uuid4()), now()
    with connection() as db:
        db.execute('INSERT INTO chats(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                   (chat_id, title(name), timestamp, timestamp))
    return get_chat(chat_id)


def get_chat(chat_id):
    with connection() as db:
        chat = dict(require_chat(db, chat_id))
        chat['conversation'] = json.loads(chat['conversation'])
        chat['messages'] = [dict(row) for row in db.execute(
            'SELECT id, role, content, created_at FROM chat_messages WHERE chat_id=? ORDER BY id', (chat_id,))]
    return chat


def rename_chat(chat_id, name):
    with connection() as db:
        require_chat(db, chat_id)
        db.execute('UPDATE chats SET title=?, updated_at=? WHERE id=?', (title(name), now(), chat_id))


def delete_chat(chat_id):
    with connection() as db:
        require_chat(db, chat_id)
        db.execute('DELETE FROM chats WHERE id=?', (chat_id,))


def save_turn(chat_id, revision, question, answer, state):
    """Commit both messages and context together; never overwrite a concurrent turn."""
    timestamp = now()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        chat = require_chat(db, chat_id)
        if chat['revision'] != revision:
            raise ChatConflict('This chat changed while calculating. Review its latest messages and send again.')
        name = question[:100] if revision == 0 and chat['title'] == 'New chat' else chat['title']
        db.execute('UPDATE chats SET title=?, updated_at=?, revision=revision+1, conversation=? WHERE id=?',
                   (name, timestamp, json.dumps(state), chat_id))
        db.executemany('INSERT INTO chat_messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)',
                       [(chat_id, 'user', question, timestamp), (chat_id, 'assistant', answer, timestamp)])
    return get_chat(chat_id)


# Public HTTP routes.
logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/chats', dependencies=[Depends(same_origin)])
workspace = APIRouter()


@workspace.get('/')
def workspace_page():
    return FileResponse(ROOT / 'public/workspace.html', headers={'Cache-Control': 'no-store'})


def call(function, *args):
    try:
        return function(*args)
    except ChatConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


def public_chat(chat):
    return {key: value for key, value in chat.items() if key != 'conversation'}


@router.get('')
def api_list_chats():
    return list_chats()


@router.post('', status_code=201)
def api_create_chat():
    return public_chat(create_chat())


@router.get('/{chat_id}')
def api_get_chat(chat_id: str):
    return public_chat(call(get_chat, chat_id))


@router.put('/{chat_id}')
def api_rename_chat(chat_id: str, data: dict = Body(...)):
    call(rename_chat, chat_id, data.get('title'))
    return {'ok': True}


@router.delete('/{chat_id}')
def api_delete_chat(chat_id: str):
    call(delete_chat, chat_id)
    return {'ok': True}


@router.post('/{chat_id}/messages')
def send_message(chat_id: str, data: dict = Body(...)):
    question = data.get('content')
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= CONTEXT_MESSAGE_CHARS:
        raise HTTPException(422, f'Write a message between 1 and {CONTEXT_MESSAGE_CHARS:,} characters.')
    question = question.strip()
    chat = call(get_chat, chat_id)
    if type(data.get('revision')) is not int or data['revision'] != chat['revision']:
        raise HTTPException(409, 'This chat changed. Review its latest messages and send again.')
    try:
        answer, state = answer_question(question, chat['conversation'])
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception('Chat calculation failed')
        raise HTTPException(502, 'The calculation could not complete. Please try again.') from exc
    return public_chat(call(save_turn, chat_id, chat['revision'], question, answer, state))


def register_chat_routes():
    from chainlit.server import app
    app.router.routes[:] = [route for route in app.router.routes
                            if not getattr(route, 'path', '').startswith('/api/chats')
                            and getattr(getattr(route, 'endpoint', None), '__name__', '') != 'workspace_page']
    app.router.routes[0:0] = [*workspace.routes, *router.routes]
