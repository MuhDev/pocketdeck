import { state } from '../state.js';
import { api } from '../api.js';
import { icon } from '../ui/icons.js';

const appVolTimeouts = {};

export function initMixerScreen() {
  const refreshBtn = document.getElementById('btn-refresh-mixer');
  if (refreshBtn) {
    refreshBtn.onclick = () => fetchAppVolumes();
  }
}

export async function fetchAppVolumes() {
  try {
    const data = await api.get('/audio/sessions');
    state.audioSessions = data.sessions || [];
    renderAppVolumes(state.audioSessions);
  } catch (_) {}
}

export function renderAppVolumes(sessions) {
  const container = document.getElementById('app-volumes-container');
  if (!container) return;

  const validSessions = (sessions || []).filter(
    (s) => s.name && !s.name.toLowerCase().includes('idle')
  );

  if (validSessions.length === 0) {
    container.innerHTML = `
      <div class="empty-state-box">
        ${icon('sliders-horizontal')}
        <div style="font-weight:700; color:var(--text-secondary);">No Active Audio Streams</div>
        <div style="font-size:12px;">Apps playing sound on your PC will appear here automatically.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = '';

  validSessions.forEach((session) => {
    const row = document.createElement('div');
    row.className = `mixer-row ${session.muted ? 'is-muted' : ''}`;
    row.style.setProperty('--row-accent', session.accent || 'var(--accent)');

    const cleanName = session.name.replace(/\.exe$/i, '');
    const iconUrl = session.icon_url || `/api/icons/process/${encodeURIComponent(cleanName)}`;

    row.innerHTML = `
      <img class="mixer-app-icon" src="${iconUrl}" alt="" loading="lazy">
      <div class="mixer-middle">
        <div class="mixer-top-line">
          <span class="mixer-app-name"></span>
          <span class="mixer-pct tabular">${session.muted ? 'Muted' : `${session.level}%`}</span>
        </div>
        <input
          type="range"
          class="pro-slider ${session.muted ? 'is-muted' : ''}"
          min="0"
          max="100"
          value="${session.level}"
          style="--fill-pct: ${session.level}%; --slider-color: ${session.accent || 'var(--accent)'};"
        >
      </div>
      <button type="button" class="icon-pill-btn ${session.muted ? 'muted' : ''}" aria-label="Toggle Mute">
        ${icon(session.muted ? 'volume-x' : session.level < 35 ? 'volume-1' : 'volume-2')}
      </button>
    `;

    row.querySelector('.mixer-app-name').textContent = cleanName;

    const slider = row.querySelector('.pro-slider');
    const pctLabel = row.querySelector('.mixer-pct');
    const muteBtn = row.querySelector('.icon-pill-btn');

    slider.oninput = (e) => {
      const level = parseInt(e.target.value, 10) || 0;
      session.level = level;
      slider.style.setProperty('--fill-pct', `${level}%`);
      if (!session.muted) {
        pctLabel.textContent = `${level}%`;
      }
      clearTimeout(appVolTimeouts[session.id]);
      appVolTimeouts[session.id] = setTimeout(() => {
        api.post(`/audio/sessions/${encodeURIComponent(session.id)}/volume`, { level }).catch(() => {});
      }, 45);
    };

    muteBtn.onclick = async () => {
      try {
        const res = await api.post(`/audio/sessions/${encodeURIComponent(session.id)}/mute`);
        if (res && typeof res.muted === 'boolean') {
          session.muted = res.muted;
        } else {
          session.muted = !session.muted;
        }
        renderAppVolumes(validSessions);
      } catch (_) {}
    };

    container.appendChild(row);
  });
}
