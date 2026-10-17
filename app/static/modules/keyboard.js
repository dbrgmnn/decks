// With an on-screen keyboard up the visual viewport shrinks while fixed elements
// keep their layout position, so a bottom bar would float mid-screen. Mark the
// document only while the viewport is actually shrunk: a focused field with no
// keyboard (desktop, or a tablet with a hardware keyboard) keeps the bar.
const KEYBOARD_MIN = 100; // px of shrink that counts as an on-screen keyboard

export function initKeyboardHints() {
  const viewport = window.visualViewport;
  if (!viewport) return;

  const sync = () => {
    const shrunk = window.innerHeight - viewport.height > KEYBOARD_MIN;
    document.documentElement.classList.toggle('typing', shrunk);
  };

  viewport.addEventListener('resize', sync);
  viewport.addEventListener('scroll', sync);
  sync();
}
