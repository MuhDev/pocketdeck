import { api } from '../api.js';
import { icon } from '../ui/icons.js';
import { showToast } from '../ui/toast.js';
import { openSheet, closeSheet } from '../ui/sheet.js';
import { createHoldButton } from '../ui/holdButton.js';

let lastNowPlayingData = null;

function formatTime(ms) {
  if (!ms || ms < 0) return '0:00';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
}

export function updateNowPlayingUI(data) {
  lastNowPlayingData = data;
  let artImg = document.getElementById('media-art-img');
  const artWrap = document.getElementById('media-art-wrap');
  const artFallback = document.getElementById('media-art-fallback');
  const sourceBadge = document.getElementById('media-source-badge');
  const statusDot = document.getElementById('media-status-dot');
  const titleEl = document.getElementById('media-track-title');
  const artistEl = document.getElementById('media-track-artist');
  const progressContainer = document.getElementById('media-progress-container');
  const progressFill = document.getElementById('media-progress-fill');
  const timePos = document.getElementById('media-time-pos');
  const timeDur = document.getElementById('media-time-dur');
  const playBtn = document.getElementById('btn-media-play');

  if (!titleEl || !artistEl) return;

  const isPlaying = data && data.status === 'Playing';

  // 1. Play / Pause button toggle
  if (playBtn) {
    playBtn.innerHTML = icon(isPlaying ? 'pause' : 'play');
    playBtn.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
  }

  // 2. Active Media State
  if (data && data.has_media && data.title) {
    titleEl.textContent = data.title;
    artistEl.textContent = data.artist ? (data.album ? `${data.artist} · ${data.album}` : data.artist) : (data.album || 'Unknown Artist');

    if (sourceBadge) {
      sourceBadge.textContent = data.app || 'Media Player';
    }
    if (statusDot) {
      statusDot.classList.toggle('active', isPlaying);
    }

    // Artwork
    if (data.thumb_url && artWrap && artFallback) {
      if (!artImg) {
        artImg = document.createElement('img');
        artImg.id = 'media-art-img';
        artImg.className = 'media-art-img';
        artImg.alt = 'Album Artwork';
        artWrap.prepend(artImg);
      }
      if (artImg.getAttribute('data-src') !== data.thumb_url) {
        artImg.setAttribute('data-src', data.thumb_url);
        artImg.onerror = () => {
          artImg.style.display = 'none';
          if (artFallback) artFallback.style.display = 'flex';
        };
        artImg.onload = () => {
          artImg.style.display = 'block';
          if (artFallback) artFallback.style.display = 'none';
        };
        artImg.src = data.thumb_url;
      }
      if (artImg.complete && artImg.naturalWidth > 0) {
        artImg.style.display = 'block';
        if (artFallback) artFallback.style.display = 'none';
      }
    } else {
      if (artImg) {
        artImg.removeAttribute('data-src');
        artImg.style.display = 'none';
      }
      if (artFallback) artFallback.style.display = 'flex';
    }

    // Timeline Progress
    if (data.duration_ms && data.duration_ms > 0 && progressContainer && progressFill && timePos && timeDur) {
      progressContainer.style.display = 'flex';
      const pct = Math.max(0, Math.min(100, (data.position_ms / data.duration_ms) * 100));
      progressFill.style.width = `${pct.toFixed(1)}%`;
      timePos.textContent = formatTime(data.position_ms);
      timeDur.textContent = formatTime(data.duration_ms);
    } else if (progressContainer) {
      progressContainer.style.display = 'none';
    }
  } else {
    // Idle / No Media State
    titleEl.textContent = 'Spotify Media';
    artistEl.textContent = 'No track currently playing';
    if (sourceBadge) sourceBadge.textContent = 'Spotify';
    if (statusDot) statusDot.classList.remove('active');
    if (progressContainer) progressContainer.style.display = 'none';
    if (artImg) {
      artImg.removeAttribute('data-src');
      artImg.style.display = 'none';
    }
    if (artFallback) {
      artFallback.style.display = 'flex';
    }
  }
}

export async function fetchNowPlaying() {
  try {
    const data = await api.get('/media/now-playing');
    updateNowPlayingUI(data);
  } catch (_) {}
}

export function initControlsScreen() {
  // 1. Media bar buttons
  const bindMedia = (id, action, label) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.onclick = async () => {
      try {
        await api.post(`/media/${action}`);
        showToast(label);
        // Fast follow-up poll after action
        setTimeout(() => fetchNowPlaying(), 300);
      } catch (_) {}
    };
  };
  bindMedia('btn-media-prev', 'prev', 'Previous Track');
  bindMedia('btn-media-play', 'play_pause', 'Play / Pause');
  bindMedia('btn-media-next', 'next', 'Next Track');

  // 2. Type on PC
  const typeInput = document.getElementById('type-input');
  const sendTypeBtn = document.getElementById('btn-send-type');
  const triggerSendType = async () => {
    if (!typeInput) return;
    const text = typeInput.value;
    if (!text) return;
    try {
      await api.post('/keys/type', { text });
      typeInput.value = '';
      showToast('Typed on PC');
    } catch (err) {
      showToast('Failed to send keystrokes', { type: 'error' });
    }
  };
  if (sendTypeBtn) sendTypeBtn.onclick = triggerSendType;
  if (typeInput) {
    typeInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        triggerSendType();
      }
    });
  }

  // 3. Quick Shortcut Keys (Copy, Paste, Cut, Undo, Select All)
  document.querySelectorAll('[data-key-action]').forEach((btn) => {
    btn.onclick = async () => {
      const action = btn.dataset.keyAction;
      const label = btn.dataset.keyLabel || action;
      try {
        await api.post(`/keys/${action}`);
        showToast(`Sent ${label} to PC`);
      } catch (_) {
        showToast(`Failed to send ${label}`, { type: 'error' });
      }
    };
  });

  // 4. Clipboard Studio
  const clipTextarea = document.getElementById('clipboard-text');
  const btnClipSend = document.getElementById('btn-clip-send');
  const btnClipGet = document.getElementById('btn-clip-get');
  const btnClipCopyLocal = document.getElementById('btn-clip-local');

  if (btnClipSend) {
    btnClipSend.onclick = async () => {
      const text = clipTextarea ? clipTextarea.value : '';
      try {
        await api.post('/clipboard', { text, paste: false });
        showToast('Sent to PC clipboard');
      } catch (_) {
        showToast('Clipboard send failed', { type: 'error' });
      }
    };
  }

  if (btnClipGet) {
    btnClipGet.onclick = async () => {
      try {
        const data = await api.get('/clipboard');
        if (clipTextarea) clipTextarea.value = data.text || '';
        showToast('Fetched PC clipboard');
      } catch (_) {
        showToast('Could not read PC clipboard', { type: 'error' });
      }
    };
  }

  if (btnClipCopyLocal) {
    btnClipCopyLocal.onclick = async () => {
      const text = clipTextarea ? clipTextarea.value : '';
      if (!text) {
        showToast('Nothing to copy', { type: 'error' });
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to phone clipboard');
      } catch (_) {
        if (clipTextarea) {
          clipTextarea.select();
          document.execCommand('copy');
          showToast('Copied to phone clipboard');
        }
      }
    };
  }

  // 5. Power Actions (Lock, Sleep, Restart, Shutdown)
  document.querySelectorAll('[data-power-action]').forEach((btn) => {
    btn.onclick = () => {
      const action = btn.dataset.powerAction;
      openPowerConfirmSheet(action);
    };
  });

  // Initial fetch
  fetchNowPlaying();
}

const POWER_META = {
  lock: {
    title: 'Lock Workstation',
    desc: 'Immediately locks your Windows session and returns to the lock screen.',
    icon: 'lock',
    color: 'var(--cyan)',
    requireHold: false,
  },
  sleep: {
    title: 'Put PC to Sleep',
    desc: 'Suspends your PC into low-power sleep mode.',
    icon: 'moon',
    color: 'var(--warning)',
    requireHold: false,
  },
  restart: {
    title: 'Restart PC',
    desc: 'Closes all applications and reboots Windows in 5 seconds. Press and hold to confirm.',
    icon: 'rotate-ccw',
    color: 'var(--warning)',
    requireHold: true,
  },
  shutdown: {
    title: 'Shut Down PC',
    desc: 'Closes all open applications and powers off your PC in 5 seconds. Press and hold to confirm.',
    icon: 'power',
    color: 'var(--danger)',
    requireHold: true,
  },
};

export function openPowerConfirmSheet(action) {
  const meta = POWER_META[action];
  if (!meta) return;

  openSheet({
    title: meta.title,
    renderBody(bodyEl) {
      const info = document.createElement('p');
      info.style.color = 'var(--text-secondary)';
      info.style.fontSize = '13.5px';
      info.style.marginBottom = '18px';
      info.textContent = meta.desc;
      bodyEl.appendChild(info);

      const executeAction = async () => {
        try {
          await api.post(`/power/${action}`, { confirm: true });
          closeSheet();
          showToast(`${meta.title} command sent`);
        } catch (err) {
          showToast(`Failed: ${err.message}`, { type: 'error' });
        }
      };

      if (meta.requireHold) {
        const holdBtn = createHoldButton({
          label: `Hold to ${meta.title}`,
          holdingLabel: 'Keep Holding…',
          iconName: meta.icon,
          durationMs: 1150,
          onConfirm: executeAction,
        });
        bodyEl.appendChild(holdBtn);
      } else {
        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'primary-btn';
        confirmBtn.style.width = '100%';
        confirmBtn.style.height = '48px';
        confirmBtn.innerHTML = `${icon(meta.icon)} <span>Confirm ${meta.title}</span>`;
        confirmBtn.onclick = executeAction;
        bodyEl.appendChild(confirmBtn);
      }
    },
  });
}
