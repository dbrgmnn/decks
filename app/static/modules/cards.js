import {$, TRASH_SVG, el} from './dom.js';
import {t} from './i18n.js';

const SEARCH_DELAY = 250;

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
  let cardsSeq = 0;
  let tagsSeq = 0;
  let searchTimer = null;

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

  const renderTitle = (shown, total) => {
    const count = shown === total ? String(total) : t('cards.range', {shown, total});
    listTitle.textContent = `${curDeck.name} (${count})`;
  };

  const renderWords = (cards, total, query) => {
    if (!curDeck) return;
    wordsList.replaceChildren();

    if (!cards.length) {
      renderTitle(0, total);
      if (total && (query.length >= 2 || activeTag)) {
        wordsList.append(el('li', t('cards.no_matches'), 'empty'));
      }
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const card of cards) {
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
    renderTitle(cards.length, total);
  };

  const fetchCards = async () => {
    if (!curDeck) return;
    const seq = ++cardsSeq;
    const params = new URLSearchParams();
    const query = searchInput.value.trim();
    if (query.length >= 2) params.set('q', query);
    if (activeTag) params.set('tag', activeTag);
    if (!params.has('q') && !params.has('tag')) params.set('recent', '1');

    let response;
    try {
      response = await fetch(`/api/decks/${curDeck.id}/cards?${params}`);
    } catch {
      return;
    }
    if (!response.ok) return;

    const cards = await response.json();
    if (!Array.isArray(cards) || seq !== cardsSeq) return;

    const total = Number(response.headers.get('X-Total-Count'));
    renderWords(cards, Number.isFinite(total) ? total : cards.length, query);
  };

  const loadTags = async () => {
    if (!curDeck || !tagFilter) return [];
    const seq = ++tagsSeq;

    let response;
    try {
      response = await fetch(`/api/decks/${curDeck.id}/tags`);
    } catch {
      return [];
    }
    if (!response.ok) return [];

    const tags = await response.json();
    if (!Array.isArray(tags) || seq !== tagsSeq) return [];

    if (activeTag) {
      const match = tags.find(tag => tag.toLocaleLowerCase() === activeTag.toLocaleLowerCase());
      activeTag = match || '';
    }

    // Rebuild only when the tag set changes, so an open menu is not replaced
    // while the search field is being typed into.
    const signature = tags.join('\u0000');
    if (tagFilter.dataset.tags !== signature) {
      tagFilter.dataset.tags = signature;
      const options = [new Option(t('home.recent'), '')];
      for (const tag of tags) options.push(new Option(tag, tag));
      tagFilter.replaceChildren(...options);
    }
    tagFilter.value = activeTag;
    tagFilter.hidden = tags.length === 0;
    return tags;
  };

  const refreshList = async () => {
    if (!curDeck) return;
    await loadTags();
    await fetchCards();
  };

  const closeAddSheet = async ({refresh = false} = {}) => {
    addSheet.hidden = true;
    addForm.reset();
    addMsg.textContent = '';
    editing = null;

    if (refresh && curDeck && !listSheet.hidden) {
      await refreshList();
    }
  };

  const openDeckCards = async deck => {
    setCurrentDeck(deck);
    activeTag = '';
    searchInput.value = '';
    wordsList.replaceChildren();
    listTitle.textContent = deck.name;
    listSheet.hidden = false;
    await refreshList();
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

  searchInput.oninput = () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(fetchCards, SEARCH_DELAY);
  };

  if (tagFilter) {
    tagFilter.onchange = () => {
      activeTag = tagFilter.value;
      fetchCards();
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
    document.dispatchEvent(new CustomEvent('dex:home-refresh'));
    addForm.front.focus();

    // Keep the list fresh if the current deck is already open.
    if (!listSheet.hidden) await refreshList();
  };

  listClose.onclick = () => {
    listSheet.hidden = true;
  };

  addClose.onclick = () => {
    closeAddSheet({refresh: !listSheet.hidden});
  };

  return {
    refreshList,
    openDeckCards,
  };
}
