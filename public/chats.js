'use strict';
const $ = id => document.getElementById(id);
let chats = [], current = null, selected = null, selectionVersion = 0, creating = false;
const drafts = new Map(), pending = new Map(), errors = new Map();
let renameTarget = null, deleteTarget = null;

async function api(path = '', method = 'GET', body) {
  const response = await fetch(`/api/chats${path}`, {
    method, headers: {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Unable to complete the request.');
    error.status = response.status;
    throw error;
  }
  return data;
}
function remember(id) {
  try { if (id) localStorage.setItem('damage-active-chat', id); else localStorage.removeItem('damage-active-chat'); } catch (_) {}
}
function renderList() {
  const query = $('search').value.trim().toLowerCase();
  $('chat-list').replaceChildren();
  for (const chat of chats.filter(c => c.title.toLowerCase().includes(query))) {
    const row = document.createElement('div'); row.className = 'chat-row';
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'chat-entry';
    button.setAttribute('aria-current', String(chat.id === selected));
    const label = document.createElement('span'); label.textContent = chat.title;
    const detail = document.createElement('small');
    detail.textContent = pending.has(chat.id) ? 'Calculating…' : new Date(chat.updated_at).toLocaleString([], {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
    button.append(label, detail);
    button.onclick = () => selectChat(chat.id);
    const actions = document.createElement('details'); actions.className = 'chat-actions';
    const toggle = document.createElement('summary'); toggle.textContent = '☰';
    toggle.setAttribute('aria-label', `Actions for ${chat.title}`);
    toggle.title = 'Chat actions';
    const choices = document.createElement('div'); choices.className = 'chat-action-buttons';
    const rename = document.createElement('button'); rename.type = 'button'; rename.textContent = 'Rename';
    rename.onclick = () => { actions.open = false; openRename(chat); };
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Delete';
    remove.className = 'danger'; remove.disabled = pending.has(chat.id);
    remove.onclick = () => { actions.open = false; openDelete(chat); };
    choices.append(rename, remove); actions.append(toggle, choices);
    actions.addEventListener('toggle', () => {
      if (actions.open) document.querySelectorAll('.chat-actions[open]').forEach(other => {
        if (other !== actions) other.open = false;
      });
    });
    row.append(button, actions); $('chat-list').append(row);
  }
  if (!$('chat-list').children.length) {
    const empty = document.createElement('p'); empty.className = 'muted';
    empty.textContent = query ? 'No matching chats.' : 'Your conversations will appear here.';
    $('chat-list').append(empty);
  }
}
async function refreshList() { chats = await api(); renderList(); }
function appendInline(container, content) {
  content.split(/\*\*([^*]+)\*\*/g).forEach((text, i) => {
    if (i % 2) { const strong = document.createElement('strong'); strong.textContent = text; container.append(strong); }
    else container.append(document.createTextNode(text));
  });
}
function appendAnswer(container, content) {
  const lines = content.split('\n');
  const cells = line => line.trim().slice(1, -1).split('|').map(cell => cell.trim());
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('| ') && /^\|(?:\s*:?-{3,}:?\s*\|)+\s*$/.test(lines[i + 1] || '')) {
      const wrapper = document.createElement('div'); wrapper.className = 'message-table'; wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region'); wrapper.setAttribute('aria-label', 'Bulk optimization ranges');
      const table = document.createElement('table');
      const head = document.createElement('thead'), row = document.createElement('tr');
      cells(lines[i]).forEach(value => { const cell = document.createElement('th'); cell.scope = 'col'; cell.textContent = value; row.append(cell); });
      head.append(row); table.append(head);
      const body = document.createElement('tbody'); i += 2;
      while (i < lines.length && lines[i].startsWith('| ') && lines[i].trim().endsWith('|')) {
        const row = document.createElement('tr');
        cells(lines[i]).forEach(value => { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); });
        body.append(row); i++;
      }
      i--; table.append(body); wrapper.append(table); container.append(wrapper);
    } else appendInline(container, lines[i] + (i < lines.length - 1 ? '\n' : ''));
  }
}
function message(role, content, waiting = false) {
  const article = document.createElement('article');
  article.className = `message ${role}${waiting ? ' pending' : ''}`;
  const label = document.createElement('div'); label.className = 'message-label';
  label.textContent = role === 'user' ? 'You' : 'Damage Agent';
  const body = document.createElement('div'); body.className = 'message-content';
  // Text, emphasis and tables only; model/user content never becomes executable HTML.
  if (role === 'assistant') appendAnswer(body, content);
  else body.textContent = content;
  article.append(label, body); $('messages').append(article);
}
function render() {
  $('chat-title').textContent = current?.title || (selected ? 'Loading chat…' : 'New chat');
  $('question').disabled = creating || (selected !== null && !current);
  $('send').disabled = creating || (selected !== null && !current) || pending.has(selected);
  $('send').textContent = pending.has(selected) ? 'Working…' : 'Send ↑';
  $('notice').textContent = errors.get(selected) || '';
  $('messages').replaceChildren();
  for (const item of current?.messages || []) message(item.role, item.content);
  if (pending.has(selected)) {
    message('user', pending.get(selected));
    message('assistant', 'Calculating…', true);
  } else if ((!current && !selected) || (current && !current.messages.length)) {
    const welcome = document.createElement('div'); welcome.className = 'welcome';
    const heading = document.createElement('h2'); heading.textContent = 'What battle are we calculating?';
    const description = document.createElement('p');
    description.textContent = 'Start with an attacker, defender, and move. Then ask follow-ups—each chat remembers its own battle.';
    const example = document.createElement('button'); example.type = 'button';
    example.textContent = 'Sneasler with max attack using Dire Claw into Primarina with max HP';
    example.onclick = () => { $('question').value = example.textContent; drafts.set(selected, example.textContent); $('question').focus(); };
    welcome.append(heading, description, example); $('messages').append(welcome);
  }
  renderList();
  $('messages').scrollTop = $('messages').scrollHeight;
}
function closeSidebar() {
  document.body.classList.remove('show-chats'); $('toggle-chats').setAttribute('aria-expanded', 'false');
}
async function selectChat(id) {
  drafts.set(selected, $('question').value);
  selected = id; current = null; remember(id);
  const version = ++selectionVersion;
  $('question').value = drafts.get(id) || '';
  closeSidebar(); render();
  if (!id) return;
  try {
    const chat = await api(`/${id}`);
    if (version !== selectionVersion) return;
    current = chat; render();
  } catch (error) {
    if (version !== selectionVersion) return;
    errors.set(id, error.message); render();
    if (error.status === 404) {
      await refreshList();
      if (version === selectionVersion) await selectChat(null);
    }
  }
}
$('new-chat').onclick = async () => {
  if (creating) return;
  creating = true; $('new-chat').disabled = true;
  try {
    const chat = await api('', 'POST');
    await refreshList(); await selectChat(chat.id);
    $('question').focus();
  } catch (error) { errors.set(selected, error.message); }
  finally { creating = false; $('new-chat').disabled = false; render(); }
};
$('composer').onsubmit = async event => {
  event.preventDefault();
  const question = $('question').value.trim();
  if (!question || pending.has(selected) || creating || (selected && !current)) return;
  if (!current) {
    creating = true; $('new-chat').disabled = true; render();
    try {
      const chat = await api('', 'POST');
      selected = chat.id; current = chat; ++selectionVersion; remember(selected);
      drafts.delete(null);
    } catch (error) { errors.set(selected, error.message); creating = false; $('new-chat').disabled = false; render(); return; }
    creating = false; $('new-chat').disabled = false;
  }
  const id = selected, revision = current.revision;
  drafts.set(id, ''); $('question').value = ''; errors.delete(id); pending.set(id, question); render();
  try {
    const chat = await api(`/${id}/messages`, 'POST', {content: question, revision});
    if (selected === id) current = chat;
  } catch (error) {
    errors.set(id, error.message);
    if (!drafts.get(id)) drafts.set(id, question);
    if (selected === id) $('question').value = drafts.get(id);
    if (error.status === 409) {
      try { const latest = await api(`/${id}`); if (selected === id) current = latest; } catch (_) {}
    }
  } finally {
    pending.delete(id);
    try { await refreshList(); } catch (error) { errors.set(selected, error.message); }
    render();
  }
};
$('question').oninput = () => drafts.set(selected, $('question').value);
$('question').onkeydown = event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('composer').requestSubmit(); }
};
$('search').oninput = renderList;
$('toggle-chats').onclick = () => {
  const open = document.body.classList.toggle('show-chats'); $('toggle-chats').setAttribute('aria-expanded', String(open));
};
function openRename(chat) {
  renameTarget = chat.id; $('rename-input').value = chat.title; $('rename-error').textContent = '';
  $('rename-dialog').showModal(); $('rename-input').select();
}
$('cancel-rename').onclick = () => $('rename-dialog').close();
$('rename-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  try {
    const title = $('rename-input').value.trim();
    await api(`/${renameTarget}`, 'PUT', {title});
    if (selected === renameTarget && current) current.title = title;
    $('rename-dialog').close(); await refreshList(); render();
  } catch (error) { $('rename-error').textContent = error.message; }
  finally { button.disabled = false; }
};
function openDelete(chat) {
  if (pending.has(chat.id)) return;
  deleteTarget = chat.id; $('delete-description').textContent = `“${chat.title}” and its messages will be permanently deleted.`;
  $('delete-error').textContent = ''; $('delete-dialog').showModal(); $('cancel-delete').focus();
}
document.addEventListener('click', event => {
  document.querySelectorAll('.chat-actions[open]').forEach(actions => {
    if (!actions.contains(event.target)) actions.open = false;
  });
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') document.querySelectorAll('.chat-actions[open]').forEach(actions => {
    actions.open = false; actions.querySelector('summary').focus();
  });
});
$('cancel-delete').onclick = () => $('delete-dialog').close();
$('confirm-delete').onclick = async () => {
  $('confirm-delete').disabled = true;
  try {
    await api(`/${deleteTarget}`, 'DELETE');
    drafts.delete(deleteTarget); errors.delete(deleteTarget);
    $('delete-dialog').close(); await refreshList();
    if (selected === deleteTarget) await selectChat(chats[0]?.id || null);
  } catch (error) { $('delete-error').textContent = error.message; }
  finally { $('confirm-delete').disabled = false; }
};
async function init() {
  $('send').disabled = true;
  try {
    await refreshList();
    let saved; try { saved = localStorage.getItem('damage-active-chat'); } catch (_) {}
    await selectChat(chats.find(c => c.id === saved)?.id || chats[0]?.id || null);
  } catch (error) { errors.set(null, `${error.message} Reload to retry.`); render(); }
}
init();
