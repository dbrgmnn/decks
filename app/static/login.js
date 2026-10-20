import {$, errText, syncThemeColor} from './modules/dom.js';
import {t} from './modules/i18n.js';
import {initServiceWorker} from './modules/pwa.js';
import {initTouchFeedback} from './modules/touch.js';
import {initPasswordToggles, resetPassword} from './modules/password.js';

syncThemeColor();
initServiceWorker();
initTouchFeedback();
initPasswordToggles();

const form = $('#auth-form');
const submitButton = $('#submit');
const switchButton = $('#switch');
const message = $('#msg');
const passwordField = form.password.closest('.password-field');
const password2Field = form.password2.closest('.password-field');

let signup = false;

const setMode = on => {
  signup = on;
  form.reset();
  resetPassword(passwordField);
  resetPassword(password2Field);
  password2Field.hidden = !on;
  form.password2.required = on;
  form.password2.disabled = !on;
  form.password.autocomplete = on ? 'new-password' : 'current-password';
  form.password2.autocomplete = 'new-password';
  submitButton.textContent = on ? t('login.create_account') : t('login.sign_in');
  switchButton.textContent = on ? t('login.have_account') : t('login.create_account');
  message.textContent = '';
};

switchButton.onclick = () => setMode(!signup);
setMode(false);

form.onsubmit = async event => {
  event.preventDefault();

  if (signup && form.password.value !== form.password2.value) {
    message.textContent = t('common.passwords_mismatch');
    return;
  }

  submitButton.disabled = true;
  const body = new URLSearchParams(new FormData(form));
  body.set('tz', Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');

  const response = await fetch(signup ? '/api/signup' : '/api/login', {
    method: 'POST',
    body,
  });

  submitButton.disabled = false;
  if (response.ok) {
    location.href = '/';
  } else {
    message.textContent = await errText(response);
  }
};
