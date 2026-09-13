// Searchable, keyboard-accessible choices rendered inside the team editor.
const teamDropdowns = [];
function createTeamDropdown(control) {
  const isSelect = control.tagName === 'SELECT';
  const source = isSelect ? control : document.getElementById(control.getAttribute('list'));
  const wrapper = document.createElement('div');
  wrapper.className = 'team-combobox';
  control.before(wrapper);
  wrapper.append(control);
  let input = control;
  if (isSelect) {
    control.hidden = true;
    input = document.createElement('input');
    input.id = `${control.id}-search`;
    input.placeholder = 'Search options…';
    wrapper.append(input);
    document.querySelector(`label[for="${control.id}"]`)?.setAttribute('for', input.id);
  } else control.removeAttribute('list');
  input.autocomplete = 'off';
  input.spellcheck = false;
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false');
  const list = document.createElement('div');
  list.className = 'team-options';
  list.id = `${control.id}-choices`;
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', document.querySelector(`label[for="${input.id}"]`)?.textContent || 'Options');
  list.hidden = true;
  wrapper.append(list);
  input.setAttribute('aria-controls', list.id);
  let matches = [], active = -1;
  const sync = () => {
    if (isSelect) input.value = control.selectedOptions[0]?.textContent || '';
  };
  const close = () => {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    active = -1;
    sync();
  };
  function highlight(index) {
    active = index;
    [...list.children].forEach((row, i) => row.setAttribute('aria-selected', String(i === active)));
    const row = list.children[active];
    if (row) {
      input.setAttribute('aria-activedescendant', row.id);
      row.scrollIntoView({block:'nearest'});
    }
  }
  function choose(index) {
    const option = matches[index];
    if (!option) return;
    control.value = option.value;
    control.dispatchEvent(new Event('input', {bubbles:true}));
    control.dispatchEvent(new Event('change', {bubbles:true}));
    close();
  }
  function show(filter = '') {
    teamDropdowns.forEach(dropdown => { if (dropdown.control !== control) dropdown.close(); });
    const query = filter.toLowerCase().trim();
    matches = [...source.options].filter(option => option.textContent.toLowerCase().includes(query) || option.value.toLowerCase().includes(query));
    list.replaceChildren();
    active = -1;
    input.removeAttribute('aria-activedescendant');
    for (const [index, option] of matches.entries()) {
      const row = document.createElement('div');
      row.id = `${list.id}-${index}`;
      row.className = 'team-option';
      row.setAttribute('role', 'option');
      row.setAttribute('aria-selected', 'false');
      row.textContent = option.textContent || option.value;
      // Keep focus on the combobox until selection has completed.
      row.addEventListener('mousedown', event => event.preventDefault());
      row.addEventListener('click', () => choose(index));
      list.append(row);
    }
    if (!matches.length) {
      const empty = document.createElement('div');
      empty.className = 'team-options-empty';
      empty.textContent = 'No matches. Try another name.';
      list.append(empty);
    }
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }
  input.addEventListener('focus', () => show());
  input.addEventListener('click', () => { if (list.hidden) show(); });
  input.addEventListener('input', () => show(input.value));
  input.addEventListener('blur', close);
  input.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (list.hidden) show();
      if (matches.length) highlight((active + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length);
    } else if (event.key === 'Enter' && !list.hidden) {
      event.preventDefault();
      if (active >= 0) choose(active);
      else if (matches.length === 1) choose(0);
      else close();
    } else if (event.key === 'Escape' && !list.hidden) {
      event.preventDefault();
      event.stopPropagation();
      close();
    } else if (event.key === 'Tab') close();
  });
  teamDropdowns.push({control, sync, close});
  sync();
}
function syncTeamDropdowns() { teamDropdowns.forEach(dropdown => dropdown.sync()); }
function closeTeamDropdowns() { teamDropdowns.forEach(dropdown => dropdown.close()); }
