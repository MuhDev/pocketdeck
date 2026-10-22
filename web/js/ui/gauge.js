export function updateStatWidget(metric, value, historyArray) {
  const pct = Math.max(0, Math.min(100, Math.round(Number(value) || 0)));

  const valEl = document.getElementById(`stat-${metric}`);
  const barEl = document.getElementById(`stat-bar-${metric}`);
  const cardEl = document.getElementById(`stat-card-${metric}`);

  if (valEl) {
    valEl.textContent = `${pct}%`;
  }

  if (barEl) {
    barEl.style.width = `${pct}%`;
  }

  if (cardEl) {
    if (pct >= 90) {
      cardEl.classList.add('is-danger');
      cardEl.classList.remove('is-warn');
    } else if (pct >= 75) {
      cardEl.classList.add('is-warn');
      cardEl.classList.remove('is-danger');
    } else {
      cardEl.classList.remove('is-danger', 'is-warn');
    }
  }
}
