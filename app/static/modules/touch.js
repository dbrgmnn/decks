// iOS Safari only starts painting the :active state once the document has seen
// a touch listener, so buttons can look "dead" on the first tap. Register a
// no-op listener to switch that on; it stays passive so scrolling is unaffected.
export function initTouchFeedback() {
  if (typeof window === 'undefined' || !('ontouchstart' in window)) return;

  document.addEventListener('touchstart', () => {}, {passive: true, capture: true});
}
