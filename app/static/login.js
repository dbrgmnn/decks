import {$, errText} from './modules/dom.js';

const form = $('#auth-form');

const passwordToggle = button => {
  const field = button.closest('.password-field');
  const input = field?.querySelector('input');
  if (!input) return;
  const visible = input.type === 'text';
  input.type = visible ? 'password' : 'text';
  button.setAttribute('aria-pressed', String(!visible));
  button.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
  field.querySelector('.eye-open')?.toggleAttribute('hidden', !visible);
  field.querySelector('.eye-closed')?.toggleAttribute('hidden', visible);
};

const resetPasswordToggle = field => {
  const input = field?.querySelector('input');
  const button = field?.querySelector('.password-toggle');
  if (!input || !button) return;
  input.type = 'password';
  button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', 'Show password');
  field.querySelector('.eye-open')?.removeAttribute('hidden');
  field.querySelector('.eye-closed')?.setAttribute('hidden', '');
};

document.querySelectorAll('.password-toggle').forEach(button => {
  button.addEventListener('click', () => passwordToggle(button));
});

let signup = false;

const setMode = on => {
  signup = on;
  form.reset();
  const password2Field = form.password2.closest('.password-field');
  resetPasswordToggle(form.password.closest('.password-field'));
  resetPasswordToggle(password2Field);
  password2Field.hidden = !on;
  form.password2.required = on;
  form.password2.disabled = !on;
  form.password.autocomplete = on ? 'new-password' : 'current-password';
  form.password2.autocomplete = 'new-password';
  $('#submit').textContent = on ? 'Create account' : 'Sign in';
  $('#switch').textContent = on ? 'I already have an account' : 'Create account';
  $('#msg').textContent = '';
};

$('#switch').onclick = () => setMode(!signup);
setMode(false);

form.onsubmit = async event => {
  event.preventDefault();
  if (signup && form.password.value !== form.password2.value) {
    $('#msg').textContent = 'Passwords do not match';
    return;
  }
  $('#submit').disabled = true;
  const body = new URLSearchParams(new FormData(form));
  body.set('tz', Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const response = await fetch(signup ? '/api/signup' : '/api/login', {method: 'POST', body});
  $('#submit').disabled = false;
  if (response.ok) location.href = '/';
  else $('#msg').textContent = await errText(response);
};
