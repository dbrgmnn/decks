// Haptic feedback for touch devices.
//
// Android exposes the Vibration API. iOS Safari never shipped it, but Safari
// 17.4+ fires a native Taptic tick whenever an <input type="checkbox" switch>
// is activated — so on iOS we keep one hidden switch around and toggle it from
// inside the user's tap. The pref is client-side only and lives in localStorage.
const STORAGE_KEY = 'decks.haptics';
const PATTERNS = {
  light: 12,
  medium: 22,
  heavy: 35,
  success: [15, 45, 25],
  warning: [25, 60, 25],
};

let enabled = readEnabled();
let probe = null;

function readEnabled() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'off';
  } catch {
    return true;
  }
}

function storeEnabled(value) {
  try {
    localStorage.setItem(STORAGE_KEY, value ? 'on' : 'off');
  } catch {
    // Storage can be blocked (private mode); keep the choice for this session.
  }
}

const hasVibration = () => typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function';
const isTouch = () => typeof window !== 'undefined' && (navigator.maxTouchPoints > 0 || 'ontouchstart' in window);

function ensureProbe() {
  if (probe || typeof document === 'undefined') return probe;

  const input = document.createElement('input');
  input.type = 'checkbox';
  input.setAttribute('switch', '');
  input.setAttribute('aria-hidden', 'true');
  input.tabIndex = -1;

  const label = document.createElement('label');
  label.className = 'haptic-probe';
  label.append(input);

  document.body.append(label);
  probe = label;
  return probe;
}

export const hapticsEnabled = () => enabled;

export function setHapticsEnabled(value) {
  enabled = !!value;
  storeEnabled(enabled);
}

// Fire from inside a real tap/click handler — iOS needs that user activation.
export function haptic(kind = 'light') {
  if (!enabled) return;
  const pattern = PATTERNS[kind] ?? PATTERNS.light;

  if (hasVibration()) {
    navigator.vibrate(pattern);
    return;
  }

  if (!isTouch()) return;

  const input = ensureProbe()?.querySelector('input');
  if (!input) return;

  input.click();
  if (Array.isArray(pattern)) setTimeout(() => input.click(), 70);
}

export function initHaptics() {
  const toggle = document.querySelector('#haptics-toggle');
  if (!toggle) return;

  const sync = () => toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  sync();

  toggle.onclick = () => {
    setHapticsEnabled(!enabled);
    sync();
    haptic('light');
  };
}
