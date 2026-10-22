import { state } from '../state.js';
import { api, vibrate } from '../api.js';
import { showToast } from '../ui/toast.js';

export function attachDragSort(container, onOrderChanged) {
  let draggingEl = null;
  let pointerId = null;
  let startX = 0;
  let startY = 0;
  let hasMoved = false;

  container.addEventListener('pointerdown', (e) => {
    if (!state.editMode) return;
    if (e.target.closest('.key-delete-badge')) return;
    const keyEl = e.target.closest('.deck-key[data-preset-id]');
    if (!keyEl) return;

    draggingEl = keyEl;
    pointerId = e.pointerId;
    startX = e.clientX;
    startY = e.clientY;
    hasMoved = false;
  });

  container.addEventListener('pointermove', (e) => {
    if (!draggingEl || e.pointerId !== pointerId || !state.editMode) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (!hasMoved && Math.hypot(dx, dy) > 10) {
      hasMoved = true;
      draggingEl.classList.add('dragging');
      draggingEl.dataset.wasDragged = '1';
      vibrate(12);
    }
    if (!hasMoved) return;

    const target = document.elementFromPoint(e.clientX, e.clientY);
    const overKey = target ? target.closest('.deck-key[data-preset-id]') : null;
    if (overKey && overKey !== draggingEl && overKey.parentElement === container) {
      const children = Array.from(container.querySelectorAll('.deck-key[data-preset-id]'));
      const fromIdx = children.indexOf(draggingEl);
      const toIdx = children.indexOf(overKey);
      if (fromIdx !== -1 && toIdx !== -1) {
        // FLIP Animation: Record First positions of siblings
        const firstPositions = new Map();
        children.forEach((node) => {
          if (node !== draggingEl) {
            firstPositions.set(node, node.getBoundingClientRect());
          }
        });

        // DOM Swap
        if (fromIdx < toIdx) {
          container.insertBefore(draggingEl, overKey.nextSibling);
        } else {
          container.insertBefore(draggingEl, overKey);
        }
        vibrate(6);

        // FLIP Animation: Invert & Play for siblings
        children.forEach((node) => {
          if (node !== draggingEl && firstPositions.has(node)) {
            const first = firstPositions.get(node);
            const last = node.getBoundingClientRect();
            const invX = first.left - last.left;
            const invY = first.top - last.top;
            if (invX !== 0 || invY !== 0) {
              node.style.transform = `translate(${invX}px, ${invY}px)`;
              node.style.transition = 'none';
              requestAnimationFrame(() => {
                node.style.transition = 'transform 220ms cubic-bezier(0.23, 1, 0.32, 1)';
                node.style.transform = '';
              });
            }
          }
        });
      }
    }
  });

  const finishDrag = async () => {
    if (!draggingEl) return;
    const el = draggingEl;
    const didMove = hasMoved;
    draggingEl = null;
    pointerId = null;
    hasMoved = false;

    el.classList.remove('dragging');
    if (!didMove) return;

    setTimeout(() => {
      delete el.dataset.wasDragged;
    }, 80);

    const newIds = Array.from(container.querySelectorAll('.deck-key[data-preset-id]')).map(
      (node) => node.dataset.presetId
    );
    const byId = Object.fromEntries(state.presets.map((p) => [p.id, p]));
    state.presets = newIds.map((id) => byId[id]).filter(Boolean);

    try {
      const res = await api.put('/apps/order', { ids: newIds });
      if (res && res.presets) {
        state.presets = res.presets;
      }
      if (typeof onOrderChanged === 'function') onOrderChanged();
    } catch (err) {
      showToast('Failed to save key order', { type: 'error' });
    }
  };

  container.addEventListener('pointerup', finishDrag);
  container.addEventListener('pointercancel', finishDrag);
}
