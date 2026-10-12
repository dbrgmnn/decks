import {$} from './dom.js';

function quickAddDuplicateMessage(data) {
  const folderName = data.folder?.name || 'Folder';
  const deckName = data.deck?.name || 'Deck';
  const cardPath = `“${folderName} / ${deckName}”`;

  if (data.kind === 'folder') {
    return `Folder “${folderName}” already exists`;
  }

  if (data.kind === 'deck') {
    return `Deck “${deckName}” already exists in folder “${folderName}”`;
  }

  if (data.kind === 'card') {
    return `This card already exists in ${cardPath}`;
  }

  return 'Already exists';
}

function wasCreated(data) {
  if (data.kind === 'folder') return data.folder?.status === 'created';
  if (data.kind === 'deck') return data.deck?.status === 'created';
  if (data.kind === 'card') return data.card?.status === 'created';
  return false;
}

export function initQuickAdd({errText}) {
  const form = $('#quick-add-form');
  if (!form) return;

  form.onsubmit = async event => {
    event.preventDefault();
    const text = event.target.name.value.trim();
    const msg = $('#quick-add-msg');
    const response = await fetch('/api/quick-add', {method: 'POST', body: new URLSearchParams({text})});
    if (response.ok) {
      const data = await response.json();
      if (wasCreated(data)) {
        form.reset();
        msg.textContent = '';
        location.reload();
        return;
      }
      msg.textContent = quickAddDuplicateMessage(data);
    } else {
      msg.textContent = await errText(response);
    }
  };
}
