import {$, errText} from './modules/dom.js';
import {initSessionGuard} from './modules/session.js';
import {initTheme} from './modules/theme.js';
import {createDialogs} from './modules/dialogs.js';
import {initPractice} from './modules/practice.js';
import {initCards} from './modules/cards.js';
import {initDecks} from './modules/decks.js';
import {initFolders} from './modules/folders.js';
import {initAccount} from './modules/account.js';

initSessionGuard();
initTheme();

const practice = initPractice();
const cards = {};
const dialogs = createDialogs({
  errText,
  loadWords: () => cards.loadWords?.(),
});

Object.assign(cards, initCards({
  confirmDelete: dialogs.confirmDelete,
  errText,
}));

initDecks({
  confirmDelete: dialogs.confirmDelete,
  errText,
  getCurrentDeck: cards.getCurrentDeck,
  openDeckCards: cards.openDeckCards,
});
initFolders({confirmDelete: dialogs.confirmDelete, errText});
initAccount({confirmDelete: dialogs.confirmDelete, errText});

const togglePasswordField = button => {
  const field = button.closest('.password-field');
  const input = field?.querySelector('input');
  if (!input) return;
  const visible = input.type === 'text';
  input.type = visible ? 'password' : 'text';
  button.setAttribute('aria-pressed', String(!visible));
  button.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
  field.querySelector('.eye-open')?.toggleAttribute('hidden', !visible);
  field.querySelector('.eye-closed')?.toggleAttribute('hidden', visible);
};

document.querySelectorAll('.password-toggle').forEach(button => {
  button.addEventListener('click', () => togglePasswordField(button));
});

addEventListener('keydown', event => {
  if (!$('#account-sheet').hidden) return event.key === 'Escape' && $('#account-sheet .close').click();
  if (!$('#confirm').hidden) return event.key === 'Escape' && $('#confirm-cancel').click();
  if (!$('#deck-edit').hidden) return event.key === 'Escape' && $('#deck-edit .close').click();
  if (!$('#folder-sheet').hidden) return event.key === 'Escape' && $('#folder-sheet .close').click();
  if (!$('#add').hidden) return event.key === 'Escape' && $('#add .close').click();
  if (!$('#list').hidden) return event.key === 'Escape' && $('#list .close').click();
  if ($('#practice').hidden) return;
  if (event.key === ' ') practice.flip();
});
