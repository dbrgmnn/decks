import {$} from './dom.js';
import {haptic} from './haptics.js';

// Rating 1 gets a double tick ("missed"), 4 a single firm one. 2 and 3 sit between.
const RATE_HAPTIC = {1: 'warning', 2: 'light', 3: 'medium', 4: 'heavy'};

export function initPractice() {
  const practiceSheet = $('#practice');
  const closeButton = $('#close');
  const card = $('#card');
  const front = $('#front');
  const back = $('#back');
  const note = $('#note');
  const badge = $('#card-kind');
  const counterCurrent = $('#n');
  const counterTotal = $('#m');
  const ratingButtons = [...document.querySelectorAll('.rate button')];
  const learnButtons = [...document.querySelectorAll('.learn')];
  const studyEnabledButton = $('#study-enabled');
  const main = document.querySelector('main.wrap');

  let current = null;
  let deckId = null;
  let shown = false;
  let n = 0;
  let total = 0;
  let startX = null;
  let startY = null;
  let exitTimer = null;
  let seq = 0;
  let lastPreview = null;

  const clearActiveRating = () => {
    ratingButtons.forEach(button => button.classList.remove('active-swipe'));
    lastPreview = null;
  };

  const previewRating = rating => {
    ratingButtons.forEach(button => {
      button.classList.toggle('active-swipe', shown && Number(button.dataset.r) === rating);
    });
    if (rating !== lastPreview) {
      lastPreview = rating;
      haptic('light');
    }
  };

  const setRatingEnabled = enabled => {
    ratingButtons.forEach(button => {
      button.disabled = !enabled;
      if (!enabled) button.classList.remove('active-swipe');
    });
  };

  const clearExitTimer = () => {
    if (!exitTimer) return;
    clearTimeout(exitTimer);
    exitTimer = null;
  };

  const resetCardTransform = () => {
    startX = null;
    startY = null;
    card.style.transform = '';
    clearActiveRating();
  };

  const closePractice = () => {
    seq += 1;
    clearExitTimer();
    current = null;
    shown = false;
    setRatingEnabled(false);
    resetCardTransform();
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
    clearExitTimer();
    current = cardData;
    shown = false;
    setRatingEnabled(false);

    if (cardData) n += 1;

    updateCounter(cardData ? Math.max(0, Number(cardData.left || 0) - 1) : 0);
    front.textContent = cardData ? cardData.front : 'All done for today ✓';
    back.textContent = cardData ? cardData.back : '';
    note.textContent = cardData ? cardData.note : '';

    if (cardData) {
      const isNew = cardData.kind === 'new';
      badge.hidden = false;
      badge.textContent = isNew ? 'NEW' : 'REVIEW';
      badge.classList.toggle('is-new', isNew);
      badge.classList.toggle('is-review', !isNew);
    } else {
      badge.hidden = true;
      badge.textContent = '';
      badge.classList.remove('is-new', 'is-review');
      exitTimer = setTimeout(closePractice, 1000);
      haptic('success');
    }

    back.hidden = true;
    note.hidden = true;
  };

  const next = async () => {
    const my = ++seq;
    const path = deckId === 'active' ? '/api/next/active' : '/api/next/' + deckId;
    const response = await fetch(path);
    if (my !== seq) return;
    if (!response.ok) return;
    show(await response.json());
  };

  const flip = () => {
    if (!current) return;
    shown = true;
    setRatingEnabled(true);
    back.hidden = false;
    note.hidden = !current.note;
    haptic('light');
  };

  const rate = async rating => {
    if (!current || !shown) return;
    const my = seq;
    const cardId = current.id;
    shown = false;
    setRatingEnabled(false);
    clearActiveRating();
    haptic(RATE_HAPTIC[rating] || 'medium');
    const response = await fetch('/api/rate/' + cardId, {method: 'POST', body: new URLSearchParams({rating})});
    if (my !== seq) return;
    if (!response.ok) {
      shown = true;
      setRatingEnabled(true);
      return;
    }
    await next();
  };

  const startSession = id => {
    seq += 1;
    deckId = id;
    n = 0;
    total = 0;
    current = null;
    shown = false;
    setRatingEnabled(false);
    clearExitTimer();
    practiceSheet.hidden = false;
    counterCurrent.textContent = '0';
    counterTotal.textContent = id === 'active' && main
      ? String(Number(main.dataset.studyDue || 0) + Number(main.dataset.studyNew || 0))
      : '0';
    haptic('medium');
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

  addEventListener('keydown', event => {
    if (practiceSheet.hidden) return;
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
    if (distance < 10) return flip();
    if (!shown || distance < 80) return;
    rate(getSwipeRating(dx, dy));
  };

  card.onpointercancel = resetCardTransform;

  return {rate, flip};
}
