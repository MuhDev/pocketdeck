import { icon } from './icons.js';
import { vibrate } from '../api.js';

let activeToastTimeout = null;

export function showToast(message, options = {}) {
  const {
    type = 'info', // 'info' | 'success' | 'error'
    duration = 2800,
    actionText = null,
    onAction = null,
  } = typeof options === 'number' ? { duration: options } : options;

  const container = document.getElementById('toast-container');
  if (!container) return;

  if (activeToastTimeout) {
    clearTimeout(activeToastTimeout);
    activeToastTimeout = null;
  }

  container.innerHTML = '';

  const bar = document.createElement('div');
  bar.className = `toast-bar ${type === 'error' ? 'toast-error' : ''}`;

  const iconName =
    type === 'error'
      ? 'alert-circle'
      : type === 'success'
      ? 'check-circle-2'
      : 'check-circle-2';

  const left = document.createElement('div');
  left.className = 'toast-left';
  left.innerHTML = `${icon(iconName)}<span></span>`;
  left.querySelector('span').textContent = message;
  bar.appendChild(left);

  if (actionText && typeof onAction === 'function') {
    const btn = document.createElement('button');
    btn.className = 'toast-action-btn';
    btn.textContent = actionText;
    btn.onclick = () => {
      vibrate(12);
      clearTimeout(activeToastTimeout);
      bar.classList.remove('show');
      onAction();
    };
    bar.appendChild(btn);
  }

  container.appendChild(bar);
  requestAnimationFrame(() => {
    bar.classList.add('show');
  });

  activeToastTimeout = setTimeout(() => {
    bar.classList.remove('show');
  }, duration);
}
