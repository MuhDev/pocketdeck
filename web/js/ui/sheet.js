import { icon } from './icons.js';
import { vibrate } from '../api.js';

let currentOnClose = null;

export function initSheet() {
  const backdrop = document.getElementById('sheet-backdrop');
  const sheet = backdrop?.querySelector('.bottom-sheet');
  const dragZone = backdrop?.querySelector('.sheet-drag-zone');
  if (!backdrop || !sheet) return;

  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) {
      closeSheet();
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && backdrop.classList.contains('open')) {
      closeSheet();
    }
  });

  // Emil Kowalski Drag-to-Dismiss with Velocity Tracking
  if (dragZone) {
    let startY = 0;
    let startTime = 0;
    let currentY = 0;
    let isDragging = false;

    const onPointerDown = (e) => {
      if (e.button && e.button !== 0) return;
      isDragging = true;
      startY = e.clientY;
      currentY = e.clientY;
      startTime = performance.now();
      sheet.style.transition = 'none';
      dragZone.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e) => {
      if (!isDragging) return;
      currentY = e.clientY;
      const deltaY = currentY - startY;
      if (deltaY > 0) {
        // Dragging downwards
        sheet.style.transform = `translateY(${deltaY}px)`;
      } else {
        // Upward pull - apply rubber-band resistance
        const damped = deltaY * 0.25;
        sheet.style.transform = `translateY(${damped}px)`;
      }
    };

    const onPointerUp = (e) => {
      if (!isDragging) return;
      isDragging = false;
      const deltaY = currentY - startY;
      const elapsed = Math.max(1, performance.now() - startTime);
      const velocity = deltaY / elapsed; // px per ms
      const sheetHeight = sheet.offsetHeight || 300;

      sheet.style.transition = '';

      if (velocity > 0.11 || deltaY > sheetHeight * 0.35) {
        // Dismiss with momentum
        closeSheet();
      } else {
        // Snap back
        sheet.style.transform = '';
      }
    };

    dragZone.addEventListener('pointerdown', onPointerDown);
    dragZone.addEventListener('pointermove', onPointerMove);
    dragZone.addEventListener('pointerup', onPointerUp);
    dragZone.addEventListener('pointercancel', onPointerUp);
  }
}

export function openSheet({ title, renderBody, onClose = null }) {
  const backdrop = document.getElementById('sheet-backdrop');
  const sheet = backdrop?.querySelector('.bottom-sheet');
  const titleEl = document.getElementById('sheet-title');
  const bodyEl = document.getElementById('sheet-body');
  const closeBtn = document.getElementById('sheet-close-btn');
  if (!backdrop || !titleEl || !bodyEl || !sheet) return;

  sheet.style.transform = '';
  sheet.style.transition = '';
  currentOnClose = onClose;
  titleEl.textContent = title || '';
  bodyEl.innerHTML = '';

  if (closeBtn) {
    closeBtn.innerHTML = icon('x');
    closeBtn.onclick = () => closeSheet();
  }

  if (typeof renderBody === 'function') {
    renderBody(bodyEl);
  }

  vibrate(8);
  backdrop.classList.add('open');
}

export function closeSheet() {
  const backdrop = document.getElementById('sheet-backdrop');
  const sheet = backdrop?.querySelector('.bottom-sheet');
  if (!backdrop) return;

  if (sheet) {
    sheet.style.transform = '';
  }
  backdrop.classList.remove('open');

  if (typeof currentOnClose === 'function') {
    const fn = currentOnClose;
    currentOnClose = null;
    fn();
  }
}
