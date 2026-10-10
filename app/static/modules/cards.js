import {$, TRASH_SVG, el} from './dom.js';

export function initCards({confirmDelete, errText}) {
  let curDeck = null;
  let editing = null;
  let allCards = [];

  const setCurrentDeck = deck => {
    curDeck = deck;
  };

  const openDeckCards = async deck => {
    curDeck = deck;
    $('#search').value = '';
    $('#list').hidden = false;
    await loadWords();
  };

  const openEdit = card => {
    editing = card.id;
    const form = $('#add-form');
    form.front.value = card.front;
    form.back.value = card.back;
    form.note.value = card.note || '';
    $('#add-title').textContent = 'Edit card';
    $('#add-btn').textContent = 'Save changes';
    $('#add-msg').textContent = '';
    $('#add').hidden = false;
    form.front.focus();
  };

  const renderWords = () => {
    const q = $('#search').value.trim().toLowerCase();
    const list = q.length >= 2
      ? allCards.filter(card => [card.front, card.back].some(text => (text || '').toLowerCase().includes(q)))
      : allCards;
    const ul = $('#words');
    ul.replaceChildren();
    if (!list.length) {
      const title = allCards.length ? `${curDeck.name} (0 of ${allCards.length})` : `${curDeck.name} (0)`;
      $('#list-title').textContent = title;
      if (allCards.length && q.length >= 2) ul.append(el('li', 'No matches.', 'empty'));
      return;
    }
    for (const card of list) {
      const li = el('li');
      li.append(el('b', card.front), el('span', card.back));
      const del = el('button', '', 'delete-card');
      del.innerHTML = TRASH_SVG;
      del.setAttribute('aria-label', 'Delete card');
      del.onclick = event => {
        event.stopPropagation();
        confirmDelete('card', card);
      };
      li.append(del);
      li.onclick = () => openEdit(card);
      ul.append(li);
    }
    const count = list.length === allCards.length ? list.length : `${list.length} of ${allCards.length}`;
    $('#list-title').textContent = `${curDeck.name} (${count})`;
  };

  const loadWords = async () => {
    allCards = await (await fetch(`/api/decks/${curDeck.id}/cards`)).json();
    renderWords();
  };

  $('#search').oninput = renderWords;

  document.querySelectorAll('.plus').forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      const deck = button.closest('.deck');
      setCurrentDeck({id: deck.dataset.id, name: deck.dataset.name});
      editing = null;
      $('#add-form').reset();
      $('#add-btn').textContent = 'Save';
      $('#add-title').textContent = 'Add card to ' + curDeck.name;
      $('#add-msg').textContent = '';
      $('#add').hidden = false;
      $('#add-form [name=front]').focus();
    };
  });

  $('#add-form').onsubmit = async event => {
    event.preventDefault();
    const form = event.target;
    const body = new URLSearchParams(new FormData(form));
    if (!editing) body.set('deck_id', curDeck.id);
    const response = await fetch(editing ? '/api/cards/' + editing : '/api/cards', {method: editing ? 'PUT' : 'POST', body});
    if (!response.ok) return $('#add-msg').textContent = await errText(response);
    if (editing) return $('#add .close').click();
    $('#add-msg').textContent = 'Saved ✓';
    form.reset();
    form.front.focus();
  };

  $('#list .close').onclick = () => {
    $('#list').hidden = true;
    location.reload();
  };
  $('#add .close').onclick = () => {
    $('#add').hidden = true;
    editing = null;
    if ($('#list').hidden) location.reload();
    else loadWords();
  };

  return {
    getCurrentDeck: () => curDeck,
    loadWords,
    openDeckCards,
    setCurrentDeck,
  };
}
