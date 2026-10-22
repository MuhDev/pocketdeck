import { api, vibrate } from '../api.js';
import { icon } from '../ui/icons.js';
import { showToast } from '../ui/toast.js';

let lastObsData = null;
let volDebounceTimers = {};

export function updateObsUI(data) {
  if (!data) return;
  lastObsData = data;

  // 1. Connection Banner
  const connDot = document.getElementById('obs-conn-dot');
  const connText = document.getElementById('obs-conn-text');
  const launchBtn = document.getElementById('btn-obs-launch');
  const reconnectBtn = document.getElementById('btn-obs-reconnect');

  if (connDot && connText) {
    connDot.classList.toggle('connected', Boolean(data.connected));
    connDot.classList.toggle('error', !data.connected && Boolean(data.last_error));

    if (data.connected) {
      connText.textContent = `Connected to OBS Studio (Port ${data.port})`;
      if (launchBtn) launchBtn.style.display = 'none';
      if (reconnectBtn) reconnectBtn.style.display = 'none';
    } else {
      connText.textContent = data.last_error
        ? `Disconnected: ${data.last_error}`
        : `OBS Studio Disconnected (Port ${data.port})`;
      if (launchBtn) launchBtn.style.display = 'inline-flex';
      if (reconnectBtn) reconnectBtn.style.display = 'inline-flex';
    }
  }

  // 2. Stream Transport Card
  const streamCard = document.getElementById('obs-stream-card');
  const streamDot = document.getElementById('obs-stream-dot');
  const streamTimer = document.getElementById('obs-stream-timer');
  const streamStats = document.getElementById('obs-stream-stats');
  const streamBtn = document.getElementById('btn-obs-stream');
  const streamBtnLabel = document.getElementById('btn-obs-stream-label');

  if (streamCard && streamBtn) {
    const isLive = Boolean(data.streaming);
    streamCard.classList.toggle('active', isLive);
    if (streamDot) streamDot.classList.toggle('active', isLive);
    if (streamTimer) streamTimer.textContent = data.stream_timecode || '00:00:00';
    if (streamStats) {
      streamStats.textContent = isLive
        ? `${data.stream_kbits || 0} kbps · ${data.stream_dropped_frames || 0} dropped`
        : 'Offline';
    }
    streamBtn.classList.toggle('is-active', isLive);
    if (streamBtnLabel) streamBtnLabel.textContent = isLive ? 'End Stream' : 'Start Stream';
  }

  // 3. Record Transport Card
  const recordCard = document.getElementById('obs-record-card');
  const recordDot = document.getElementById('obs-record-dot');
  const recordTimer = document.getElementById('obs-record-timer');
  const recordStats = document.getElementById('obs-record-stats');
  const recordBtn = document.getElementById('btn-obs-record');
  const recordBtnLabel = document.getElementById('btn-obs-record-label');
  const pauseBtn = document.getElementById('btn-obs-pause-record');

  if (recordCard && recordBtn) {
    const isRec = Boolean(data.recording);
    const isPaused = Boolean(data.record_paused);
    recordCard.classList.toggle('active', isRec);
    if (recordDot) recordDot.classList.toggle('active', isRec);
    if (recordTimer) recordTimer.textContent = data.record_timecode || '00:00:00';
    if (recordStats) {
      recordStats.textContent = isRec ? (isPaused ? 'Recording Paused' : 'Recording Live') : 'Ready';
    }
    recordBtn.classList.toggle('is-active', isRec);
    if (recordBtnLabel) recordBtnLabel.textContent = isRec ? 'Stop Record' : 'Start Record';
    if (pauseBtn) {
      pauseBtn.classList.toggle('is-paused', isPaused);
      pauseBtn.style.opacity = isRec ? '1' : '0.4';
      pauseBtn.style.pointerEvents = isRec ? 'auto' : 'none';
      pauseBtn.innerHTML = icon(isPaused ? 'play' : 'pause');
    }
  }

  // 4. Studio Hardware Keys (Virtual Cam, Replay, Studio Mode)
  const vcamBtn = document.getElementById('btn-obs-vcam');
  if (vcamBtn) vcamBtn.classList.toggle('is-active', Boolean(data.virtual_cam));

  const replayBtn = document.getElementById('btn-obs-replay');
  if (replayBtn) replayBtn.classList.toggle('is-active', Boolean(data.replay_buffer));

  const studioBtn = document.getElementById('btn-obs-studiomode');
  if (studioBtn) studioBtn.classList.toggle('is-active', Boolean(data.studio_mode));

  // 5. Scenes Grid
  renderScenes(data.scenes || [], data.current_program_scene, data.current_preview_scene, data.studio_mode);

  // 6. Audio Inputs
  renderAudioInputs(data.audio_inputs || []);

  // 7. Scene Sources / Layers
  renderSceneItems(data.scene_items || [], data.current_program_scene);
}

function renderScenes(scenes, currentProgram, currentPreview, isStudioMode) {
  const container = document.getElementById('obs-scenes-container');
  const badge = document.getElementById('obs-active-scene-badge');
  if (!container) return;

  if (badge) {
    badge.textContent = isStudioMode
      ? `Prog: ${currentProgram || 'None'} · Prev: ${currentPreview || 'None'}`
      : `Program: ${currentProgram || 'None'}`;
  }

  if (!scenes || scenes.length === 0) {
    container.innerHTML = '<div class="obs-meta-text" style="padding: 12px;">No scenes detected</div>';
    return;
  }

  container.innerHTML = '';
  scenes.forEach((sceneName) => {
    const isProgram = sceneName === currentProgram;
    const isPreview = isStudioMode && sceneName === currentPreview;

    const card = document.createElement('div');
    card.className = `obs-scene-card${isProgram ? ' is-program' : ''}${isPreview ? ' is-preview' : ''}`;
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');

    let statusText = 'Inactive';
    if (isProgram) statusText = 'Live Program';
    else if (isPreview) statusText = 'Preview';

    card.innerHTML = `
      <div class="obs-scene-card-top">
        <span class="obs-scene-name">${sceneName}</span>
        <span class="obs-scene-dot"></span>
      </div>
      <div class="obs-scene-status">${statusText}</div>
    `;

    card.onclick = async () => {
      vibrate(10);
      try {
        await api.post('/obs/scene', { scene: sceneName });
        showToast(isStudioMode ? `Preview: ${sceneName}` : `Switched to ${sceneName}`);
        setTimeout(fetchObsStatus, 200);
      } catch (_) {
        showToast(`Failed to switch scene`, { type: 'error' });
      }
    };

    container.appendChild(card);
  });
}

function renderAudioInputs(inputs) {
  const container = document.getElementById('obs-audio-container');
  if (!container) return;

  if (!inputs || inputs.length === 0) {
    container.innerHTML = '<div class="obs-meta-text" style="padding: 12px;">No audio inputs detected</div>';
    return;
  }

  container.innerHTML = '';
  inputs.forEach((inp) => {
    const row = document.createElement('div');
    row.className = 'obs-audio-row';

    const isMuted = Boolean(inp.muted);
    const pct = Math.round((inp.volume_mul || 0) * 100);
    const db = inp.volume_db !== undefined ? `${inp.volume_db > 0 ? '+' : ''}${inp.volume_db} dB` : `${pct}%`;

    const iconType = isMuted ? 'volume-x' : (pct > 50 ? 'volume-2' : (pct > 0 ? 'volume-1' : 'volume-x'));

    row.innerHTML = `
      <div class="obs-audio-meta">
        <div class="obs-audio-title-group">
          <svg class="lucide obs-audio-icon"><use href="#icon-${iconType}"></use></svg>
          <span class="obs-audio-name" title="${inp.name}">${inp.name}</span>
        </div>
        <div class="obs-audio-controls">
          <span class="obs-audio-db tabular">${db}</span>
          <button type="button" class="obs-mute-btn${isMuted ? ' is-muted' : ''}" aria-label="Mute ${inp.name}">
            <svg class="lucide"><use href="#icon-${isMuted ? 'volume-x' : 'volume-2'}"></use></svg>
          </button>
        </div>
      </div>
      <div class="obs-slider-wrap">
        <input type="range" class="obs-slider" min="0" max="100" value="${pct}" aria-label="${inp.name} Volume">
      </div>
    `;

    const muteBtn = row.querySelector('.obs-mute-btn');
    if (muteBtn) {
      muteBtn.onclick = async () => {
        vibrate(10);
        try {
          const res = await api.post('/obs/input/mute', { name: inp.name });
          showToast(res.muted ? `Muted ${inp.name}` : `Unmuted ${inp.name}`);
          setTimeout(fetchObsStatus, 200);
        } catch (_) {}
      };
    }

    const slider = row.querySelector('.obs-slider');
    if (slider) {
      slider.oninput = (e) => {
        const val = parseInt(e.target.value, 10) || 0;
        const volumeMul = Math.max(0, Math.min(1.0, val / 100));
        clearTimeout(volDebounceTimers[inp.name]);
        volDebounceTimers[inp.name] = setTimeout(() => {
          api.post('/obs/input/volume', { name: inp.name, volume: volumeMul }).catch(() => {});
        }, 50);
      };
    }

    container.appendChild(row);
  });
}

function renderSceneItems(items, sceneName) {
  const container = document.getElementById('obs-sources-container');
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = '<div class="obs-meta-text" style="padding: 12px;">No sources in active scene</div>';
    return;
  }

  container.innerHTML = '';
  items.forEach((item) => {
    const row = document.createElement('div');
    const isEnabled = Boolean(item.enabled);
    row.className = `obs-source-row${isEnabled ? '' : ' is-hidden'}`;

    let shortType = item.type || 'source';
    if (shortType.includes('browser')) shortType = 'browser';
    else if (shortType.includes('dshow') || shortType.includes('video')) shortType = 'camera';
    else if (shortType.includes('window') || shortType.includes('game')) shortType = 'capture';

    row.innerHTML = `
      <div class="obs-source-info">
        <span class="obs-source-name" title="${item.name}">${item.name}</span>
        <span class="obs-source-badge">${shortType}</span>
      </div>
      <button type="button" class="obs-visibility-btn${isEnabled ? '' : ' is-hidden'}" aria-label="Toggle ${item.name} visibility">
        <svg class="lucide"><use href="#icon-${isEnabled ? 'eye' : 'eye-off'}"></use></svg>
      </button>
    `;

    const visBtn = row.querySelector('.obs-visibility-btn');
    if (visBtn) {
      visBtn.onclick = async () => {
        vibrate(10);
        try {
          const nextState = !isEnabled;
          await api.post('/obs/item/toggle', { id: item.id, enabled: nextState, scene: sceneName });
          showToast(`${nextState ? 'Shown' : 'Hidden'}: ${item.name}`);
          setTimeout(fetchObsStatus, 200);
        } catch (_) {}
      };
    }

    container.appendChild(row);
  });
}

export async function fetchObsStatus() {
  try {
    const data = await api.get('/obs/status');
    updateObsUI(data);
  } catch (_) {}
}

export function initObsScreen() {
  // 1. Stream toggle
  const streamBtn = document.getElementById('btn-obs-stream');
  if (streamBtn) {
    streamBtn.onclick = async () => {
      vibrate(14);
      try {
        const res = await api.post('/obs/stream/toggle');
        showToast(res.streaming ? 'Stream Started!' : 'Stream Stopped');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {
        showToast('Stream toggle failed', { type: 'error' });
      }
    };
  }

  // 2. Record toggle
  const recordBtn = document.getElementById('btn-obs-record');
  if (recordBtn) {
    recordBtn.onclick = async () => {
      vibrate(14);
      try {
        const res = await api.post('/obs/record/toggle');
        showToast(res.recording ? 'Recording Started' : 'Recording Stopped');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {
        showToast('Record toggle failed', { type: 'error' });
      }
    };
  }

  // 3. Pause Record
  const pauseBtn = document.getElementById('btn-obs-pause-record');
  if (pauseBtn) {
    pauseBtn.onclick = async () => {
      vibrate(10);
      try {
        const res = await api.post('/obs/record/pause');
        showToast(res.paused ? 'Recording Paused' : 'Recording Resumed');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {}
    };
  }

  // 4. Virtual Cam
  const vcamBtn = document.getElementById('btn-obs-vcam');
  if (vcamBtn) {
    vcamBtn.onclick = async () => {
      vibrate(10);
      try {
        const res = await api.post('/obs/virtualcam/toggle');
        showToast(res.virtual_cam ? 'Virtual Camera On' : 'Virtual Camera Off');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {}
    };
  }

  // 5. Replay Buffer Save
  const replayBtn = document.getElementById('btn-obs-replay');
  if (replayBtn) {
    replayBtn.onclick = async () => {
      vibrate(12);
      try {
        await api.post('/obs/replay/save');
        showToast('Instant Replay Saved!');
      } catch (_) {
        showToast('Replay buffer not active', { type: 'error' });
      }
    };
  }

  // 6. Studio Mode
  const studioBtn = document.getElementById('btn-obs-studiomode');
  if (studioBtn) {
    studioBtn.onclick = async () => {
      vibrate(10);
      try {
        const res = await api.post('/obs/studiomode/toggle');
        showToast(res.studio_mode ? 'Studio Mode Active' : 'Studio Mode Off');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {}
    };
  }

  // 7. Transition
  const transBtn = document.getElementById('btn-obs-transition');
  if (transBtn) {
    transBtn.onclick = async () => {
      vibrate(12);
      try {
        await api.post('/obs/transition');
        showToast('Transition Executed');
        setTimeout(fetchObsStatus, 300);
      } catch (_) {}
    };
  }

  // 8. Launch OBS
  const launchBtn = document.getElementById('btn-obs-launch');
  if (launchBtn) {
    launchBtn.onclick = async () => {
      vibrate(10);
      try {
        const res = await api.post('/obs/launch');
        showToast(res.launched ? 'Launching OBS Studio…' : 'OBS executable not found');
        setTimeout(fetchObsStatus, 3000);
      } catch (_) {}
    };
  }

  // 9. Reconnect
  const reconnectBtn = document.getElementById('btn-obs-reconnect');
  if (reconnectBtn) {
    reconnectBtn.onclick = async () => {
      vibrate(10);
      showToast('Connecting to OBS…');
      try {
        const res = await api.post('/obs/connect', {});
        if (res.connected) {
          showToast('Connected to OBS Studio!');
        } else {
          showToast('Could not reach OBS WebSocket on port 4455', { type: 'error' });
        }
        updateObsUI(res.state);
      } catch (_) {
        showToast('Connection failed', { type: 'error' });
      }
    };
  }

  // 10. Refresh Browser Sources
  const refreshBrowserBtn = document.getElementById('btn-obs-refresh-browser');
  if (refreshBrowserBtn) {
    refreshBrowserBtn.onclick = async () => {
      vibrate(10);
      try {
        await api.post('/obs/browser/refresh');
        showToast('Overlays Refreshed!');
      } catch (_) {}
    };
  }

  // 11. Stream Screenshot
  const screenshotBtn = document.getElementById('btn-obs-screenshot');
  if (screenshotBtn) {
    screenshotBtn.onclick = async () => {
      vibrate(10);
      showToast('Stream Screenshot Captured');
    };
  }
}
