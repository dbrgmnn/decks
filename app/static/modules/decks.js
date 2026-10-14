import {$} from './dom.js';

const arrowSvg = axis => {
  const paths = {
    up: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 5.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    down: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 18.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    left: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 5.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    right: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 18.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>'
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[axis] || paths.right}</svg>`;
};

export function initDecks({confirmDelete, errText, getCurrentDeck, openDeckCards}) {
  const deckEditSheet = $('#deck-edit');
  const deckForm = $('#deck-form');
  const deckNameField = $('#deck-form [name=name]');
  const deckFolderField = $('#deck-folder');
  const deckMsg = $('#deck-msg');
  const pauseToggle = $('#pause-toggle');
  const stepsButtons = [...document.querySelectorAll('#steps button')];
  const deleteDeckButton = $('#delete-deck');
  const deckEditClose = $('#deck-edit .close');
  const newDeckForm = $('#new-deck');
  const newDeckMsg = $('#new-msg');
  const deckGrid = $('.decks');
  const deckNodes = [...document.querySelectorAll('.deck[data-id]')];
  const starButtons = [...document.querySelectorAll('.star')];

  const deckData = deck => ({
    id: deck.dataset.id,
    name: deck.dataset.name,
    newPerDay: deck.dataset.newPerDay,
    paused: deck.dataset.paused === '1',
    folder: deck.dataset.folder,
  });

  const getDeckNode = deckId => document.querySelector(`.deck[data-id="${deckId}"]`);

  const updateDeckNode = (deckId, payload) => {
    const deck = getDeckNode(deckId);
    if (!deck) return;
    deck.dataset.name = payload.name;
    deck.dataset.newPerDay = String(payload.new_per_day);
    deck.dataset.paused = payload.paused;
    deck.dataset.folder = payload.folder_id || '';
    const title = deck.querySelector('.title, .deck-name, [data-role="deck-name"]');
    if (title) title.textContent = payload.name;
  };

  const setDeckOpts = (newPerDay, paused) => {
    deckForm.new_per_day.value = newPerDay;
    deckForm.paused.value = paused ? '1' : '0';
    stepsButtons.forEach(button => {
      button.classList.toggle('on', button.dataset.v === String(newPerDay));
    });
    pauseToggle.setAttribute('aria-pressed', paused ? 'true' : 'false');
    pauseToggle.textContent = paused ? 'Paused' : 'Pause';
  };

  const openDeckEdit = deck => {
    const currentDeck = deckData(deck);
    deckNameField.value = currentDeck.name;
    deckMsg.textContent = '';
    setDeckOpts(currentDeck.newPerDay, currentDeck.paused);
    if (deckFolderField) {
      deckFolderField.value = currentDeck.folder && currentDeck.folder !== '0' ? currentDeck.folder : '';
    }
    deckEditSheet.dataset.deckId = currentDeck.id;
    deckEditSheet.dataset.deckName = currentDeck.name;
    deckEditSheet.hidden = false;
    deckNameField.focus();
  };

  deckForm.onsubmit = async event => {
    event.preventDefault();
    const deckId = deckEditSheet.dataset.deckId;
    const payload = Object.fromEntries(new FormData(deckForm));
    const response = await fetch('/api/decks/' + deckId, {
      method: 'PUT',
      body: new URLSearchParams(new FormData(deckForm)),
    });

    if (!response.ok) {
      deckMsg.textContent = await errText(response);
      return;
    }

    updateDeckNode(deckId, payload);
    location.reload();
  };

  deleteDeckButton.onclick = () => {
    const currentDeck = getCurrentDeck() || {
      id: deckEditSheet.dataset.deckId,
      name: deckEditSheet.dataset.deckName,
    };
    confirmDelete('deck', currentDeck);
  };

  deckEditClose.onclick = () => {
    deckEditSheet.hidden = true;
  };

  if (newDeckForm) {
    newDeckForm.onsubmit = async event => {
      event.preventDefault();
      const response = await fetch('/api/decks', {
        method: 'POST',
        body: new URLSearchParams(new FormData(event.target)),
      });
      if (response.ok) {
        location.reload();
      } else {
        newDeckMsg.textContent = await errText(response);
      }
    };
  }

  deckNodes.forEach(deck => {
    deck.addEventListener('click', async event => {
      if (event.target.closest('.edit')) {
        event.stopPropagation();
        openDeckEdit(deck);
        return;
      }
      if (event.target.closest('.plus, .star, .learn, .arrow')) return;
      await openDeckCards({id: deck.dataset.id, name: deck.dataset.name});
    });
  });

  starButtons.forEach(button => {
    button.onclick = async event => {
      event.stopPropagation();
      const deck = button.closest('.deck');
      const on = button.getAttribute('aria-pressed') !== 'true';
      const response = await fetch('/api/decks/' + deck.dataset.id + '/pin', {
        method: 'POST',
        body: new URLSearchParams({pinned: on ? 1 : 0}),
      });
      if (!response.ok) return;

      location.reload();
    };
  });

  stepsButtons.forEach(button => {
    button.onclick = () => setDeckOpts(button.dataset.v, deckForm.paused.value === '1');
  });

  pauseToggle.onclick = () => setDeckOpts(deckForm.new_per_day.value, deckForm.paused.value !== '1');

  if (!deckGrid) return;

  const HOLD_MS = 2000;
  let holdTimer = null;
  let holdPos = null;
  let moving = null;
  let swallow = false;

  const deckEls = () => [...deckGrid.querySelectorAll('.deck[data-id]')];
  const isVertical = () => getComputedStyle(deckGrid).gridTemplateColumns.split(' ').length === 1;

  const saveOrder = async () => {
    const body = new URLSearchParams();
    deckEls().forEach(deck => body.append('ids', deck.dataset.id));
    const response = await fetch('/api/decks/order', {method: 'POST', body});
    if (!response.ok) alert('Could not save deck order.');
  };

  const syncArrows = () => {
    if (!moving) return;
    const vertical = isVertical();
    const all = deckEls();
    const index = all.indexOf(moving);
    deckGrid.classList.toggle('vertical', vertical);
    const [prev, next] = moving.querySelectorAll('.arrow');
    prev.innerHTML = arrowSvg('left');
    next.innerHTML = arrowSvg('right');
    prev.setAttribute('aria-label', 'Move left');
    next.setAttribute('aria-label', 'Move right');
    prev.disabled = index === 0;
    next.disabled = index === all.length - 1;
  };

  const shift = async dir => {
    const sibling = dir < 0 ? moving.previousElementSibling : moving.nextElementSibling;
    if (!sibling || !sibling.dataset.id) return;
    dir < 0 ? sibling.before(moving) : sibling.after(moving);
    moving.scrollIntoView({block: 'nearest'});
    syncArrows();
    await saveOrder();
  };

  const enterMove = deck => {
    moving = deck;
    swallow = true;
    deck.classList.remove('holding');
    deck.classList.add('moving');
    deckGrid.classList.add('reordering');

    for (const cls of ['prev', 'next']) {
      const button = document.createElement('button');
      button.className = 'arrow ' + cls;
      button.onclick = event => {
        event.stopPropagation();
        shift(cls === 'prev' ? -1 : 1);
      };
      deck.append(button);
    }

    syncArrows();
    navigator.vibrate?.(25);
  };

  const exitMove = () => {
    if (!moving) return;
    moving.querySelectorAll('.arrow').forEach(arrow => arrow.remove());
    moving.classList.remove('moving');
    deckGrid.classList.remove('reordering', 'vertical');
    moving = null;
  };

  const cancelHold = deck => {
    clearTimeout(holdTimer);
    deck.classList.remove('holding');
    holdPos = null;
  };

  for (const deck of deckEls()) {
    deck.addEventListener('contextmenu', event => event.preventDefault());
    deck.addEventListener('pointerdown', event => {
      if (moving || event.button > 0 || event.target.closest('button,input,select,summary')) return;
      holdPos = [event.clientX, event.clientY];
      deck.classList.add('holding');
      holdTimer = setTimeout(() => enterMove(deck), HOLD_MS);
    });
    deck.addEventListener('pointermove', event => {
      if (holdPos && Math.hypot(event.clientX - holdPos[0], event.clientY - holdPos[1]) > 10) cancelHold(deck);
    });
    for (const name of ['pointerup', 'pointercancel', 'pointerleave']) {
      deck.addEventListener(name, () => {
        cancelHold(deck);
        if (moving) setTimeout(() => { swallow = false; }, 400);
      });
    }
  }

  document.addEventListener('click', event => {
    if (swallow) {
      swallow = false;
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (!moving || event.target.closest('.arrow')) return;
    event.preventDefault();
    event.stopPropagation();
    exitMove();
  }, true);

  addEventListener('keydown', event => {
    if (event.key === 'Escape') exitMove();
  });

  addEventListener('resize', syncArrows);
}
