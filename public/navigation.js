(() => {
  if (document.getElementById('workspace-tabs')) return;
  const nav = document.createElement('nav');
  nav.id = 'workspace-tabs';
  nav.setAttribute('aria-label', 'Workspace');
  nav.innerHTML = '<button type="button" aria-pressed="true">Damage calculator</button><button type="button" aria-pressed="false">Team builder</button>';
  const panel = document.createElement('iframe');
  panel.id = 'team-builder-panel';
  panel.title = 'Team builder';
  panel.hidden = true;
  document.body.append(nav, panel);
  const buttons = [...nav.querySelectorAll('button')];
  buttons.forEach((button, index) => button.addEventListener('click', () => {
    buttons.forEach((b, i) => b.setAttribute('aria-pressed', String(i === index)));
    panel.hidden = index === 0;
    // Keep the mounted chat and team editor alive when switching tabs.
    const chat = document.getElementById('root');
    if (chat) chat.inert = index === 1;
    if (index === 1 && !panel.getAttribute('src')) panel.src = '/public/teams.html';
  }));
})();
