import {$} from './dom.js';

export function initPractice() {
  let current = null;
  let deckId = null;
  let shown = false;
  let n = 0;
  let total = 0;
  let sx;
  let sy;

  const clearActiveRating = () => document.querySelectorAll('.rate button').forEach(button => {
    button.classList.remove('active-swipe');
  });
  const previewRating = rating => document.querySelectorAll('.rate button').forEach(button => {
    button.classList.toggle('active-swipe', shown && +button.dataset.r === rating);
  });
  const setRating = on => document.querySelectorAll('.rate button').forEach(button => {
    button.disabled = !on;
    if (!on) button.classList.remove('active-swipe');
  });
  const show = card => {
    current = card;
    shown = false;
    setRating(false);
    if (card) {
      n += 1;
      total = Math.max(total || card.left, n);
    }
    $('#n').textContent = n;
    $('#m').textContent = total;
    $('#front').textContent = card ? card.front : 'All done for today ✓';
    $('#back').textContent = card ? card.back : '';
    $('#note').textContent = card ? card.note : '';
    const badge = $('#card-kind');
    if (card) {
      const isNew = card.kind === 'new';
      badge.hidden = false;
      badge.textContent = isNew ? 'NEW' : 'REVIEW';
      badge.classList.toggle('is-new', isNew);
      badge.classList.toggle('is-review', !isNew);
    } else {
      badge.hidden = true;
      badge.textContent = '';
      badge.classList.remove('is-new', 'is-review');
    }
    $('#back').hidden = true;
    $('#note').hidden = true;
  };

  const next = async () => show(await (await fetch('/api/next/' + deckId)).json());
  const flip = () => {
    if (!current) return;
    shown = true;
    setRating(true);
    $('#back').hidden = false;
    $('#note').hidden = !current.note;
  };
  const rate = async rating => {
    if (!current || !shown) return;
    clearActiveRating();
    await fetch('/api/rate/' + current.id, {method: 'POST', body: new URLSearchParams({rating})});
    next();
  };

  document.querySelectorAll('.learn').forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      deckId = button.dataset.id;
      n = 0;
      total = 0;
      $('#practice').hidden = false;
      next();
    };
  });

  $('#close').onclick = () => {
    clearActiveRating();
    $('#practice').hidden = true;
    location.reload();
  };
  document.querySelectorAll('.rate button').forEach(button => {
    button.onclick = () => rate(+button.dataset.r);
  });

  addEventListener('keydown', event => {
    if ($('#practice').hidden) return;
    const keymap = {1: 1, 2: 2, 3: 3, 4: 4, ArrowLeft: 1, ArrowDown: 2, ArrowRight: 3, ArrowUp: 4};
    const rating = keymap[event.key];
    if (rating) rate(rating);
    else if (event.key === ' ') flip();
    else if (event.key === 'Escape') $('#close').click();
  });

  const card = $('#card');
  card.onpointerdown = event => {
    sx = event.clientX;
    sy = event.clientY;
    card.setPointerCapture(event.pointerId);
  };
  card.onpointermove = event => {
    if (sx == null || !shown) return;
    const dx = event.clientX - sx;
    const dy = event.clientY - sy;
    card.style.transform = `translate(${dx}px,${dy}px)`;
    const distance = Math.hypot(dx, dy);
    if (distance < 80) return clearActiveRating();
    previewRating(Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 1 : 3) : (dy > 0 ? 2 : 4));
  };
  card.onpointerup = event => {
    const dx = event.clientX - sx;
    const dy = event.clientY - sy;
    sx = null;
    sy = null;
    card.style.transform = '';
    clearActiveRating();
    if (Math.hypot(dx, dy) < 10) return flip();
    if (!shown || Math.hypot(dx, dy) < 80) return;
    rate(Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 1 : 3) : (dy > 0 ? 2 : 4));
  };
  card.onpointercancel = () => {
    sx = null;
    sy = null;
    card.style.transform = '';
    clearActiveRating();
  };

  return {rate, flip};
}
