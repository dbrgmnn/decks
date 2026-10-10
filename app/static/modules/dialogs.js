import {$} from './dom.js';

export function createDialogs({errText, loadWords}) {
  let pendingDelete = null;

  const confirmDelete = (kind, item) => {
    pendingDelete = {kind, item};
    const texts = {
      deck: ['Delete deck?', `Delete “${item?.name}” and all cards in it? This cannot be undone.`],
      folder: ['Delete folder?', `Delete folder “${item?.name}” with ${item?.decks} deck${item?.decks == 1 ? '' : 's'} and ${item?.cards} card${item?.cards == 1 ? '' : 's'}? This cannot be undone.`],
      card: ['Delete card?', `Delete “${item?.front}”? This cannot be undone.`],
      account: ['Delete account?', 'This permanently deletes your account, all decks and all cards. Enter your password to confirm.'],
    };
    $('#confirm-title').textContent = texts[kind][0];
    $('#confirm-text').textContent = texts[kind][1];
    $('#confirm-msg').textContent = '';
    $('#confirm-pw').value = '';
    $('#confirm-password').hidden = kind !== 'account';
    $('#confirm').hidden = false;
    if (kind === 'account') $('#confirm-pw').focus();
  };

  const closeConfirm = () => {
    $('#confirm').hidden = true;
    $('#confirm-pw').value = '';
    pendingDelete = null;
  };

  $('#confirm-cancel').onclick = closeConfirm;
  $('#confirm-delete').onclick = async () => {
    if (!pendingDelete) return;
    const {kind, item} = pendingDelete;
    const response = kind === 'account'
      ? await fetch('/api/account/delete', {method: 'POST', body: new URLSearchParams({password: $('#confirm-pw').value})})
      : await fetch((kind === 'deck' ? '/api/decks/' : kind === 'folder' ? '/api/folders/' : '/api/cards/') + item.id, {method: 'DELETE'});
    if (!response.ok) return $('#confirm-msg').textContent = await errText(response);
    closeConfirm();
    if (kind === 'account') location.href = '/login';
    else if (kind === 'folder') location.href = '/';
    else if (kind === 'deck') location.reload();
    else loadWords();
  };

  return {confirmDelete, closeConfirm};
}
