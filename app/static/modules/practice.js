import {$, el} from './dom.js';
import {t} from './i18n.js';
import {
  canSpeak,
  detectSpeechLanguage,
  resetSpeechLanguage,
  speakText,
  speechLanguageFor,
  stopSpeaking,
} from './speech.js';

export function initPractice() {
  const practiceSheet = $('#practice');
  const closeButton = $('#close');
  const card = $('#card');
  const front = $('#front');
  const frontText = $('#front-text');
  const back = $('#back');
  const speakButton = $('#speak');
  const note = $('#note');
  const summary = $('#summary');
  const message = $('#practice-msg');
  const badge = $('#card-kind');
  const counterCurrent = $('#n');
  const counterTotal = $('#m');
  const ratingButtons = [...document.querySelectorAll('.rate button')];
  const learnButtons = [...document.querySelectorAll('.learn')];
  const studyEnabledButton = $('#study-enabled');
  const main = document.querySelector('main.wrap');

  const ratingLabel = rating => t(`practice.rating.${rating}`);

  if (speakButton && !canSpeak()) speakButton.hidden = true;

  let current = null;
  let deckId = null;
  let shown = false;
  let n = 0;
  let total = 0;
  let startX = null;
  let startY = null;
  let seq = 0;
  let session = null;
  const deckLanguages = new Map();
  const requestedDecks = new Set();

  const requestDeckLanguage = id => {
    const key = Number(id);
    if (!Number.isInteger(key) || key <= 0 || requestedDecks.has(key)) return;
    requestedDecks.add(key);
    fetch('/api/decks/' + key + '/cards')
      .then(response => (response.ok ? response.json() : null))
      .then(cards => {
        if (!Array.isArray(cards) || !cards.length) return;
        const sample = cards.slice(0, 100).map(card => card.front).join(' ');
        const lang = detectSpeechLanguage(sample);
        if (lang) deckLanguages.set(key, lang);
      })
      .catch(() => requestedDecks.delete(key));
  };

  const startStats = () => {
    session = {start: Date.now(), ratings: {1: 0, 2: 0, 3: 0, 4: 0}, fresh: 0, reviews: 0};
  };

  const recordRating = (rating, kind) => {
    if (!session) return;
    session.ratings[rating] += 1;
    if (kind === 'new') session.fresh += 1;
    else session.reviews += 1;
  };

  const formatDuration = ms => {
    const secs = Math.max(1, Math.round(ms / 1000));
    if (secs < 60) return t('practice.duration_seconds', {seconds: secs});
    return t('practice.duration_minutes', {
      minutes: Math.floor(secs / 60),
      seconds: String(secs % 60).padStart(2, '0'),
    });
  };

  const renderSummary = () => {
    const stats = session || {start: Date.now(), ratings: {1: 0, 2: 0, 3: 0, 4: 0}, fresh: 0, reviews: 0};
    const rated = stats.ratings[1] + stats.ratings[2] + stats.ratings[3] + stats.ratings[4];
    const recall = rated ? Math.round(((stats.ratings[3] + stats.ratings[4]) / rated) * 100) : 0;

    const grid = el('dl', '', 'summary-grid');
    for (const [label, value] of [
      [t('practice.due'), String(stats.reviews)],
      [t('practice.new_cards'), String(stats.fresh)],
      [t('practice.time'), formatDuration(Date.now() - stats.start)],
      [t('practice.recall'), `${recall}%`],
    ]) {
      const cell = el('div');
      cell.append(el('dt', label), el('dd', value));
      grid.append(cell);
    }

    const bars = el('div', '', 'summary-bars');
    const legend = el('div', '', 'summary-legend');
    for (const rating of [1, 2, 3, 4]) {
      const count = stats.ratings[rating];
      if (!count) continue;
      const segment = el('span', '', 'summary-segment');
      segment.dataset.r = String(rating);
      segment.style.flexGrow = String(count);
      segment.title = `${ratingLabel(rating)}: ${count}`;
      bars.append(segment);
      legend.append(el('span', `${ratingLabel(rating)} ${count}`));
    }

    summary.replaceChildren(grid, ...(rated ? [bars, legend] : []));
  };

  const clearActiveRating = () => {
    ratingButtons.forEach(button => button.classList.remove('active-swipe'));
  };

  const stopSpeech = () => {
    stopSpeaking();
    if (speakButton) speakButton.classList.remove('speaking');
  };

  const showError = text => {
    message.textContent = text;
    message.hidden = false;
  };

  const clearError = () => {
    message.hidden = true;
    message.textContent = '';
  };

  const previewRating = rating => {
    ratingButtons.forEach(button => {
      button.classList.toggle('active-swipe', shown && Number(button.dataset.r) === rating);
    });
  };

  const setRatingEnabled = enabled => {
    ratingButtons.forEach(button => {
      button.disabled = !enabled;
      if (!enabled) button.classList.remove('active-swipe');
    });
  };

  const resetCardTransform = () => {
    startX = null;
    startY = null;
    card.style.transform = '';
    clearActiveRating();
  };

  const closePractice = () => {
    seq += 1;
    current = null;
    shown = false;
    stopSpeech();
    setRatingEnabled(false);
    resetCardTransform();
    clearError();
    practiceSheet.hidden = true;
    document.dispatchEvent(new CustomEvent('dex:practice-closed'));
  };

  const getSwipeRating = (dx, dy) => (
    Math.abs(dx) > Math.abs(dy)
      ? (dx < 0 ? 1 : 3)
      : (dy > 0 ? 2 : 4)
  );

  const updateCounter = left => {
    total = Math.max(n, n + left);
    counterCurrent.textContent = n;
    counterTotal.textContent = total;
  };

  const show = cardData => {
    stopSpeech();
    current = cardData;
    shown = false;
    setRatingEnabled(false);
    if (cardData) requestDeckLanguage(cardData.deck_id);

    if (cardData) n += 1;

    updateCounter(cardData ? Math.max(0, Number(cardData.left || 0) - 1) : 0);

    if (cardData) {
      summary.hidden = true;
      front.hidden = false;
      frontText.textContent = cardData.front;
      back.textContent = cardData.back;
      note.textContent = cardData.note;
      if (speakButton) speakButton.hidden = true;
      const isNew = cardData.kind === 'new';
      badge.hidden = false;
      badge.textContent = isNew ? t('practice.badge_new') : t('practice.badge_review');
      if (speakButton) {
        speakButton.setAttribute('aria-label', t('practice.pronounce', {front: cardData.front}));
        speakButton.title = t('practice.pronounce', {front: cardData.front});
      }
    } else {
      front.hidden = true;
      badge.hidden = true;
      badge.textContent = '';
      renderSummary();
      summary.hidden = false;
    }

    back.hidden = true;
    note.hidden = true;
  };

  const next = async () => {
    const my = ++seq;
    const path = deckId === 'active' ? '/api/next/active' : '/api/next/' + deckId;
    let response;
    try {
      response = await fetch(path);
    } catch {
      if (my === seq) showError(t('practice.load_failed'));
      return;
    }
    if (my !== seq) return;
    if (!response.ok) {
      showError(t('practice.load_failed'));
      return;
    }
    clearError();
    show(await response.json());
  };

  const flip = () => {
    if (!current) return;
    shown = true;
    setRatingEnabled(true);
    back.hidden = false;
    note.hidden = !current.note;
    if (speakButton && canSpeak()) speakButton.hidden = false;
  };

  const speakFront = () => {
    if (!canSpeak() || !shown || !current || !current.front) return;
    const deckLanguage = deckLanguages.get(Number(current.deck_id));
    const done = () => speakButton?.classList.remove('speaking');
    speakButton?.classList.add('speaking');
    speakText(current.front, speechLanguageFor(current.front, deckLanguage), done);
  };

  const rate = async rating => {
    if (!current || !shown) return;
    const my = seq;
    const cardId = current.id;
    const kind = current.kind;
    shown = false;
    setRatingEnabled(false);
    clearActiveRating();
    let response;
    try {
      response = await fetch('/api/rate/' + cardId, {method: 'POST', body: new URLSearchParams({rating})});
    } catch {
      if (my === seq) {
        shown = true;
        setRatingEnabled(true);
        showError(t('practice.save_failed_connection'));
      }
      return;
    }
    if (my !== seq) return;
    if (!response.ok) {
      shown = true;
      setRatingEnabled(true);
      showError(t('practice.save_failed'));
      return;
    }
    recordRating(rating, kind);
    await next();
  };

  const startSession = id => {
    seq += 1;
    deckId = id;
    n = 0;
    total = 0;
    current = null;
    shown = false;
    stopSpeech();
    resetSpeechLanguage();
    deckLanguages.clear();
    requestedDecks.clear();
    if (id !== 'active') requestDeckLanguage(id);
    setRatingEnabled(false);
    startStats();
    clearError();
    summary.hidden = true;
    front.hidden = false;
    if (speakButton) speakButton.hidden = true;
    practiceSheet.hidden = false;
    counterCurrent.textContent = '0';
    counterTotal.textContent = id === 'active' && main
      ? String(Number(main.dataset.studyDue || 0) + Number(main.dataset.studyNew || 0))
      : '0';
    next();
  };

  learnButtons.forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      startSession(button.dataset.id);
    };
  });

  if (studyEnabledButton) {
    studyEnabledButton.onclick = () => {
      if (studyEnabledButton.disabled) return;
      startSession('active');
    };
  }

  closeButton.onclick = closePractice;
  ratingButtons.forEach(button => {
    button.onclick = () => rate(Number(button.dataset.r));
  });

  if (speakButton) {
    speakButton.onpointerdown = event => event.stopPropagation();
    speakButton.onpointerup = event => event.stopPropagation();
    speakButton.onclick = event => {
      event.stopPropagation();
      speakFront();
    };
  }

  addEventListener('keydown', event => {
    if (practiceSheet.hidden) return;
    if (event.target === speakButton && event.key === ' ') return;
    const keymap = {1: 1, 2: 2, 3: 3, 4: 4, ArrowLeft: 1, ArrowDown: 2, ArrowRight: 3, ArrowUp: 4};
    const rating = keymap[event.key];
    if (rating) rate(rating);
    else if (event.key === ' ') flip();
    else if (event.key === 'Escape') closeButton.click();
  });

  card.onpointerdown = event => {
    startX = event.clientX;
    startY = event.clientY;
    card.setPointerCapture(event.pointerId);
  };

  card.onpointermove = event => {
    if (startX == null || !shown) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    card.style.transform = `translate(${dx}px,${dy}px)`;
    if (Math.hypot(dx, dy) < 80) {
      clearActiveRating();
      return;
    }
    previewRating(getSwipeRating(dx, dy));
  };

  card.onpointerup = event => {
    if (startX == null) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    const distance = Math.hypot(dx, dy);
    resetCardTransform();
    if (distance >= 80 && shown) return rate(getSwipeRating(dx, dy));
    if (distance >= 10) return;
    if (current) flip();
  };

  card.onpointercancel = resetCardTransform;
}
