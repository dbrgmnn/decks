import {$, errText} from './modules/dom.js';
import {initSessionGuard} from './modules/session.js';
import {initTheme} from './modules/theme.js';
import {initKeyboardHints} from './modules/keyboard.js';
import {initServiceWorker} from './modules/pwa.js';
import {initTouchFeedback} from './modules/touch.js';
import {createDialogs} from './modules/dialogs.js';
import {initPractice} from './modules/practice.js';
import {initCards} from './modules/cards.js';
import {initDecks} from './modules/decks.js';
import {initFolders} from './modules/folders.js';
import {initAccount} from './modules/account.js';
import {initQuickAdd} from './modules/quick-add.js';

initSessionGuard();
initTheme();
initKeyboardHints();
initServiceWorker();
initTouchFeedback();

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

initPractice();
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
    document.dispatchEvent(new CustomEvent('dex:home-refresh'));
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
  if (event.key !== 'Escape') return;
  for (const [sheet, close] of escapeActions) {
    if (sheet && !sheet.hidden) {
      close();
      return;
    }
  }
});


(function(){
  const study = document.getElementById('study-enabled');
  if (!study) return;

  const main = document.querySelector('main.wrap');
  const meta = study.querySelector('.study-bar-meta');

  const computeFromDecks = () => [...document.querySelectorAll('.deck[data-id]')].reduce((acc, deck) => {
    if (deck.dataset.paused === '1') return acc;
    acc.due += Number(deck.dataset.due || 0);
    acc.fresh += Number(deck.dataset.new || 0);
    return acc;
  }, {due: 0, fresh: 0});

  const updateStudyBar = () => {
    let due = Number(main?.dataset.studyDue || 0);
    let fresh = Number(main?.dataset.studyNew || 0);

    if (!due && !fresh) {
      const totals = computeFromDecks();
      due = totals.due;
      fresh = totals.fresh;
    }

    if (main) {
      main.dataset.studyDue = String(due);
      main.dataset.studyNew = String(fresh);
    }

    meta.textContent = due || fresh ? `${due} due · ${fresh} new` : 'No cards to study';
    study.disabled = !(due || fresh);
  };

  updateStudyBar();
  document.addEventListener('dex:decks-changed', updateStudyBar);

  const refreshHomeStats = async ({allowStructuralReload = false} = {}) => {
    try {
      const response = await fetch(window.location.href, {headers: {'X-Requested-With': 'fetch'}});
      if (!response.ok) return;
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const nextMain = doc.querySelector('main.wrap');
      if (!nextMain || !main) return;

      const currentDeckCount = document.querySelectorAll('.deck[data-id]').length;
      const nextDeckCount = nextMain.querySelectorAll('.deck[data-id]').length;
      const currentFolderCount = document.querySelectorAll('.fold[data-folder]').length;
      const nextFolderCount = nextMain.querySelectorAll('.fold[data-folder]').length;
      if (allowStructuralReload && (currentDeckCount !== nextDeckCount || currentFolderCount !== nextFolderCount)) {
        location.reload();
        return;
      }

      main.dataset.studyDue = nextMain.dataset.studyDue || '0';
      main.dataset.studyNew = nextMain.dataset.studyNew || '0';

      const nextDecks = [...nextMain.querySelectorAll('.deck[data-id]')];
      nextDecks.forEach(nextDeck => {
        const currentDeck = document.querySelector(`.deck[data-id="${nextDeck.dataset.id}"]`);
        if (!currentDeck) return;
        ['due', 'new', 'paused'].forEach(key => {
          if (nextDeck.dataset[key] !== undefined) currentDeck.dataset[key] = nextDeck.dataset[key];
        });
        const nextMeta = nextDeck.querySelector('.meta small');
        const currentMeta = currentDeck.querySelector('.meta small');
        if (nextMeta && currentMeta) currentMeta.textContent = nextMeta.textContent;

        // Keep the Study button in step: it greys out once the queue is empty.
        const nextLearn = nextDeck.querySelector('.learn');
        const currentLearn = currentDeck.querySelector('.learn');
        if (nextLearn && currentLearn) currentLearn.disabled = nextLearn.disabled;
      });

      const nextFolders = [...nextMain.querySelectorAll('.fold[data-folder]')];
      nextFolders.forEach(nextFolder => {
        const currentFolder = document.querySelector(`.fold[data-folder="${nextFolder.dataset.folder}"]`);
        if (!currentFolder) return;
        const nextSmall = nextFolder.querySelector('small');
        const currentSmall = currentFolder.querySelector('small');
        if (nextSmall && currentSmall) currentSmall.textContent = nextSmall.textContent;
      });

      updateStudyBar();
    } catch (error) {
      console.warn('Could not refresh home stats', error);
    }
  };

  document.addEventListener('dex:practice-closed', () => refreshHomeStats());
  document.addEventListener('dex:home-refresh', () => refreshHomeStats({allowStructuralReload: true}));
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) updateStudyBar();
  });
})();
