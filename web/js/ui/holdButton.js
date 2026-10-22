import { icon } from './icons.js';
import { vibrate } from '../api.js';

export function createHoldButton({
  label = 'Hold to Confirm',
  holdingLabel = 'Keep Holding…',
  iconName = 'power',
  durationMs = 1150,
  onConfirm,
}) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'hold-btn';

  btn.innerHTML = `
    <div class="hold-btn-fill"></div>
    <div class="hold-btn-content">
      ${icon(iconName)}
      <span class="hold-btn-text"></span>
    </div>
  `;
  const textEl = btn.querySelector('.hold-btn-text');
  textEl.textContent = label;

  let timerId = null;
  let completed = false;

  const stopHold = () => {
    if (timerId) {
      clearTimeout(timerId);
      timerId = null;
    }
    btn.classList.remove('holding');
    if (!completed) {
      textEl.textContent = label;
    }
  };

  const startHold = (e) => {
    if (e.type === 'mousedown' && e.button !== 0) return;
    e.preventDefault();
    completed = false;
    vibrate(15);
    textEl.textContent = holdingLabel;
    btn.classList.add('holding');

    timerId = setTimeout(() => {
      completed = true;
      vibrate([25, 40, 25]);
      textEl.textContent = 'Confirmed';
      btn.classList.remove('holding');
      if (typeof onConfirm === 'function') {
        onConfirm();
      }
    }, durationMs);
  };

  btn.addEventListener('pointerdown', startHold);
  btn.addEventListener('pointerup', stopHold);
  btn.addEventListener('pointerleave', stopHold);
  btn.addEventListener('pointercancel', stopHold);

  return btn;
}
