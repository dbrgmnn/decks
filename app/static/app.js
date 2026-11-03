import {$, errText} from './modules/dom.js';
import {t} from './modules/i18n.js';
import {initSessionGuard} from './modules/session.js';
import {initTheme} from './modules/theme.js';
import {initKeyboardHints} from './modules/keyboard.js';
import {initServiceWorker} from './modules/pwa.js';
import {initTouchFeedback} from './modules/touch.js';
import {initPasswordToggles} from './modules/password.js';
import {createDialogs} from './modules/dialogs.js';
import {initPractice} from './modules/practice.js';
import {initCards} from './modules/cards.js';
import {initDecks} from './modules/decks.js';
import {initAccount} from './modules/account.js';

initSessionGuard();
initTheme();
initKeyboardHints();

// Lock background scroll while a sheet is open (prevents the page behind the
// keyboard from scrolling), but keep the sheet itself scrollable.
let savedScrollY = 0;
let openSheetCount = 0;
const lockBodyScroll = () => {
  const openSheets = [...document.querySelectorAll('.sheet, #practice')].filter(el => !el.hidden);
  if (openSheets.length > 0 && openSheetCount === 0) {
    savedScrollY = window.scrollY;
    document.documentElement.classList.add('sheet-open');
    document.body.style.position = 'fixed';
    document.body.style.top = `-${savedScrollY}px`;
    document.body.style.width = '100%';
  } else if (openSheets.length === 0 && openSheetCount > 0) {
    document.documentElement.classList.remove('sheet-open');
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.width = '';
    window.scrollTo(0, savedScrollY);
  }
  openSheetCount = openSheets.length;
};
const sheetObserver = new MutationObserver(lockBodyScroll);
document.querySelectorAll('.sheet, #practice').forEach(el => sheetObserver.observe(el, {attributes: true, attributeFilter: ['hidden']}));
lockBodyScroll();

// Keep focused inputs visible when the on-screen keyboard shrinks the viewport.
document.addEventListener('focusin', (event) => {
  const target = event.target;
  if (!target || !target.matches('input, textarea, select')) return;
  if (!target.closest('.sheet')) return;
  requestAnimationFrame(() => {
    target.scrollIntoView({ block: 'center', behavior: 'smooth' });
  });
});

initServiceWorker();
initTouchFeedback();
initPasswordToggles();

const accountSheet = $('#account-sheet');
const newDeckSheet = $('#new-deck-sheet');
const newDeckClose = $('#new-deck-sheet .close');
const confirmSheet = $('#confirm');
const confirmCancel = $('#confirm-cancel');
const tokenConfirmSheet = $('#token-confirm');
const tokenConfirmCancel = $('#api-token-confirm-cancel');
const deckEditSheet = $('#deck-edit');
const deckEditClose = $('#deck-edit .close');
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
  openDeckCards: cards.openDeckCards,
});

initAccount({confirmDelete: dialogs.confirmDelete, errText});

const escapeActions = [
  [tokenConfirmSheet, () => tokenConfirmCancel?.click()],
  [newDeckSheet, () => newDeckClose?.click()],
  [accountSheet, () => $('#account-sheet .close')?.click()],
  [confirmSheet, () => confirmCancel?.click()],
  [deckEditSheet, () => deckEditClose?.click()],
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

    meta.textContent = due || fresh ? t('home.study_bar_meta', {due, new: fresh}) : t('home.no_cards');
    study.disabled = !(due || fresh);
  };

  updateStudyBar();
  document.addEventListener('dex:decks-changed', updateStudyBar);

  const refreshHomeStats = async ({allowStructuralReload = false} = {}) => {
    try {
      const response = await fetch(window.location.href);
      if (!response.ok) return;
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const nextMain = doc.querySelector('main.wrap');
      if (!nextMain || !main) return;

      const currentDeckCount = document.querySelectorAll('.deck[data-id]').length;
      const nextDeckCount = nextMain.querySelectorAll('.deck[data-id]').length;
      if (allowStructuralReload && currentDeckCount !== nextDeckCount) {
        location.reload();
        return;
      }

      main.dataset.studyDue = nextMain.dataset.studyDue || '0';
      main.dataset.studyNew = nextMain.dataset.studyNew || '0';

      const nextDecks = [...nextMain.querySelectorAll('.deck[data-id]')];
      nextDecks.forEach(nextDeck => {
        const currentDeck = document.querySelector(`.deck[data-id="${nextDeck.dataset.id}"]`);
        if (!currentDeck) return;
        ['due', 'new', 'paused', 'newPerDay'].forEach(key => {
          if (nextDeck.dataset[key] !== undefined) currentDeck.dataset[key] = nextDeck.dataset[key];
        });
        currentDeck.classList.toggle('paused', nextDeck.dataset.paused === '1');
        const nextMeta = nextDeck.querySelector('.meta small');
        const currentMeta = currentDeck.querySelector('.meta small');
        if (nextMeta && currentMeta) currentMeta.textContent = nextMeta.textContent;
        const nextCount = nextDeck.querySelector('.count');
        const currentCount = currentDeck.querySelector('.count');
        if (nextCount && currentCount) currentCount.textContent = nextCount.textContent;
        const nextLimit = nextDeck.querySelector('.daily-limit');
        const currentLimit = currentDeck.querySelector('.daily-limit');
        if (nextLimit && currentLimit) currentLimit.value = nextLimit.value;
        const nextPause = nextDeck.querySelector('.pause');
        const currentPause = currentDeck.querySelector('.pause');
        if (nextPause && currentPause) {
          currentPause.setAttribute('aria-pressed', nextPause.getAttribute('aria-pressed'));
          currentPause.setAttribute('aria-label', nextPause.getAttribute('aria-label'));
          currentPause.textContent = nextPause.textContent;
        }

        // Keep the Study button in step: it greys out once the queue is empty.
        const nextLearn = nextDeck.querySelector('.learn');
        const currentLearn = currentDeck.querySelector('.learn');
        if (nextLearn && currentLearn) currentLearn.disabled = nextLearn.disabled;
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
