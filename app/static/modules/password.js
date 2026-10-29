// Show/hide control shared by every password field.

import {t} from './i18n.js';

const togglePassword = button => {
  const field = button.closest('.password-field');
  const input = field?.querySelector('input');
  if (!input) return;

  const visible = input.type === 'text';
  input.type = visible ? 'password' : 'text';
  button.setAttribute('aria-pressed', String(!visible));
  button.setAttribute('aria-label', visible ? t('password.show') : t('password.hide'));
  field.querySelector('.eye-open')?.toggleAttribute('hidden', !visible);
  field.querySelector('.eye-closed')?.toggleAttribute('hidden', visible);
};

export const resetPassword = field => {
  const input = field?.querySelector('input');
  const button = field?.querySelector('.password-toggle');
  if (!input || !button) return;

  input.type = 'password';
  button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', t('password.show'));
  field.querySelector('.eye-open')?.removeAttribute('hidden');
  field.querySelector('.eye-closed')?.setAttribute('hidden', '');
};

// One delegated listener covers every current and future password toggle.
export const initPasswordToggles = () => {
  document.addEventListener('click', event => {
    const button = event.target.closest('.password-toggle');
    if (button) togglePassword(button);
  });
};
