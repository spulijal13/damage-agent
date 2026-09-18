'use strict';

function splitPokemonMessage(content) {
  const match = content.match(/\n\n```saved-pokemon\n([^]*?)\n```$/);
  if (match) {
    try {
      const members = JSON.parse(match[1]);
      if (Array.isArray(members) && members.every(m => m && Number.isInteger(m.team_member_id) && typeof m.name === 'string' && typeof m.team === 'string')) {
        return {text: content.slice(0, match.index), members};
      }
    } catch (_) {}
  }
  return {text: content, members: []};
}

function inlinePokemonChip(member, onRemove) {
  const chip = document.createElement('span'); chip.className = 'pokemon-chip';
  chip.contentEditable = 'false'; chip.dataset.member = JSON.stringify(member);
  chip.title = `${member.name} · ${member.team}`;
  const name = document.createElement('span'); name.textContent = member.name; chip.append(name);
  if (onRemove) {
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×';
    remove.setAttribute('aria-label', `Remove ${member.name} from ${member.team}`);
    remove.onclick = () => { chip.remove(); onRemove(); }; chip.append(remove);
  }
  return chip;
}

function renderPokemonMessage(container, content, onRemove) {
  const {text, members} = splitPokemonMessage(content);
  const byId = new Map(members.map(m => [String(m.team_member_id), m]));
  const pattern = /\[\[pokemon:(\d+)\]\]/g;
  let position = 0, match, inline = false;
  container.replaceChildren();
  while ((match = pattern.exec(text))) {
    container.append(document.createTextNode(text.slice(position, match.index)));
    const member = byId.get(match[1]);
    container.append(member ? inlinePokemonChip(member, onRemove) : document.createTextNode(match[0]));
    inline ||= Boolean(member); position = pattern.lastIndex;
  }
  container.append(document.createTextNode(text.slice(position)));
  // Older messages used attachments above their text; keep those readable.
  if (!inline && members.length) {
    const legacy = document.createElement('span'); legacy.className = 'pokemon-chips';
    members.forEach(m => legacy.append(inlinePokemonChip(m, onRemove)));
    container.prepend(legacy);
  }
}

function createPokemonEditor(element) {
  let cursor = null;
  const changed = () => element.dispatchEvent(new Event('input', {bubbles: true}));
  document.addEventListener('selectionchange', () => {
    const selection = window.getSelection();
    if (selection.rangeCount && element.contains(selection.anchorNode) && element.contains(selection.focusNode)) {
      cursor = selection.getRangeAt(0).cloneRange();
    }
  });
  function insertNode(node) {
    element.focus();
    const range = cursor && element.contains(cursor.commonAncestorContainer) ? cursor : document.createRange();
    if (range !== cursor) { range.selectNodeContents(element); range.collapse(false); }
    range.deleteContents(); range.insertNode(node); range.setStartAfter(node); range.collapse(true);
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    cursor = range.cloneRange(); changed();
  }
  element.addEventListener('paste', event => {
    event.preventDefault(); insertNode(document.createTextNode(event.clipboardData.getData('text/plain')));
  });
  // Prevent dragged HTML from introducing arbitrary editable markup.
  element.addEventListener('drop', event => event.preventDefault());
  return {
    getValue() {
      const members = new Map();
      function read(node) {
        if (node.nodeType === Node.TEXT_NODE) return node.textContent;
        if (node.dataset?.member) {
          const member = JSON.parse(node.dataset.member); members.set(member.team_member_id, member);
          return `[[pokemon:${member.team_member_id}]]`;
        }
        if (node.nodeName === 'BR') return '\n';
        const text = [...node.childNodes].map(read).join('');
        return ['DIV', 'P'].includes(node.nodeName) && node !== element ? '\n' + text : text;
      }
      const text = read(element).trim();
      return text + (members.size ? '\n\n```saved-pokemon\n' + JSON.stringify([...members.values()]) + '\n```' : '');
    },
    setValue(value) { cursor = null; renderPokemonMessage(element, value || '', changed); },
    insert(member) {
      const fragment = document.createDocumentFragment();
      fragment.append(inlinePokemonChip(member, changed), document.createTextNode('\u00a0'));
      // A fragment disappears on insertion; retain its final text node for the caret.
      const tail = fragment.lastChild;
      element.focus();
      const range = cursor && element.contains(cursor.commonAncestorContainer) ? cursor : document.createRange();
      if (range !== cursor) { range.selectNodeContents(element); range.collapse(false); }
      range.deleteContents(); range.insertNode(fragment); range.setStartAfter(tail); range.collapse(true);
      const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
      cursor = range.cloneRange(); changed();
    },
  };
}
