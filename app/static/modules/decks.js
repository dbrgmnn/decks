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
  const deckData = deck => ({
    id: deck.dataset.id,
    name: deck.dataset.name,
    newPerDay: deck.dataset.newPerDay,
    paused: deck.dataset.paused === '1',
    folder: deck.dataset.folder,
  });

  const setDeckOpts = (n, paused) => {
    const form = $('#deck-form');
    const toggle = $('#pause-toggle');
    form.new_per_day.value = n;
    form.paused.value = paused ? '1' : '0';
    document.querySelectorAll('#steps button').forEach(button => {
      button.classList.toggle('on', button.dataset.v === String(n));
    });
    toggle.setAttribute('aria-pressed', paused);
    toggle.textContent = paused ? 'Paused' : 'Pause';
  };

  const openDeckEdit = deck => {
    const currentDeck = deckData(deck);
    $('#deck-form [name=name]').value = currentDeck.name;
    $('#deck-msg').textContent = '';
    setDeckOpts(currentDeck.newPerDay, currentDeck.paused);
    if ($('#deck-folder')) $('#deck-folder').value = currentDeck.folder && currentDeck.folder !== '0' ? currentDeck.folder : '';
    $('#deck-edit').dataset.deckId = currentDeck.id;
    $('#deck-edit').dataset.deckName = currentDeck.name;
    $('#deck-edit').hidden = false;
    $('#deck-form [name=name]').focus();
  };

  $('#deck-form').onsubmit = async event => {
    event.preventDefault();
    const deckId = $('#deck-edit').dataset.deckId;
    const response = await fetch('/api/decks/' + deckId, {method: 'PUT', body: new URLSearchParams(new FormData(event.target))});
    if (response.ok) location.reload();
    else $('#deck-msg').textContent = await errText(response);
  };

  $('#delete-deck').onclick = () => {
    const currentDeck = getCurrentDeck() || {
      id: $('#deck-edit').dataset.deckId,
      name: $('#deck-edit').dataset.deckName,
    };
    confirmDelete('deck', currentDeck);
  };

  $('#deck-edit .close').onclick = () => {
    $('#deck-edit').hidden = true;
  };

  if ($('#new-deck')) {
    $('#new-deck').onsubmit = async event => {
      event.preventDefault();
      const response = await fetch('/api/decks', {method: 'POST', body: new URLSearchParams(new FormData(event.target))});
      if (response.ok) location.reload();
      else $('#new-msg').textContent = await errText(response);
    };
  }

  document.querySelectorAll('.deck[data-id]').forEach(deck => {
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

  document.querySelectorAll('.star').forEach(button => {
    button.onclick = async event => {
      event.stopPropagation();
      const on = button.getAttribute('aria-pressed') !== 'true';
      const response = await fetch('/api/decks/' + button.closest('.deck').dataset.id + '/pin', {method: 'POST', body: new URLSearchParams({pinned: on ? 1 : 0})});
      if (response.ok) location.reload();
    };
  });

  document.querySelectorAll('#steps button').forEach(button => {
    button.onclick = () => setDeckOpts(button.dataset.v, $('#deck-form').paused.value === '1');
  });
  $('#pause-toggle').onclick = () => setDeckOpts($('#deck-form').new_per_day.value, $('#deck-form').paused.value !== '1');

  const deckGrid = $('.decks');
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
    if (!response.ok) {
      alert('Could not save deck order.');
      location.reload();
    }
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
