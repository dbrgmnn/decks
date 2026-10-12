import {$, errText} from './modules/dom.js';
import {initSessionGuard} from './modules/session.js';
import {initTheme} from './modules/theme.js';
import {createDialogs} from './modules/dialogs.js';
import {initPractice} from './modules/practice.js';
import {initCards} from './modules/cards.js';
import {initDecks} from './modules/decks.js';
import {initFolders} from './modules/folders.js';
import {initAccount} from './modules/account.js';
import {initQuickAdd} from './modules/quick-add.js';

initSessionGuard();
initTheme();

const accountSheet = $('#account-sheet');
const confirmSheet = $('#confirm');
const confirmCancel = $('#confirm-cancel');
const deckEditSheet = $('#deck-edit');
const deckEditClose = $('#deck-edit .close');
const folderSheet = $('#folder-sheet');
const folderSheetClose = $('#folder-sheet .close');
const addSheet = $('#add');
const addSheetClose = $('#add .close');
const listSheet = $('#list');
const listSheetClose = $('#list .close');
const practiceSheet = $('#practice');

const practice = initPractice();
const cards = {};
const dialogs = createDialogs({
  errText,
  loadWords: options => cards.loadWords?.(options),
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
initQuickAdd({
  errText,
  onCreated: async () => {
    location.reload();
  },
});

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

// One delegated listener is cheaper than per-button bindings.
document.addEventListener('click', event => {
  const button = event.target.closest('.password-toggle');
  if (!button) return;
  togglePasswordField(button);
});

const escapeActions = [
  [accountSheet, () => $('#account-sheet .close')?.click()],
  [confirmSheet, () => confirmCancel?.click()],
  [deckEditSheet, () => deckEditClose?.click()],
  [folderSheet, () => folderSheetClose?.click()],
  [addSheet, () => addSheetClose?.click()],
  [listSheet, () => listSheetClose?.click()],
];

addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    for (const [sheet, close] of escapeActions) {
      if (sheet && !sheet.hidden) {
        close();
        return;
      }
    }
  }

  if (!practiceSheet?.hidden && event.key === ' ') {
    practice.flip();
  }
});
