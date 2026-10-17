// Haptic feedback.
//
// Android exposes navigator.vibrate(). iOS never did, and since iOS 26.5 Apple
// also blocked the old programmatic trick — only a *real, physical tap* on an
// <input type="checkbox" switch> ticks the Taptic Engine. So for iOS tap targets
// we lay a transparent native switch over the control so the finger hits it
// directly (verified approach: github.com/m1ckc3s/project-fathom).
const STORAGE_KEY = 'decks.haptics';
const PATTERNS = {
  light: 12,
  medium: 22,
  heavy: 35,
  success: [15, 45, 25],
  warning: [25, 60, 25],
};

let enabled = readEnabled();
const overlays = new Set();

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
const isIOS = () => typeof navigator !== 'undefined' && (
  /iPad|iPhone|iPod/.test(navigator.userAgent)
  || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
);

const patternFor = kind => PATTERNS[kind] ?? PATTERNS.light;

function syncOverlays() {
  for (const overlay of overlays) overlay.style.pointerEvents = enabled ? '' : 'none';
}

// Best effort for gestures we cannot overlay (card swipe) and the Android path.
export function haptic(kind = 'light') {
  if (!enabled || !hasVibration()) return;
  navigator.vibrate(patternFor(kind));
}

// Wire a real-tap haptic onto a control. No-op on platforms without haptics.
export function hapticTap(element, kind = 'light') {
  if (!element || element.dataset.hapticBound) return;
  element.dataset.hapticBound = '1';

  if (hasVibration()) {
    element.addEventListener('pointerdown', () => haptic(kind), {passive: true});
    return;
  }

  if (!isIOS() || !isTouch()) return;

  const overlay = document.createElement('input');
  overlay.type = 'checkbox';
  overlay.setAttribute('switch', '');
  overlay.setAttribute('aria-hidden', 'true');
  overlay.tabIndex = -1;
  overlay.className = 'haptic-switch';

  if (getComputedStyle(element).position === 'static') element.style.position = 'relative';
  element.append(overlay);
  overlays.add(overlay);
  syncOverlays();
}

export const hapticsEnabled = () => enabled;

export function setHapticsEnabled(value) {
  enabled = !!value;
  storeEnabled(enabled);
  syncOverlays();
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
