import {$} from './dom.js';
import {t} from './i18n.js';

export function createDialogs({errText, loadWords}) {
  const confirmSheet = $('#confirm');
  const confirmTitle = $('#confirm-title');
  const confirmText = $('#confirm-text');
  const confirmMsg = $('#confirm-msg');
  const confirmPassword = $('#confirm-password');
  const confirmPasswordInput = $('#confirm-pw');
  const confirmCancel = $('#confirm-cancel');
  const confirmDelete = $('#confirm-delete');

  let pendingDelete = null;

  const deleteTexts = {
    deck: item => [t('dialogs.deck.title'), t('dialogs.deck.text', {name: item?.name})],
    card: item => [t('dialogs.card.title'), t('dialogs.card.text', {front: item?.front})],
    account: () => [t('dialogs.account.title'), t('dialogs.account.text')],
  };

  const closeConfirm = () => {
    confirmSheet.hidden = true;
    confirmPasswordInput.value = '';
    pendingDelete = null;
  };

  const openConfirm = (kind, item) => {
    pendingDelete = {kind, item};
    const [title, text] = deleteTexts[kind](item);
    confirmTitle.textContent = title;
    confirmText.textContent = text;
    confirmMsg.textContent = '';
    confirmPasswordInput.value = '';
    confirmPassword.hidden = kind !== 'account';
    confirmSheet.hidden = false;

    if (kind === 'account') {
      confirmPasswordInput.focus();
    }
  };

  const deleteRequest = ({kind, item}) => {
    if (kind === 'account') {
      return fetch('/api/account/delete', {
        method: 'POST',
        body: new URLSearchParams({password: confirmPasswordInput.value}),
      });
    }

    const basePath = kind === 'deck' ? '/api/decks/' : '/api/cards/';
    return fetch(basePath + item.id, {method: 'DELETE'});
  };

  confirmCancel.onclick = closeConfirm;
  confirmDelete.onclick = async () => {
    if (!pendingDelete) return;

    const {kind} = pendingDelete;
    const response = await deleteRequest(pendingDelete);
    if (!response.ok) {
      confirmMsg.textContent = await errText(response);
      return;
    }

    closeConfirm();

    if (kind === 'account') location.href = '/login';
    else if (kind === 'deck') location.reload();
    else if (kind === 'card') {
      await loadWords?.({force: true});
      document.dispatchEvent(new CustomEvent('dex:home-refresh'));
    }
  };

  return {confirmDelete: openConfirm};
}
