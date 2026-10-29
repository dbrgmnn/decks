import {$, TRASH_SVG, el} from './dom.js';
import {t} from './i18n.js';

export function initCards({confirmDelete, errText}) {
  const searchInput = $('#search');
  const listSheet = $('#list');
  const listClose = $('#list .close');
  const listTitle = $('#list-title');
  const tagFilter = $('#tag-filter');
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
  let activeTag = '';
  const cardsByDeck = new Map();

  const getDeckCards = deckId => {
    const cards = cardsByDeck.get(String(deckId));
    return Array.isArray(cards) ? cards : [];
  };

  const setCurrentDeck = deck => {
    curDeck = deck;
  };

  const cardTags = card => (Array.isArray(card.tags) ? card.tags : []);

  const splitTags = value => {
    const tags = [];
    const seen = new Set();
    for (const part of value.split(/[,;]/)) {
      const tag = part.trim();
      const key = tag.toLocaleLowerCase();
      if (!tag || seen.has(key)) continue;
      seen.add(key);
      tags.push(tag);
    }
    return tags;
  };

  const renderTagFilter = allCards => {
    if (!tagFilter) return;

    const tags = [];
    const seen = new Set();
    for (const card of allCards) {
      for (const tag of cardTags(card)) {
        const key = tag.toLocaleLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        tags.push(tag);
      }
    }
    tags.sort((a, b) => a.localeCompare(b));

    if (activeTag && !seen.has(activeTag.toLocaleLowerCase())) activeTag = '';
    tagFilter.hidden = tags.length === 0;

    // Rebuild only when the tag set changes, so an open menu is not replaced
    // while the search field is being typed into.
    const signature = tags.join('\u0000');
    if (tagFilter.dataset.tags !== signature) {
      tagFilter.dataset.tags = signature;
      const options = [new Option(t('home.all_tags'), '')];
      for (const tag of tags) options.push(new Option(tag, tag));
      tagFilter.replaceChildren(...options);
    }
    tagFilter.value = activeTag;
  };

  const renderWords = () => {
    if (!curDeck) return;

    const allCards = getDeckCards(curDeck.id);
    renderTagFilter(allCards);

    const query = searchInput.value.trim().toLowerCase();
    const tagKey = activeTag.toLocaleLowerCase();
    const filteredCards = allCards.filter(card => {
      if (tagKey && !cardTags(card).some(tag => tag.toLocaleLowerCase() === tagKey)) return false;
      if (query.length < 2) return true;
      return [card.front, card.back].some(text => (text || '').toLowerCase().includes(query));
    });

    wordsList.replaceChildren();

    if (!filteredCards.length) {
      const count = allCards.length ? t('cards.range', {shown: 0, total: allCards.length}) : '0';
      listTitle.textContent = `${curDeck.name} (${count})`;
      if (allCards.length && (query.length >= 2 || activeTag)) {
        wordsList.append(el('li', t('cards.no_matches'), 'empty'));
      }
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
    activeTag = '';
    searchInput.value = '';
    listSheet.hidden = false;
    await loadWords();
  };

  const openEdit = card => {
    editing = card.id;
    addForm.front.value = card.front;
    addForm.back.value = card.back;
    addForm.tags.value = cardTags(card).join(', ');
    addForm.note.value = card.note || '';
    addTitle.textContent = t('cards.edit_title');
    addButton.textContent = t('common.save_changes');
    addMsg.textContent = '';
    addSheet.hidden = false;
    addForm.front.focus();
  };

  searchInput.oninput = renderWords;
  if (tagFilter) {
    tagFilter.onchange = () => {
      activeTag = tagFilter.value;
      renderWords();
    };
  }

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

    const payload = {
      front: addForm.front.value,
      back: addForm.back.value,
      note: addForm.note.value,
      tags: splitTags(addForm.tags.value),
    };
    if (!editing) payload.deck_id = Number(curDeck.id);

    const response = await fetch(editing ? '/api/cards/' + editing : '/api/cards', {
      method: editing ? 'PUT' : 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      addMsg.textContent = await errText(response);
      return;
    }

    const data = await response.json();

    if (editing) {
      await closeAddSheet({refresh: true});
      return;
    }

    if (!data.card?.created) {
      addMsg.textContent = t('error.card_exists');
      addForm.front.focus();
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
