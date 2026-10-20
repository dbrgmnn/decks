import {$, TRASH_SVG, el} from './dom.js';
import {t} from './i18n.js';

export function initCards({confirmDelete, errText}) {
  const searchInput = $('#search');
  const listSheet = $('#list');
  const listClose = $('#list .close');
  const listTitle = $('#list-title');
  const wordsList = $('#words');
  const addSheet = $('#add');
  const addClose = $('#add .close');
  const addForm = $('#add-form');
  const addTitle = $('#add-title');
  const addButton = $('#add-btn');
  const addMsg = $('#add-msg');
  const plusButtons = [...document.querySelectorAll('.plus')];

  let curDeck = null;
  let editing = null;
  const cardsByDeck = new Map();

  const getDeckCards = deckId => {
    const cards = cardsByDeck.get(String(deckId));
    return Array.isArray(cards) ? cards : [];
  };

  const setCurrentDeck = deck => {
    curDeck = deck;
  };

  const renderWords = () => {
    if (!curDeck) return;

    const allCards = getDeckCards(curDeck.id);
    const query = searchInput.value.trim().toLowerCase();
    const filteredCards = query.length >= 2
      ? allCards.filter(card => [card.front, card.back].some(text => (text || '').toLowerCase().includes(query)))
      : allCards;

    wordsList.replaceChildren();

    if (!filteredCards.length) {
      const count = allCards.length ? t('cards.range', {shown: 0, total: allCards.length}) : '0';
      listTitle.textContent = `${curDeck.name} (${count})`;
      if (allCards.length && query.length >= 2) wordsList.append(el('li', t('cards.no_matches'), 'empty'));
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const card of filteredCards) {
      const li = el('li');
      li.append(el('b', card.front), el('span', card.back));

      const del = el('button', '', 'delete-card');
      del.type = 'button';
      del.innerHTML = TRASH_SVG;
      del.setAttribute('aria-label', t('cards.delete'));
      del.onclick = event => {
        event.stopPropagation();
        confirmDelete('card', card);
      };

      li.append(del);
      li.onclick = () => openEdit(card);
      fragment.append(li);
    }

    wordsList.append(fragment);
    const count = filteredCards.length === allCards.length
      ? String(filteredCards.length)
      : t('cards.range', {shown: filteredCards.length, total: allCards.length});
    listTitle.textContent = `${curDeck.name} (${count})`;
  };

  const loadWords = async ({force = false} = {}) => {
    if (!curDeck) return;
    if (!force && cardsByDeck.has(String(curDeck.id))) {
      renderWords();
      return;
    }

    let response;
    try {
      response = await fetch(`/api/decks/${curDeck.id}/cards`);
    } catch {
      return;
    }
    // A deck deleted elsewhere answers with an error object, not a list.
    if (!response.ok) return;
    const cards = await response.json();
    if (!Array.isArray(cards)) return;
    cardsByDeck.set(String(curDeck.id), cards);
    renderWords();
  };

  const closeAddSheet = async ({refresh = false} = {}) => {
    addSheet.hidden = true;
    addForm.reset();
    addMsg.textContent = '';
    editing = null;

    if (refresh && curDeck && !listSheet.hidden) {
      cardsByDeck.delete(String(curDeck.id));
      await loadWords({force: true});
    }
  };

  const openDeckCards = async deck => {
    setCurrentDeck(deck);
    searchInput.value = '';
    listSheet.hidden = false;
    await loadWords();
  };

  const openEdit = card => {
    editing = card.id;
    addForm.front.value = card.front;
    addForm.back.value = card.back;
    addForm.note.value = card.note || '';
    addTitle.textContent = t('cards.edit_title');
    addButton.textContent = t('common.save_changes');
    addMsg.textContent = '';
    addSheet.hidden = false;
    addForm.front.focus();
  };

  searchInput.oninput = renderWords;

  plusButtons.forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      const deck = button.closest('.deck');
      setCurrentDeck({id: deck.dataset.id, name: deck.dataset.name});
      editing = null;
      addForm.reset();
      addButton.textContent = t('common.save');
      addTitle.textContent = t('cards.add_to', {deck: curDeck.name});
      addMsg.textContent = '';
      addSheet.hidden = false;
      addForm.front.focus();
    };
  });

  addForm.onsubmit = async event => {
    event.preventDefault();
    const body = new URLSearchParams(new FormData(addForm));
    if (!editing) body.set('deck_id', curDeck.id);

    const response = await fetch(editing ? '/api/cards/' + editing : '/api/cards', {
      method: editing ? 'PUT' : 'POST',
      body,
    });

    if (!response.ok) {
      addMsg.textContent = await errText(response);
      return;
    }

    if (editing) {
      await closeAddSheet({refresh: true});
      return;
    }

    addMsg.textContent = t('common.saved');
    addForm.reset();
    cardsByDeck.delete(String(curDeck.id));
    document.dispatchEvent(new CustomEvent('dex:home-refresh'));
    addForm.front.focus();

    // Keep the list fresh if the current deck is already open.
    if (!listSheet.hidden) await loadWords({force: true});
  };

  listClose.onclick = () => {
    listSheet.hidden = true;
  };

  addClose.onclick = () => {
    closeAddSheet({refresh: !listSheet.hidden});
  };

  return {
    loadWords,
    openDeckCards,
  };
}
