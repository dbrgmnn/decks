import {$} from './dom.js';

export function initAccount({confirmDelete, errText}) {
  const accountButton = $('#account');
  const accountSheet = $('#account-sheet');
  const accountClose = $('#account-sheet .close');
  const pwForm = $('#pw-form');
  const pwMsg = $('#pw-msg');
  const logoutButton = $('#logout');
  const tzSelect = $('#tz');
  const tzMsg = $('#tz-msg');
  const showExportButton = $('#show-export');
  const showImportButton = $('#show-import');
  const exportBox = $('#export-box');
  const importBox = $('#import-box');
  const apiTokenButton = $('#api-token');
  const apiTokenMsg = $('#api-token-msg');
  const tokenSheet = $('#token-sheet');
  const apiTokenValue = $('#api-token-value');
  const apiTokenCopyButton = $('#api-token-copy');
  const apiTokenCopyMsg = $('#api-token-copy-msg');
  const apiTokenOk = $('#api-token-ok');
  const exportScope = $('#export-scope');
  const exportFolder = $('#export-folder');
  const exportDeck = $('#export-deck');
  const exportCsvForm = $('#export-csv-form');
  const exportCsvMsg = $('#export-csv-msg');
  const importCsvForm = $('#import-csv-form');
  const importCsvMsg = $('#import-csv-msg');
  const deleteAccountButton = $('#delete-account');

  const clearText = (...nodes) => {
    nodes.forEach(node => {
      if (node) node.textContent = '';
    });
  };

  const closeTokenSheet = () => {
    tokenSheet.hidden = true;
    apiTokenValue.value = '';
    apiTokenCopyMsg.textContent = '';
  };

  const openAccountSheet = () => {
    pwForm.reset();
    clearText(pwMsg, tzMsg, apiTokenMsg, apiTokenCopyMsg, exportCsvMsg, importCsvMsg);
    accountSheet.hidden = false;
  };

  const copyTokenValue = async value => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
    apiTokenValue.focus();
    apiTokenValue.select();
    apiTokenValue.setSelectionRange(0, value.length);
    return document.execCommand('copy');
  };

  const setDataButtons = () => {
    const exportOpen = !exportBox.hidden;
    const importOpen = !importBox.hidden;
    showExportButton.classList.toggle('on', exportOpen);
    showImportButton.classList.toggle('on', importOpen);
    showExportButton.setAttribute('aria-pressed', exportOpen ? 'true' : 'false');
    showImportButton.setAttribute('aria-pressed', importOpen ? 'true' : 'false');
  };

  const toggleDataBox = kind => {
    const exportOpen = !exportBox.hidden;
    const importOpen = !importBox.hidden;
    exportBox.hidden = kind === 'export' ? exportOpen : true;
    importBox.hidden = kind === 'import' ? importOpen : true;
    setDataButtons();
  };

  const syncExportScope = () => {
    const scope = exportScope.value;
    exportFolder.hidden = scope !== 'folder';
    exportDeck.hidden = scope !== 'deck';
  };

  accountButton.onclick = openAccountSheet;
  accountClose.onclick = () => {
    accountSheet.hidden = true;
  };

  pwForm.onsubmit = async event => {
    event.preventDefault();
    if (event.target.password.value !== event.target.password2.value) {
      pwMsg.textContent = 'Passwords do not match';
      return;
    }
    const response = await fetch('/api/password', {method: 'POST', body: new URLSearchParams(new FormData(event.target))});
    if (response.ok) {
      event.target.reset();
      pwMsg.textContent = 'Password changed ✓';
    } else {
      pwMsg.textContent = await errText(response);
    }
  };

  logoutButton.onclick = async () => {
    await fetch('/api/logout', {method: 'POST'});
    location.href = '/login';
  };

  tzSelect.dataset.prev = tzSelect.value;
  tzSelect.onchange = async event => {
    const select = event.target;
    const response = await fetch('/api/settings', {method: 'POST', body: new URLSearchParams({tz: select.value})});
    if (response.ok) {
      select.dataset.prev = select.value;
      tzMsg.textContent = 'Saved ✓';
    } else {
      select.value = select.dataset.prev;
      tzMsg.textContent = await errText(response);
    }
  };

  setDataButtons();
  showExportButton.onclick = () => toggleDataBox('export');
  showImportButton.onclick = () => toggleDataBox('import');

  apiTokenButton.onclick = async () => {
    apiTokenMsg.textContent = '';
    const response = await fetch('/api/account/token', {method: 'POST'});
    if (!response.ok) {
      apiTokenMsg.textContent = await errText(response);
      return;
    }
    const data = await response.json();
    apiTokenValue.value = data.token || '';
    apiTokenCopyMsg.textContent = '';
    tokenSheet.hidden = false;
  };

  apiTokenCopyButton.onclick = async () => {
    const value = apiTokenValue.value;
    try {
      const copied = await copyTokenValue(value);
      apiTokenCopyMsg.textContent = copied ? 'Copied ✓' : 'Select and copy manually';
    } catch {
      apiTokenCopyMsg.textContent = 'Select and copy manually';
    }
  };

  apiTokenOk.onclick = closeTokenSheet;
  exportScope.onchange = syncExportScope;
  syncExportScope();

  exportCsvForm.onsubmit = async event => {
    event.preventDefault();
    const form = event.target;
    const scope = form.scope.value;
    if (scope === 'folder' && !form.folder_id.value) return exportCsvMsg.textContent = 'Choose a folder to export';
    if (scope === 'deck' && !form.deck_id.value) return exportCsvMsg.textContent = 'Choose a deck to export';
    exportCsvMsg.textContent = '';
    const response = await fetch('/api/export/cards.csv', {method: 'POST', body: new URLSearchParams(new FormData(form))});
    if (!response.ok) return exportCsvMsg.textContent = await errText(response);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'decks-cards.csv';
    link.click();
    URL.revokeObjectURL(url);
    exportCsvMsg.textContent = 'CSV downloaded ✓';
  };

  importCsvForm.onsubmit = async event => {
    event.preventDefault();
    const form = event.target;
    const body = new FormData(form);
    const response = await fetch('/api/import/cards.csv', {method: 'POST', body});
    if (response.ok) {
      const data = await response.json();
      importCsvMsg.textContent = `Imported ${data.cards} cards · ${data.decks} decks · ${data.folders} folders ✓`;
      form.reset();
    } else {
      importCsvMsg.textContent = await errText(response);
    }
  };

  deleteAccountButton.onclick = () => confirmDelete('account', null);
}
