import {$} from './dom.js';

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

  let current = null;
  let deckId = null;
  let shown = false;
  let n = 0;
  let total = 0;
  let startX = null;
  let startY = null;
  let exitTimer = null;

  const clearActiveRating = () => {
    ratingButtons.forEach(button => button.classList.remove('active-swipe'));
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

  // Keep practice close lightweight: no full page reload.
  const closePractice = () => {
    clearExitTimer();
    current = null;
    shown = false;
    setRatingEnabled(false);
    resetCardTransform();
    practiceSheet.hidden = true;
  };

  const getSwipeRating = (dx, dy) => (
    Math.abs(dx) > Math.abs(dy)
      ? (dx < 0 ? 1 : 3)
      : (dy > 0 ? 2 : 4)
  );

  const show = cardData => {
    clearExitTimer();
    current = cardData;
    shown = false;
    setRatingEnabled(false);

    if (cardData) {
      n += 1;
      total = n + cardData.left - 1;
    }

    counterCurrent.textContent = n;
    counterTotal.textContent = total;
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
    }

    back.hidden = true;
    note.hidden = true;
  };

  const next = async () => {
    const response = await fetch('/api/next/' + deckId);
    show(await response.json());
  };

  const flip = () => {
    if (!current) return;
    shown = true;
    setRatingEnabled(true);
    back.hidden = false;
    note.hidden = !current.note;
  };

  const rate = async rating => {
    if (!current || !shown) return;
    clearActiveRating();
    await fetch('/api/rate/' + current.id, {method: 'POST', body: new URLSearchParams({rating})});
    await next();
  };

  learnButtons.forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      deckId = button.dataset.id;
      n = 0;
      total = 0;
      clearExitTimer();
      practiceSheet.hidden = false;
      next();
    };
  });

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
