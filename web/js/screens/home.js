import { state } from '../state.js';
import { api, vibrate } from '../api.js';
import { icon } from '../ui/icons.js';
import { showToast } from '../ui/toast.js';
import { updateStatWidget } from '../ui/gauge.js';
import { openAddAppSheet } from '../editor/addAppSheet.js';
import { openEditAppSheet } from '../editor/editAppSheet.js';
import { attachDragSort } from '../editor/dragSort.js';

let volDebounceTimer = null;

export function initHomeScreen() {
  const appsContainer = document.getElementById('apps-container');
  const editToggleBtn = document.getElementById('btn-toggle-edit-apps');
  const volSlider = document.getElementById('vol-slider');
  const volMuteBtn = document.getElementById('btn-master-vol-pill');
  const keyDiscordMute = document.getElementById('key-discord-mute');
  const keyDiscordDeafen = document.getElementById('key-discord-deafen');
  const keyMasterMute = document.getElementById('key-master-mute');

  if (appsContainer) {
    attachDragSort(appsContainer, () => renderAppsGrid());
  }

  if (editToggleBtn) {
    editToggleBtn.onclick = () => {
      setEditMode(!state.editMode);
    };
  }

  if (keyDiscordMute) {
    keyDiscordMute.onclick = async () => {
      state.discord.muted = !state.discord.muted;
      renderQuickAudioKeys();
      try {
        await api.post('/discord/mute');
        showToast(state.discord.muted ? 'Discord Mic Muted' : 'Discord Mic Active');
      } catch (_) {}
    };
  }

  if (keyDiscordDeafen) {
    keyDiscordDeafen.onclick = async () => {
      state.discord.deafened = !state.discord.deafened;
      renderQuickAudioKeys();
      try {
        await api.post('/discord/deafen');
        showToast(state.discord.deafened ? 'Discord Deafened' : 'Discord Undeafened');
      } catch (_) {}
    };
  }

  const toggleMasterMuteAction = async () => {
    try {
      const res = await api.post('/audio/mute');
      if (res && typeof res.muted === 'boolean') {
        state.masterAudio.muted = res.muted;
      } else {
        state.masterAudio.muted = !state.masterAudio.muted;
      }
      renderMasterVolumeUI();
      renderQuickAudioKeys();
    } catch (_) {}
  };

  if (keyMasterMute) {
    keyMasterMute.onclick = toggleMasterMuteAction;
  }
  if (volMuteBtn) {
    volMuteBtn.onclick = toggleMasterMuteAction;
  }

  if (volSlider) {
    volSlider.oninput = (e) => {
      const level = parseInt(e.target.value, 10) || 0;
      state.masterAudio.level = level;
      renderMasterVolumeUI(false);
      clearTimeout(volDebounceTimer);
      volDebounceTimer = setTimeout(() => {
        api.post('/audio/volume', { level }).catch(() => {});
      }, 45);
    };
  }

  renderQuickAudioKeys();
  renderMasterVolumeUI();
}

export function setEditMode(enabled) {
  state.editMode = Boolean(enabled);
  vibrate(12);
  const appsContainer = document.getElementById('apps-container');
  const editToggleBtn = document.getElementById('btn-toggle-edit-apps');
  if (appsContainer) {
    appsContainer.classList.toggle('editing', state.editMode);
  }
  if (editToggleBtn) {
    editToggleBtn.innerHTML = state.editMode
      ? `${icon('check')} <span>Done</span>`
      : `${icon('pencil')} <span>Edit</span>`;
  }
}

export function renderQuickAudioKeys() {
  const keyDiscordMute = document.getElementById('key-discord-mute');
  const keyDiscordDeafen = document.getElementById('key-discord-deafen');
  const keyMasterMute = document.getElementById('key-master-mute');

  if (keyDiscordMute) {
    keyDiscordMute.classList.toggle('active-state', state.discord.muted);
    keyDiscordMute.style.setProperty(
      '--key-accent',
      state.discord.muted ? 'var(--danger)' : 'var(--blurple)'
    );
    const vis = keyDiscordMute.querySelector('.key-visual');
    const lbl = keyDiscordMute.querySelector('.key-label');
    if (vis) vis.innerHTML = icon(state.discord.muted ? 'mic-off' : 'mic');
    if (lbl) lbl.textContent = state.discord.muted ? 'Muted' : 'Mic Mute';
  }

  if (keyDiscordDeafen) {
    keyDiscordDeafen.classList.toggle('active-state', state.discord.deafened);
    keyDiscordDeafen.style.setProperty(
      '--key-accent',
      state.discord.deafened ? 'var(--danger)' : 'var(--blurple)'
    );
    const vis = keyDiscordDeafen.querySelector('.key-visual');
    const lbl = keyDiscordDeafen.querySelector('.key-label');
    if (vis) vis.innerHTML = icon(state.discord.deafened ? 'headphone-off' : 'headphones');
    if (lbl) lbl.textContent = state.discord.deafened ? 'Deafened' : 'Deafen';
  }

  if (keyMasterMute) {
    const isMuted = state.masterAudio.muted;
    keyMasterMute.classList.toggle('active-state', isMuted);
    keyMasterMute.style.setProperty(
      '--key-accent',
      isMuted ? 'var(--danger)' : 'var(--accent)'
    );
    const vis = keyMasterMute.querySelector('.key-visual');
    const lbl = keyMasterMute.querySelector('.key-label');
    const sub = keyMasterMute.querySelector('.key-sublabel');
    if (vis) vis.innerHTML = icon(isMuted ? 'volume-x' : 'volume-2');
    if (lbl) lbl.textContent = isMuted ? 'Audio Muted' : 'Master Audio';
    if (sub) sub.textContent = isMuted ? 'Tap to unmute' : `${state.masterAudio.level}% output`;
  }
}

export function renderMasterVolumeUI(syncSliderValue = true) {
  const volSlider = document.getElementById('vol-slider');
  const volLabel = document.getElementById('vol-label');
  const volMuteBtn = document.getElementById('btn-master-vol-pill');

  const { level, muted } = state.masterAudio;
  if (volSlider) {
    if (syncSliderValue) volSlider.value = level;
    volSlider.style.setProperty('--fill-pct', `${level}%`);
    volSlider.classList.toggle('is-muted', muted);
  }
  if (volLabel) {
    volLabel.textContent = muted ? `${level}% · Muted` : `${level}%`;
  }
  if (volMuteBtn) {
    volMuteBtn.classList.toggle('muted', muted);
    volMuteBtn.innerHTML = icon(muted ? 'volume-x' : level < 35 ? 'volume-1' : 'volume-2');
  }
  renderQuickAudioKeys();
}

export async function loadApps() {
  try {
    const data = await api.get('/apps');
    state.presets = data.presets || [];
    state.defaultPin = Boolean(data.default_pin);
    if (data.hostname) state.hostname = data.hostname;
    updateHeaderInfo();
    renderAppsGrid();
  } catch (_) {}
}

export function updateHeaderInfo() {
  const hostEl = document.getElementById('header-hostname');
  if (hostEl && state.hostname) {
    hostEl.textContent = state.hostname;
  }
  const banner = document.getElementById('default-pin-banner');
  if (banner) {
    banner.classList.toggle('visible', Boolean(state.defaultPin));
  }
}

export function renderAppsGrid() {
  const container = document.getElementById('apps-container');
  if (!container) return;
  container.innerHTML = '';
  container.classList.toggle('editing', state.editMode);

  state.presets.forEach((preset, idx) => {
    const key = document.createElement('div');
    key.className = 'deck-key';
    key.dataset.presetId = preset.id;
    key.style.setProperty('--key-accent', preset.accent || 'var(--accent)');

    key.innerHTML = `
      <button type="button" class="key-delete-badge" aria-label="Remove ${preset.name}">
        ${icon('x')}
      </button>
      <div class="key-visual">
        <img class="key-app-icon icon-skeleton" src="${preset.icon_url}" alt="">
      </div>
      <div class="key-label"></div>
    `;

    const imgEl = key.querySelector('.key-app-icon');
    imgEl.onload = () => imgEl.classList.remove('icon-skeleton');
    imgEl.onerror = () => imgEl.classList.remove('icon-skeleton');

    key.querySelector('.key-label').textContent = preset.name;

    // Delete badge click
    const delBadge = key.querySelector('.key-delete-badge');
    delBadge.onclick = (e) => {
      e.stopPropagation();
      deletePresetWithUndo(preset, idx);
    };

    // Long-press to enter Edit Mode
    let longPressTimer = null;
    key.addEventListener('pointerdown', () => {
      if (state.editMode) return;
      longPressTimer = setTimeout(() => {
        setEditMode(true);
      }, 480);
    });
    const clearLongPress = () => {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
    };
    key.addEventListener('pointerup', clearLongPress);
    key.addEventListener('pointerleave', clearLongPress);
    key.addEventListener('pointercancel', clearLongPress);
    key.addEventListener('pointermove', clearLongPress);

    key.onclick = () => {
      if (key.dataset.wasDragged) return;
      if (state.editMode) {
        openEditAppSheet(preset, {
          onUpdated: () => renderAppsGrid(),
          onDeleteRequest: (p) => deletePresetWithUndo(p, idx),
        });
      } else {
        api
          .post(`/apps/${preset.id}/launch`)
          .then(() => showToast(`Launching ${preset.name}`))
          .catch(() => showToast(`Could not launch ${preset.name}`, { type: 'error' }));
      }
    };

    container.appendChild(key);
  });

  // Always append "+" Add App tile
  const addTile = document.createElement('button');
  addTile.type = 'button';
  addTile.className = 'deck-key add-app-tile';
  addTile.innerHTML = `
    <div class="key-visual">
      ${icon('plus')}
    </div>
    <div class="key-label">Add App</div>
  `;
  addTile.onclick = () => {
    openAddAppSheet(() => renderAppsGrid());
  };
  container.appendChild(addTile);
}

async function deletePresetWithUndo(preset, originalIndex) {
  const backup = { ...preset };
  state.presets = state.presets.filter((p) => p.id !== preset.id);
  renderAppsGrid();

  try {
    await api.delete(`/apps/${preset.id}`);
    showToast(`${backup.name} removed`, {
      duration: 4500,
      actionText: 'Undo',
      onAction: async () => {
        try {
          const res = await api.post('/apps', {
            id: backup.id,
            name: backup.name,
            type: backup.type,
            target: backup.target,
            args: backup.args,
            icon: backup.icon,
            index: originalIndex,
          });
          if (res && res.preset) {
            await loadApps();
            showToast(`Restored ${backup.name}`);
          }
        } catch (_) {
          showToast('Could not restore app', { type: 'error' });
        }
      },
    });
  } catch (err) {
    await loadApps();
    showToast('Failed to delete app', { type: 'error' });
  }
}

export async function updateVolume() {
  try {
    const data = await api.get('/audio');
    state.masterAudio.level = data.level;
    state.masterAudio.muted = Boolean(data.muted);
    renderMasterVolumeUI(true);
  } catch (_) {}
}

export async function fetchStats() {
  try {
    const stats = await api.get('/stats');
    const pushStat = (key, val) => {
      const arr = state.statsHistory[key];
      arr.push(Number(val) || 0);
      if (arr.length > 20) arr.shift();
      updateStatWidget(key, val, arr);
    };
    pushStat('cpu', stats.cpu);
    pushStat('ram', stats.ram);
    pushStat('gpu', stats.gpu ?? 0);
    if (stats.gpu_name) {
      const card = document.getElementById('stat-card-gpu');
      if (card && card.title !== stats.gpu_name) {
        card.title = stats.gpu_name;
      }
    }
  } catch (_) {}
}
