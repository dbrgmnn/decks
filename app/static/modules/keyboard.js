// iPhone: with the on-screen keyboard up the visual viewport shrinks while fixed
// elements keep their layout position, so a bottom bar would float mid-screen.
// Mark the document so CSS can hide the study bar until the field loses focus.
const FIELDS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

export function initKeyboardHints() {
  const sync = () => {
    const tag = document.activeElement?.tagName;
    document.documentElement.classList.toggle('typing', FIELDS.has(tag));
  };

  document.addEventListener('focusin', sync);
  // focusout fires before document.activeElement moves on to the next element.
  document.addEventListener('focusout', () => setTimeout(sync, 0));
}
