'use strict';
const $ = id => document.getElementById(id);
const stats = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'];
const labels = {hp:'HP', atk:'Atk', spa:'SpA', def:'Def', spd:'SpD', spe:'Spe'};
let catalog, teams = [], selected = null, editing = null, species = null, dirty = false, saving = false;
const escapeHTML = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
async function api(path = '', method = 'GET', data) {
  const response = await fetch(`/api/teams${path}`, {method, headers: {'Content-Type':'application/json'}, body:data === undefined ? undefined : JSON.stringify(data)});
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Unable to save. Please try again.');
  }
  return response.json();
}
function notify(message) { $('notice').textContent = message; }
function art(container, pokemon) {
  container.replaceChildren();
  const fallback = () => { container.innerHTML = '<span aria-hidden="true">◉</span><small>Artwork coming soon</small>'; };
  if (!pokemon) { fallback(); return; }
  const names = [...new Set([pokemon.id, pokemon.name, String(pokemon.num), String(pokemon.num).padStart(3,'0')])];
  const urls = [pokemon.art_url, ...names.map(name => `/public/pokemon/${encodeURIComponent(name)}.png`)].filter(Boolean);
  let index = 0;
  const img = new Image();
  img.alt = pokemon.name;
  img.onerror = () => { if (index < urls.length) img.src = urls[index++]; else fallback(); };
  container.append(img);
  img.onerror();
}
async function refresh() {
  teams = await api();
  if (!teams.some(t => t.team_id === selected)) selected = teams[0]?.team_id ?? null;
  render();
}
function render() {
  $('team-count').textContent = teams.length;
  $('team-list').replaceChildren();
  teams.forEach(team => {
    const button = document.createElement('button');
    button.className = `team-button${selected === team.team_id ? ' active' : ''}`;
    button.innerHTML = `${escapeHTML(team.team_name)}<small>${team.pokemon.length} / 6 Pokémon</small>`;
    button.setAttribute('aria-pressed', String(selected === team.team_id));
    button.onclick = () => { selected = team.team_id; render(); };
    $('team-list').append(button);
  });
  const team = teams.find(t => t.team_id === selected);
  if (!team) {
    $('workspace').innerHTML = '<div class="empty"><span class="empty-symbol">＋</span><h2>A great battle starts with a team.</h2><p>Create a named team to start adding Pokémon.</p></div>';
    return;
  }
  $('workspace').innerHTML = `<form class="team-heading" id="rename-team"><input aria-label="Team name" id="team-name" maxlength="100" required value="${escapeHTML(team.team_name)}"><button type="submit">Rename</button><button type="button" id="delete-team">Delete team</button></form><p class="muted">${team.pokemon.length} of 6 slots · Unique species and held items</p><div class="roster" id="roster"></div>`;
  $('rename-team').onsubmit = async event => {
    event.preventDefault();
    const name = $('team-name').value;
    try { await api(`/${team.team_id}`, 'PUT', {team_name:name}); await refresh(); notify('Team renamed.'); } catch(e) { notify(e.message); }
  };
  $('delete-team').onclick = () => openDeleteConfirmation(team);
  team.pokemon.forEach(member => {
    const card = document.createElement('article'); card.className = 'card';
    card.innerHTML = `<div class="art"></div><h3>${escapeHTML(member.name)}</h3><div>${[member.type_1, member.type_2].filter(Boolean).map(t=>`<span class="type" data-type="${escapeHTML(t)}">${escapeHTML(t)}</span>`).join('')}</div><p>${escapeHTML(member.ability)}<br>${escapeHTML(member.item || 'No held item')}</p><p class="muted">${escapeHTML(member.nature)} · ${stats.reduce((n,s)=>n+member[`${s}_points`],0)} / 66 points<br>${[1,2,3,4].map(i=>member[`move_${i}`]).filter(Boolean).map(escapeHTML).join(' · ') || 'Moves not selected'}</p><div class="card-actions"><button type="button">Edit Pokémon</button><button type="button">Remove</button></div>`;
    art(card.querySelector('.art'), catalog.pokemon.find(p=>p.name===member.name));
    const [edit, remove] = card.querySelectorAll('button');
    edit.onclick = () => openEditor(member);
    remove.onclick = async () => {
      if (!confirm(`Remove ${member.name} from this team?`)) return;
      try { await api(`/${team.team_id}/pokemon/${member.pokemon_id}`, 'DELETE'); await refresh(); notify('Pokémon removed.'); } catch(e) { notify(e.message); }
    };
    $('roster').append(card);
  });
  if (team.pokemon.length < 6) {
    const add = document.createElement('button'); add.className = 'add-card'; add.textContent = '＋ Add Pokémon'; add.onclick = () => openEditor(); $('roster').append(add);
  }
}
let deletingTeam = null, deletePending = false;
function openDeleteConfirmation(team) {
  deletingTeam = team.team_id;
  $('delete-description').textContent = `“${team.team_name}” and all ${team.pokemon.length} of its Pokémon will be permanently deleted. This cannot be undone.`;
  $('delete-error').textContent = '';
  $('delete-confirmation').showModal();
  $('cancel-delete').focus();
}
$('cancel-delete').onclick = () => { if (!deletePending) $('delete-confirmation').close(); };
$('delete-confirmation').addEventListener('cancel', event => { if (deletePending) event.preventDefault(); });
$('delete-confirmation').addEventListener('close', () => { deletingTeam = null; });
$('confirm-delete').onclick = async () => {
  if (deletePending || deletingTeam === null) return;
  deletePending = true;
  $('confirm-delete').disabled = $('cancel-delete').disabled = true;
  $('confirm-delete').textContent = 'Deleting…';
  $('delete-error').textContent = '';
  try {
    await api(`/${deletingTeam}`, 'DELETE');
    $('delete-confirmation').close();
    await refresh();
    notify('Team deleted.');
    ($('team-name') || $('new-name')).focus();
  } catch (error) {
    if ($('delete-confirmation').open) $('delete-error').textContent = error.message;
    else notify(`Team deleted, but the list could not refresh. Reload the page. ${error.message}`);
  } finally {
    deletePending = false;
    $('confirm-delete').disabled = $('cancel-delete').disabled = false;
    $('confirm-delete').textContent = 'Delete team';
  }
};
function openEditor(member = null) {
  editing = member?.pokemon_id ?? null;
  closeTeamDropdowns();
  $('pokemon-form').reset();
  $('editor-title').textContent = editing ? 'Edit Pokémon' : 'Add Pokémon';
  $('species').value = member?.name ?? '';
  $('editor-error').textContent = '';
  setSpecies(member);
  dirty = false;
  $('editor').showModal();
  $('species').focus();
}
function setSpecies(member = null) {
  species = catalog.pokemon.find(p => p.name.toLowerCase() === $('species').value.trim().toLowerCase()) || null;
  $('pokemon-details').hidden = !species;
  $('save-pokemon').disabled = !species;
  $('save-hint').textContent = species ? 'Changes are saved when you click Save.' : 'Select a Pokémon to begin.';
  if (!species) return;
  $('species-title').textContent = species.name;
  $('dex-number').textContent = `#${species.num} • ${species.height_m != null ? species.height_m + ' m' : 'Height unknown'} • ${species.weight_kg != null ? species.weight_kg + ' kg' : 'Weight unknown'}`;
  $('types').innerHTML = species.types.map(t=>`<span class="type" data-type="${escapeHTML(t)}">${escapeHTML(t)}</span>`).join('');
  art($('art'), species);
  $('ability').innerHTML = species.abilities.map(a=>`<option>${escapeHTML(a)}</option>`).join('');
  if (member) $('ability').value = member.ability;
  $('item').value = member ? (member.item ?? '') : (species.default_item ?? '');
  $('nature').value = member?.nature ?? 'Serious';
  $('stats').innerHTML = '<div class="stat stat-head"><span>STAT</span><span>BASE</span><span>INVESTMENT</span><span>POINTS</span><span>LV 50</span></div>' + stats.map(s=>`<div class="stat"><label for="${s}-slider">${labels[s]}</label><span class="muted">${species.base_stats[s]}</span><input type="range" id="${s}-slider" min="0" max="32" value="${member?.[`${s}_points`] ?? 0}" aria-label="${labels[s]} points slider"><input type="number" id="${s}-points" min="0" max="32" step="1" required value="${member?.[`${s}_points`] ?? 0}" aria-label="${labels[s]} points"><output id="${s}-total"></output></div>`).join('');
  stats.forEach(s => {
    for (const kind of ['slider','points']) $(`${s}-${kind}`).oninput = () => {
      const input = $(`${s}-${kind}`);
      const otherTotal = stats.filter(k=>k!==s).reduce((sum,k)=>sum+Number($(`${k}-points`).value),0);
      const value = Math.max(0, Math.min(32, 66-otherTotal, Math.floor(Number(input.value)||0)));
      $(`${s}-slider`).value = $(`${s}-points`).value = value;
      dirty = true; updateStats();
    };
  });
  [1,2,3,4].forEach(i=>$(`move-${i}`).value=member?.[`move_${i}`] ?? '');
  updateMoveDetails();
  syncTeamDropdowns();
  updateStats();
}
function applyMegaStone() {
  if (!species) return;
  const item = $('item').value.trim().toLowerCase();
  const mega = catalog.pokemon.find(p => p.num === species.num && p.default_item && p.default_item.toLowerCase() === item);
  if (!mega || mega.name === species.name) return;
  const preserved = {ability: mega.abilities[0], item: mega.default_item, nature: $('nature').value};
  stats.forEach(s => preserved[`${s}_points`] = Number($(`${s}-points`).value));
  [1,2,3,4].forEach(i => preserved[`move_${i}`] = $(`move-${i}`).value);
  $('species').value = mega.name;
  setSpecies(preserved);
  dirty = true;
}
function moveDetails(name) {
  return catalog.move_details[name.toLowerCase().replace(/[^a-z0-9]/g, '')];
}
function typeIcon(type) {
  return `<img class="move-type-icon" src="/api/teams/type-icons/${encodeURIComponent(type)}" alt="" loading="lazy">`;
}
function updateMoveDetails() {
  [1,2,3,4].forEach(i => {
    const panel = $(`move-${i}-details`);
    const name = $(`move-${i}`).value.trim();
    const move = moveDetails(name);
    panel.hidden = !name;
    if (!move) {
      panel.textContent = name ? 'Select a listed move to see its details.' : '';
      return;
    }
    const power = move.basePower || (move.damage || move.damageCallback || move.basePowerCallback ? 'Variable / fixed' : '—');
    const preview = abilityMovePreview(move, $('ability').value, catalog.move_traits[name.toLowerCase().replace(/[^a-z0-9]/g, '')]);
    const powerSuffix = preview.adjustedPower !== null ? ` (${preview.adjustedPower})` : '';
    const accuracy = move.accuracy === true ? 'No accuracy check' : `${move.accuracy}%`;
    panel.innerHTML = `<div class="move-detail-heading">${typeIcon(preview.type)}<strong>${escapeHTML(preview.type)}</strong><span>${escapeHTML(move.category)}</span></div>
      <dl class="move-numbers"><div><dt>PP</dt><dd>${move.pp}</dd></div><div><dt>Base power</dt><dd>${escapeHTML(power)}${powerSuffix}</dd></div><div><dt>Accuracy</dt><dd>${accuracy}</dd></div><div><dt>Priority</dt><dd>${move.priority > 0 ? '+' : ''}${move.priority}</dd></div></dl>
      ${preview.note ? `<p class="ability-preview">${escapeHTML(preview.note)}</p>` : ''}
      <p>${escapeHTML(move.shortDesc || '')}</p>
      ${move.desc && move.desc !== move.shortDesc ? `<details><summary>Full description</summary><p>${escapeHTML(move.desc)}</p></details>` : ''}`;
  });
}
function updateStats() {
  if (!species) return;
  const nature = catalog.natures.find(n=>n.name===$('nature').value);
  const aligned = nature.plus !== nature.minus;
  $('nature-effect').textContent = aligned
    ? `${nature.name}: +10% ${labels[nature.plus]}, −10% ${labels[nature.minus]}. Applied to the level-50 stats below.`
    : `${nature.name}: neutral alignment. No stat increases or reductions.`;
  let total = 0;
  stats.forEach(s=>{
    const points = Number($(`${s}-points`).value); total += points;
    const value = level50Stat(species.base_stats[s], s, points, nature);
    const direction = aligned && s === nature.plus ? 1 : aligned && s === nature.minus ? -1 : 0;
    const output = $(`${s}-total`);
    output.textContent = value;
    const row = output.closest('.stat');
    row.classList.toggle('nature-up', direction === 1);
    row.classList.toggle('nature-down', direction === -1);
    row.querySelector('label').textContent = labels[s] + (direction === 1 ? ' ↑' : direction === -1 ? ' ↓' : '');
    output.setAttribute('aria-label', `${labels[s]} ${value}${direction === 1 ? ', nature boosted' : direction === -1 ? ', nature reduced' : ''}`);
    output.title = direction ? `${nature.name}: ${direction === 1 ? '+10%' : '−10%'} ${labels[s]}` : 'No nature modifier';
  });
  $('budget').textContent = `${total} / 66 · ${66-total} left`;
}
function closeEditor() {
  if (saving) return;
  if (!dirty || confirm('Discard unsaved Pokémon changes?')) $('editor').close();
}
$('close-editor').onclick = closeEditor;
$('editor').addEventListener('cancel', e=>{e.preventDefault(); closeEditor();});
window.addEventListener('beforeunload', e=>{if(dirty && $('editor').open){e.preventDefault(); e.returnValue='';}});
$('pokemon-form').addEventListener('input', ()=>{dirty=true;});
$('species').oninput = () => setSpecies();
$('nature').onchange = updateStats;
$('ability').onchange = updateMoveDetails;
$('item').addEventListener('input', applyMegaStone);
$('item').addEventListener('change', applyMegaStone);
$('pokemon-form').onsubmit = async event => {
  event.preventDefault();
  if (!species || saving) return;
  const data = {name:species.name, ability:$('ability').value, item:$('item').value.trim(), nature:$('nature').value};
  stats.forEach(s=>data[`${s}_points`]=Number($(`${s}-points`).value));
  [1,2,3,4].forEach(i=>data[`move_${i}`]=$(`move-${i}`).value.trim());
  saving = true; $('save-pokemon').disabled = true; $('editor-error').textContent = '';
  try {
    await api(`/${selected}/pokemon${editing ? `/${editing}` : ''}`, editing ? 'PUT' : 'POST', data);
    dirty = false; $('editor').close(); await refresh(); notify('Pokémon saved to your team.');
  } catch(e) { $('editor-error').textContent = e.message; }
  finally { saving = false; $('save-pokemon').disabled = !species; }
};
$('create-team').onsubmit = async event => {
  event.preventDefault();
  const button = event.submitter; button.disabled = true;
  try {
    const result = await api('', 'POST', {team_name:$('new-name').value}); selected = result.team_id;
    $('new-name').value = ''; await refresh(); notify('Team created. Add your first Pokémon.');
  } catch(e) { notify(e.message); } finally {button.disabled=false;}
};
async function init() {
  $('create-team').querySelector('button').disabled = true;
  try {
    catalog = await api('/catalog');
    $('pokemon-options').innerHTML = catalog.pokemon.map(p=>`<option value="${escapeHTML(p.name)}"></option>`).join('');
    for (const [id, values] of [['item-options',catalog.items],['move-options',catalog.moves]]) $(id).innerHTML=values.map(v=>`<option value="${escapeHTML(v)}"></option>`).join('');
    $('nature').innerHTML = catalog.natures.map(n=>`<option value="${escapeHTML(n.name)}">${escapeHTML(n.name)}${n.plus!==n.minus ? ` (+${labels[n.plus]}, −${labels[n.minus]})` : ' (neutral)'}</option>`).join('');
    $('moves').innerHTML = [1,2,3,4].map(i=>`<div><label for="move-${i}">Move ${i}</label><input id="move-${i}" list="move-options" placeholder="Select a move" autocomplete="off"><div id="move-${i}-details" class="move-details" aria-live="polite" hidden></div></div>`).join('');
    [...$('move-options').options].forEach(option => { option.dataset.type = moveDetails(option.value)?.type || ''; });
    [1,2,3,4].forEach(i => $(`move-${i}`).addEventListener('input', updateMoveDetails));
    document.querySelectorAll('#pokemon-form input[list], #pokemon-form select').forEach(createTeamDropdown);
    await refresh();
    $('create-team').querySelector('button').disabled = false;
  } catch(e) { notify(`Could not load your team library. ${e.message} Reload to retry.`); }
}
init();
