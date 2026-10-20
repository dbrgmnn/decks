import {$} from './dom.js';
import {t} from './i18n.js';

function quickAddDuplicateMessage(data) {
  const folderName = data.folder?.name || t('common.folder');
  const deckName = data.deck?.name || t('common.deck');
  const cardPath = t('quick_add.path', {folder: folderName, deck: deckName});

  if (data.kind === 'folder') {
    return t('quick_add.folder_exists', {name: folderName});
  }

  if (data.kind === 'deck') {
    return t('quick_add.deck_exists', {name: deckName, folder: folderName});
  }

  if (data.kind === 'card') {
    return t('quick_add.card_exists', {path: cardPath});
  }

  return t('quick_add.exists');
}

function wasCreated(data) {
  if (data.kind === 'folder') return data.folder?.status === 'created';
  if (data.kind === 'deck') return data.deck?.status === 'created';
  if (data.kind === 'card') return data.card?.status === 'created';
  return false;
}

export function initQuickAdd({errText, onCreated}) {
  const form = $('#quick-add-form');
  if (!form) return;

  const nameField = form.name;
  const msg = $('#quick-add-msg');

  form.onsubmit = async event => {
    event.preventDefault();
    const text = nameField.value.trim();
    if (!text) {
      msg.textContent = t('quick_add.enter_value');
      return;
    }

    const response = await fetch('/api/quick-add', {
      method: 'POST',
      body: new URLSearchParams({text}),
    });

    if (!response.ok) {
      msg.textContent = await errText(response);
      return;
    }

    const data = await response.json();
    if (!wasCreated(data)) {
      msg.textContent = quickAddDuplicateMessage(data);
      return;
    }

    form.reset();
    msg.textContent = '';

    // Allow incremental UI refresh without forcing a page reload.
    if (onCreated) {
      await onCreated(data);
      return;
    }
  };
}
