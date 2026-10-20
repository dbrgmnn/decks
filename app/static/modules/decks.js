import {$, afterCenterX, afterCenterY, insideRect} from './dom.js';
import {t} from './i18n.js';

export function initDecks({confirmDelete, errText, openDeckCards}) {
  const deckEditSheet = $('#deck-edit');
  const deckForm = $('#deck-form');
  const deckNameField = $('#deck-form [name=name]');
  const deckFolderField = $('#deck-folder');
  const deckMsg = $('#deck-msg');
  const deckListMsg = $('#deck-list-msg');
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

  const openDeckEdit = deck => {
    const currentDeck = deckData(deck);
    deckNameField.value = currentDeck.name;
    deckMsg.textContent = '';
    deckForm.new_per_day.value = currentDeck.newPerDay;
    deckForm.paused.value = currentDeck.paused ? '1' : '0';
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
    const response = await fetch('/api/decks/' + deckId, {
      method: 'PUT',
      body: new URLSearchParams(new FormData(deckForm)),
    });

    if (!response.ok) {
      deckMsg.textContent = await errText(response);
      return;
    }

    location.reload();
  };

  deleteDeckButton.onclick = () => {
    // Always the deck shown in this sheet: the card list may point at another deck.
    confirmDelete('deck', {
      id: deckEditSheet.dataset.deckId,
      name: deckEditSheet.dataset.deckName,
    });
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
      if (event.target.closest('.plus, .star, .learn, select, .pause')) return;
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

  if (!deckGrid) return;

  const applyDeckSettings = (deck, newPerDay, paused) => {
    deck.dataset.newPerDay = String(newPerDay);
    deck.dataset.paused = paused ? '1' : '0';
    deck.classList.toggle('paused', paused);

    const limit = deck.querySelector('.daily-limit');
    if (limit) limit.value = String(newPerDay);

    const pause = deck.querySelector('.pause');
    if (pause) {
      pause.setAttribute('aria-pressed', paused ? 'true' : 'false');
      pause.setAttribute('aria-label', `${paused ? t('deck.resume') : t('home.pause')}: ${deck.dataset.name}`);
      pause.textContent = paused ? '▶' : '⏸';
    }

    const learn = deck.querySelector('.learn');
    if (learn) learn.disabled = paused || (!Number(deck.dataset.due) && !Number(deck.dataset.new));

    const metaSmall = deck.querySelector('.meta small');
    if (metaSmall) {
      metaSmall.textContent = paused
        ? t('home.folder.paused')
        : t('home.folder.stats', {due: deck.dataset.due, new: deck.dataset.new});
    }
  };

  const saveDeckSettings = async (deck, newPerDay, paused) => {
    const previous = {
      newPerDay: deck.dataset.newPerDay,
      paused: deck.dataset.paused === '1',
    };
    const limit = deck.querySelector('.daily-limit');
    const pause = deck.querySelector('.pause');
    if (limit) limit.disabled = true;
    if (pause) pause.disabled = true;
    deck.setAttribute('aria-busy', 'true');
    if (deckListMsg) deckListMsg.textContent = '';

    let response;
    try {
      response = await fetch('/api/decks/' + deck.dataset.id + '/settings', {
        method: 'POST',
        body: new URLSearchParams({
          new_per_day: String(newPerDay),
          paused: paused ? '1' : '0',
        }),
      });
    } catch {
      applyDeckSettings(deck, previous.newPerDay, previous.paused);
      if (deckListMsg) deckListMsg.textContent = t('common.save_failed_connection');
      if (limit) limit.disabled = false;
      if (pause) pause.disabled = false;
      deck.removeAttribute('aria-busy');
      return;
    }

    if (!response.ok) {
      applyDeckSettings(deck, previous.newPerDay, previous.paused);
      if (deckListMsg) deckListMsg.textContent = await errText(response);
      if (limit) limit.disabled = false;
      if (pause) pause.disabled = false;
      deck.removeAttribute('aria-busy');
      return;
    }

    applyDeckSettings(deck, newPerDay, paused);
    if (limit) limit.disabled = false;
    if (pause) pause.disabled = false;
    deck.removeAttribute('aria-busy');
    document.dispatchEvent(new CustomEvent('dex:home-refresh'));
  };

  deckGrid.addEventListener('change', event => {
    const limit = event.target.closest('.daily-limit');
    if (!limit) return;
    const deck = limit.closest('.deck[data-id]');
    if (!deck) return;
    saveDeckSettings(deck, limit.value, deck.dataset.paused === '1');
  });

  deckGrid.addEventListener('click', event => {
    const pause = event.target.closest('.pause');
    if (!pause) return;
    const deck = pause.closest('.deck[data-id]');
    if (!deck) return;
    event.stopPropagation();
    saveDeckSettings(deck, deck.dataset.newPerDay, deck.dataset.paused !== '1');
  });

  if (!deckGrid.classList.contains('decks-list')) return;

  const HOLD_MS = 400;
  let holdTimer = null;
  let holdPos = null;
  let holdPointer = null;
  let moving = null;
  let dragPointer = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragMoved = false;
  let swallow = false;
  let swallowTimer = null;

  const deckEls = () => [...deckGrid.querySelectorAll('.deck[data-id]')];

  const saveOrder = async () => {
    const body = new URLSearchParams();
    deckEls().forEach(deck => body.append('ids', deck.dataset.id));
    let response;
    try {
      response = await fetch('/api/decks/order', {method: 'POST', body});
    } catch {
      alert(t('deck.order_failed'));
      location.reload();
      return;
    }
    if (!response.ok) {
      alert(t('deck.order_failed'));
      location.reload();
    }
  };

  const exitMove = () => {
    if (!moving) return;
    moving.classList.remove('moving', 'dragging');
    moving = null;
    dragPointer = null;
    dragMoved = false;
  };

  const enterMove = deck => {
    if (moving && moving !== deck) exitMove();
    moving = deck;
    deck.classList.remove('holding');
    deck.classList.add('moving');
    holdTimer = null;
    holdPos = null;
    holdPointer = null;
    clearTimeout(swallowTimer);
    swallow = true;
  };

  const onDragMove = event => {
    if (!moving || event.pointerId !== dragPointer) return;
    if (Math.hypot(event.clientX - dragStartX, event.clientY - dragStartY) > 4) dragMoved = true;
    if (insideRect(moving.getBoundingClientRect(), event.clientX, event.clientY)) return;

    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest('.deck[data-id]');
    const rect = target?.getBoundingClientRect();
    if (!target || target === moving || !rect) return;

    // On a grid, the row tells us which row the drop belongs to; the horizontal
    // half of the target decides the slot. A one-column list uses the vertical
    // half instead.
    const columns = getComputedStyle(deckGrid).gridTemplateColumns.split(' ').length;
    const after = columns > 1
      ? afterCenterX(rect, event.clientX)
      : afterCenterY(rect, event.clientY);
    if (after === null) return;
    if (after) {
      if (moving.previousElementSibling !== target) target.after(moving);
    } else if (moving.nextElementSibling !== target) {
      target.before(moving);
    }
  };

  const endDrag = event => {
    if (event && event.pointerId !== dragPointer) return;
    document.removeEventListener('pointermove', onDragMove);
    document.removeEventListener('pointerup', endDrag);
    document.removeEventListener('pointercancel', endDrag);
    dragPointer = null;
    if (!moving) return;
    moving.classList.remove('dragging');
    const moved = dragMoved;
    swallow = true;
    clearTimeout(swallowTimer);
    swallowTimer = setTimeout(() => { swallow = false; }, 400);
    exitMove();
    if (moved) saveOrder();
  };

  const beginDrag = (pointerId, startX, startY) => {
    if (!moving || dragPointer !== null) return;
    dragPointer = pointerId;
    dragStartX = startX;
    dragStartY = startY;
    dragMoved = false;
    moving.classList.add('dragging');
    document.addEventListener('pointermove', onDragMove);
    document.addEventListener('pointerup', endDrag);
    document.addEventListener('pointercancel', endDrag);
  };

  const cancelHold = deck => {
    clearTimeout(holdTimer);
    holdTimer = null;
    holdPos = null;
    holdPointer = null;
    deck.classList.remove('holding');
  };

  for (const deck of deckEls()) {
    deck.addEventListener('contextmenu', event => event.preventDefault());
    deck.addEventListener('pointerdown', event => {
      if (moving || event.button > 0 || event.target.closest('button,input,select,summary,a')) return;
      holdPos = [event.clientX, event.clientY];
      holdPointer = event.pointerId;
      deck.classList.add('holding');
      holdTimer = setTimeout(() => {
        const pointer = holdPointer;
        const startX = holdPos ? holdPos[0] : event.clientX;
        const startY = holdPos ? holdPos[1] : event.clientY;
        enterMove(deck);
        beginDrag(pointer, startX, startY);
      }, HOLD_MS);
    });
    deck.addEventListener('pointermove', event => {
      if (holdPos && Math.hypot(event.clientX - holdPos[0], event.clientY - holdPos[1]) > 10) cancelHold(deck);
    });
    for (const name of ['pointerup', 'pointercancel']) {
      deck.addEventListener(name, () => {
        if (holdTimer) cancelHold(deck);
      });
    }
    deck.addEventListener('pointerleave', () => {
      if (!moving && holdTimer) cancelHold(deck);
    });
  }

  document.addEventListener('click', event => {
    if (swallow) {
      swallow = false;
      clearTimeout(swallowTimer);
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (!moving) return;
    event.preventDefault();
    event.stopPropagation();
    exitMove();
  }, true);

  addEventListener('keydown', event => {
    if (event.key === 'Escape') exitMove();
  });
}
