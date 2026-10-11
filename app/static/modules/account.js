import {$} from './dom.js';

function quickAddMessage(data) {
  const folderName = data.folder?.name || 'Folder';
  const deckName = data.deck?.name || 'Deck';
  const cardPath = `“${folderName} / ${deckName}”`;

  if (data.kind === 'folder') {
    return data.folder.status === 'created'
      ? `Folder “${folderName}” created ✓`
      : `Folder “${folderName}” already exists`;
  }

  if (data.kind === 'deck') {
    return data.deck.status === 'created'
      ? `Deck “${deckName}” added to folder “${folderName}” ✓`
      : `Deck “${deckName}” already exists in folder “${folderName}”`;
  }

  if (data.kind === 'card') {
    return data.card.status === 'created'
      ? `Card added to ${cardPath} ✓`
      : `This card already exists in ${cardPath}`;
  }

  return 'Saved ✓';
}

export function initAccount({confirmDelete, errText}) {
  let folderAdded = false;

  const closeTokenSheet = () => {
    $('#token-sheet').hidden = true;
    $('#api-token-value').value = '';
    $('#api-token-copy-msg').textContent = '';
  };

  $('#account').onclick = () => {
    $('#folder-add-form').reset();
    $('#fa-msg').textContent = '';
    $('#pw-form').reset();
    $('#pw-msg').textContent = '';
    $('#tz-msg').textContent = '';
    $('#api-token-msg').textContent = '';
    $('#api-token-copy-msg').textContent = '';
    $('#export-csv-msg').textContent = '';
    $('#import-csv-msg').textContent = '';
    $('#account-sheet').hidden = false;
  };

  $('#account-sheet .close').onclick = () => {
    $('#account-sheet').hidden = true;
    if (folderAdded) location.reload();
  };

  $('#folder-add-form').onsubmit = async event => {
    event.preventDefault();
    const name = event.target.name.value.trim();
    const msg = $('#fa-msg');
    const response = await fetch('/api/folders', {method: 'POST', body: new URLSearchParams({name})});
    if (response.ok) {
      const data = await response.json();
      folderAdded = true;
      msg.textContent = quickAddMessage(data);
      event.target.reset();
    } else {
      msg.textContent = await errText(response);
    }
  };

  $('#pw-form').onsubmit = async event => {
    event.preventDefault();
    if (event.target.password.value !== event.target.password2.value) {
      $('#pw-msg').textContent = 'Passwords do not match';
      return;
    }
    const response = await fetch('/api/password', {method: 'POST', body: new URLSearchParams(new FormData(event.target))});
    if (response.ok) {
      event.target.reset();
      $('#pw-msg').textContent = 'Password changed ✓';
    } else {
      $('#pw-msg').textContent = await errText(response);
    }
  };

  $('#logout').onclick = async () => {
    await fetch('/api/logout', {method: 'POST'});
    location.href = '/login';
  };

  $('#tz').dataset.prev = $('#tz').value;
  $('#tz').onchange = async event => {
    const select = event.target;
    const response = await fetch('/api/settings', {method: 'POST', body: new URLSearchParams({tz: select.value})});
    if (response.ok) {
      select.dataset.prev = select.value;
      $('#tz-msg').textContent = 'Saved ✓';
    } else {
      select.value = select.dataset.prev;
      $('#tz-msg').textContent = await errText(response);
    }
  };

  $('#api-token').onclick = async () => {
    $('#api-token-msg').textContent = '';
    const response = await fetch('/api/account/token', {method: 'POST'});
    if (!response.ok) {
      $('#api-token-msg').textContent = await errText(response);
      return;
    }
    const data = await response.json();
    $('#api-token-value').value = data.token || '';
    $('#api-token-copy-msg').textContent = '';
    $('#token-sheet').hidden = false;
  };

  $('#api-token-copy').onclick = async () => {
    const field = $('#api-token-value');
    const value = field.value;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        field.focus();
        field.select();
        field.setSelectionRange(0, value.length);
        if (!document.execCommand('copy')) throw new Error('copy failed');
      }
      $('#api-token-copy-msg').textContent = 'Copied ✓';
    } catch {
      try {
        field.focus();
        field.select();
        field.setSelectionRange(0, value.length);
        if (!document.execCommand('copy')) throw new Error('copy failed');
        $('#api-token-copy-msg').textContent = 'Copied ✓';
      } catch {
        $('#api-token-copy-msg').textContent = 'Select and copy manually';
      }
    }
  };

  $('#api-token-ok').onclick = closeTokenSheet;

  const syncExportScope = () => {
    const scope = $('#export-scope').value;
    $('#export-folder').hidden = scope !== 'folder';
    $('#export-deck').hidden = scope !== 'deck';
  };
  $('#export-scope').onchange = syncExportScope;
  syncExportScope();

  $('#export-csv-form').onsubmit = async event => {
    event.preventDefault();
    const form = event.target;
    const msg = $('#export-csv-msg');
    const scope = form.scope.value;
    if (scope === 'folder' && !form.folder_id.value) return msg.textContent = 'Choose a folder to export';
    if (scope === 'deck' && !form.deck_id.value) return msg.textContent = 'Choose a deck to export';
    msg.textContent = '';
    const response = await fetch('/api/export/cards.csv', {method: 'POST', body: new URLSearchParams(new FormData(form))});
    if (!response.ok) return msg.textContent = await errText(response);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'decks-cards.csv';
    a.click();
    URL.revokeObjectURL(url);
    msg.textContent = 'CSV downloaded ✓';
  };

  $('#import-csv-form').onsubmit = async event => {
    event.preventDefault();
    const form = event.target;
    const msg = $('#import-csv-msg');
    const body = new FormData(form);
    const response = await fetch('/api/import/cards.csv', {method: 'POST', body});
    if (response.ok) {
      const data = await response.json();
      msg.textContent = `Imported ${data.cards} cards · ${data.decks} decks · ${data.folders} folders ✓`;
      $('#export-deck').innerHTML = '<option value="0" disabled selected>Choose a deck</option>';
      $('#export-folder').innerHTML = '<option value="0" disabled selected>Choose a folder</option>';
      location.reload();
      form.reset();
      folderAdded = true;
    } else {
      msg.textContent = await errText(response);
    }
  };

  $('#delete-account').onclick = () => confirmDelete('account', null);
}
