import { state } from '../state.js';
import { api, vibrate } from '../api.js';
import { icon } from '../ui/icons.js';
import { showToast } from '../ui/toast.js';

let pinBuffer = '';
let isSubmitting = false;

export function initLoginScreen(onLoginSuccess) {
  const padContainer = document.getElementById('pinpad-grid');
  const dotsContainer = document.getElementById('pin-dots');
  const statusMsg = document.getElementById('pin-status-msg');
  if (!padContainer || !dotsContainer) return;

  const renderDots = (isError = false) => {
    const count = Math.max(4, pinBuffer.length);
    dotsContainer.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const dot = document.createElement('div');
      dot.className = 'pin-dot';
      if (i < pinBuffer.length) {
        dot.classList.add(isError ? 'error' : 'filled');
      }
      dotsContainer.appendChild(dot);
    }
  };

  const triggerError = (msg = 'Incorrect PIN') => {
    vibrate([40, 50, 40]);
    renderDots(true);
    dotsContainer.classList.remove('shake');
    void dotsContainer.offsetWidth;
    dotsContainer.classList.add('shake');
    if (statusMsg) {
      statusMsg.textContent = msg;
      statusMsg.style.color = 'var(--danger)';
    }
    setTimeout(() => {
      pinBuffer = '';
      renderDots(false);
      if (statusMsg) {
        statusMsg.textContent = 'Enter 4-digit security PIN';
        statusMsg.style.color = 'var(--text-muted)';
      }
    }, 520);
  };

  const submitPin = async () => {
    if (isSubmitting || !pinBuffer.length) return;
    isSubmitting = true;
    if (statusMsg) {
      statusMsg.textContent = 'Connecting…';
      statusMsg.style.color = 'var(--accent-hover)';
    }
    try {
      const res = await api.post('/auth/login', { pin: pinBuffer });
      state.token = res.token;
      state.defaultPin = Boolean(res.default_pin);
      if (res.hostname) state.hostname = res.hostname;
      localStorage.setItem('pc_remote_token', res.token);
      pinBuffer = '';
      renderDots(false);
      if (statusMsg) {
        statusMsg.textContent = 'Enter 4-digit security PIN';
        statusMsg.style.color = 'var(--text-muted)';
      }
      onLoginSuccess();
    } catch (err) {
      triggerError('Invalid PIN code');
    } finally {
      isSubmitting = false;
    }
  };

  const appendDigit = (digit) => {
    if (isSubmitting || pinBuffer.length >= 8) return;
    vibrate(8);
    pinBuffer += String(digit);
    renderDots(false);
    if (pinBuffer.length === 4) {
      submitPin();
    }
  };

  const backspace = () => {
    if (isSubmitting || !pinBuffer.length) return;
    vibrate(6);
    pinBuffer = pinBuffer.slice(0, -1);
    renderDots(false);
  };

  const clearPin = () => {
    if (isSubmitting) return;
    vibrate(10);
    pinBuffer = '';
    renderDots(false);
  };

  // Build 3x4 PIN pad
  const keys = [
    { label: '1', type: 'digit' },
    { label: '2', type: 'digit' },
    { label: '3', type: 'digit' },
    { label: '4', type: 'digit' },
    { label: '5', type: 'digit' },
    { label: '6', type: 'digit' },
    { label: '7', type: 'digit' },
    { label: '8', type: 'digit' },
    { label: '9', type: 'digit' },
    { label: 'Clear', type: 'clear' },
    { label: '0', type: 'digit' },
    { label: 'del', type: 'back' },
  ];

  padContainer.innerHTML = '';
  keys.forEach((k) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    if (k.type === 'digit') {
      btn.className = 'pin-key tabular';
      btn.textContent = k.label;
      btn.onclick = () => appendDigit(k.label);
    } else if (k.type === 'clear') {
      btn.className = 'pin-key action-key';
      btn.textContent = 'Clear';
      btn.onclick = clearPin;
    } else {
      btn.className = 'pin-key action-key';
      btn.setAttribute('aria-label', 'Backspace');
      btn.innerHTML = icon('delete');
      btn.onclick = backspace;
    }
    padContainer.appendChild(btn);
  });

  // Physical keyboard support when auth screen is visible
  window.addEventListener('keydown', (e) => {
    const authEl = document.getElementById('auth-screen');
    if (!authEl || authEl.style.display === 'none') return;
    if (e.key >= '0' && e.key <= '9') {
      appendDigit(e.key);
    } else if (e.key === 'Backspace') {
      backspace();
    } else if (e.key === 'Escape') {
      clearPin();
    } else if (e.key === 'Enter' && pinBuffer.length > 0) {
      submitPin();
    }
  });

  renderDots(false);
}
