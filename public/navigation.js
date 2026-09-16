(() => {
  if (document.getElementById('workspace-tabs')) return;
  document.body.dataset.workspace = 'chat';
  const nav = document.createElement('nav');
  nav.id = 'workspace-tabs';
  nav.setAttribute('aria-label', 'Workspace');
  nav.innerHTML = '<button type="button" aria-pressed="true">Damage calculator</button><button type="button" aria-pressed="false">Team builder</button>';
  const panel = document.createElement('iframe');
  panel.id = 'team-builder-panel';
  panel.title = 'Team builder';
  panel.hidden = true;
  const chats = document.createElement('iframe');
  chats.id = 'chat-panel';
  chats.title = 'Damage calculator chats';
  chats.src = '/public/chats.html?v=20260915';
  document.body.append(nav, chats, panel);
  const buttons = [...nav.querySelectorAll('button')];
  buttons.forEach((button, index) => button.addEventListener('click', () => {
    document.body.dataset.workspace = index === 0 ? 'chat' : 'teams';
    buttons.forEach((b, i) => b.setAttribute('aria-pressed', String(i === index)));
    panel.hidden = index === 0;
    chats.hidden = index === 1;
    // Keep both editors mounted when switching tabs.
    const chat = document.getElementById('root');
    if (chat) { chat.inert = true; chat.hidden = true; }
    if (index === 1 && !panel.getAttribute('src')) panel.src = '/public/teams.html?v=20260914';
  }));
})();
