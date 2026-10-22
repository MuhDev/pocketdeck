import { state, subscribe, setConnectionState } from './state.js';
import { api, setOnUnauthorized, vibrate } from './api.js';
import { loadIconSprite } from './ui/icons.js';
import { initSheet, closeSheet } from './ui/sheet.js';
import { initLoginScreen } from './screens/login.js';
import {
  initHomeScreen,
  loadApps,
  updateVolume,
  fetchStats,
  setEditMode,
  updateHeaderInfo,
  renderAppsGrid,
  renderMasterVolumeUI,
} from './screens/home.js';
import { initMixerScreen, fetchAppVolumes, renderAppVolumes } from './screens/mixer.js';
import { initControlsScreen, fetchNowPlaying, updateNowPlayingUI } from './screens/controls.js';
import { initObsScreen, fetchObsStatus, updateObsUI } from './screens/obs.js';
import { updateStatWidget } from './ui/gauge.js';

let statsTimer = null;
let mixerTimer = null;
let mediaTimer = null;
let obsTimer = null;

function updateConnectionUI() {
  const pill = document.getElementById('conn-pill');
  const text = document.getElementById('conn-status');
  if (!pill || !text) return;

  pill.classList.remove('reconnecting', 'offline');
  if (state.connection === 'connected') {
    text.textContent = 'Connected';
  } else if (state.connection === 'reconnecting') {
    pill.classList.add('reconnecting');
    text.textContent = 'Reconnecting…';
  } else {
    pill.classList.add('offline');
    text.textContent = 'Offline';
  }
}

function startPolling() {
  stopPolling();
  fetchStats();
  statsTimer = setInterval(() => {
    fetchStats();
    updateVolume();
  }, 2800);

  mixerTimer = setInterval(() => {
    if (state.activeTab === 'volumes') {
      fetchAppVolumes();
    }
  }, 4000);

  mediaTimer = setInterval(() => {
    if (state.activeTab === 'extras') {
      fetchNowPlaying();
    }
  }, 2500);

  obsTimer = setInterval(() => {
    if (state.activeTab === 'obs') {
      fetchObsStatus();
    }
  }, 2200);
}

function stopPolling() {
  if (statsTimer) {
    clearInterval(statsTimer);
    statsTimer = null;
  }
  if (mixerTimer) {
    clearInterval(mixerTimer);
    mixerTimer = null;
  }
  if (mediaTimer) {
    clearInterval(mediaTimer);
    mediaTimer = null;
  }
  if (obsTimer) {
    clearInterval(obsTimer);
    obsTimer = null;
  }
}

export function showApp() {
  const authEl = document.getElementById('auth-screen');
  const appEl = document.getElementById('app-screen');
  if (authEl) authEl.style.display = 'none';
  if (appEl) appEl.style.display = 'flex';

  setConnectionState('connected');
  updateConnectionUI();
  updateHeaderInfo();

  loadApps();
  updateVolume();
  fetchAppVolumes();
  fetchNowPlaying();
  fetchObsStatus();
  startPolling();
}

export function logout() {
  state.token = null;
  state.editMode = false;
  localStorage.removeItem('pc_remote_token');
  stopPolling();
  closeSheet();

  const authEl = document.getElementById('auth-screen');
  const appEl = document.getElementById('app-screen');
  if (appEl) appEl.style.display = 'none';
  if (authEl) authEl.style.display = 'flex';
}

export function switchTab(tabName) {
  if (!['main', 'volumes', 'extras', 'obs'].includes(tabName)) return;
  state.activeTab = tabName;
  vibrate(8);

  if (tabName !== 'main' && state.editMode) {
    setEditMode(false);
  }

  document.querySelectorAll('.tab-pane').forEach((pane) => {
    pane.classList.toggle('active', pane.id === `tab-${tabName}`);
  });

  const tabsOrder = ['main', 'volumes', 'extras', 'obs'];
  const idx = tabsOrder.indexOf(tabName);
  const indicator = document.getElementById('tabbar-indicator');
  if (indicator && idx !== -1) {
    indicator.style.setProperty('--active-tab-index', String(idx));
  }

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  if (tabName === 'volumes') {
    fetchAppVolumes();
  }
  if (tabName === 'extras') {
    fetchNowPlaying();
  }
  if (tabName === 'obs') {
    fetchObsStatus();
  }
}

window.switchTab = switchTab;

function enableBreakUiStressTest() {
  console.log('[break-ui] Activating worst-case data fixture stress test mode');
  const authEl = document.getElementById('auth-screen');
  const appEl = document.getElementById('app-screen');
  if (authEl) authEl.style.display = 'none';
  if (appEl) appEl.style.display = 'flex';

  state.token = 'stress-token';
  state.hostname = 'DESKTOP-STRESS-TEST-ULTRA-WIDE-RIG';
  updateHeaderInfo();

  // 1. Extreme Presets (60-char names, single-letter, emoji, many apps)
  state.presets = [
    { id: 's1', name: 'SuperLongDevelopmentEnvironmentVisualStudioCodeInsidersEnterpriseBuild', icon_url: '/assets/logo/icon-192.png', accent: '#7C5CFF' },
    { id: 's2', name: 'X', icon_url: '/assets/logo/icon-192.png', accent: '#38BDF8' },
    { id: 's3', name: 'Spotify (Music Player / Gaming)', icon_url: '/assets/logo/icon-192.png', accent: '#22C58B' },
    { id: 's4', name: 'Node.js (v22.19.0-x64) [PROD/STAGING]', icon_url: '/assets/logo/icon-192.png', accent: '#E5A024' },
    { id: 's5', name: 'Steam Client Bootstrapper (32 bit)', icon_url: '/assets/logo/icon-192.png', accent: '#7C5CFF' },
    { id: 's6', name: 'Discord PTB Canary', icon_url: '/assets/logo/icon-192.png', accent: '#5865F2' },
    { id: 's7', name: 'Blender 4.2 LTS', icon_url: '/assets/logo/icon-192.png', accent: '#E5A024' },
    { id: 's8', name: 'Photoshop 2026', icon_url: '/assets/logo/icon-192.png', accent: '#38BDF8' },
    { id: 's9', name: 'Terminal (PowerShell 7 Elevated)', icon_url: '/assets/logo/icon-192.png', accent: '#7C5CFF' },
    { id: 's10', name: 'DaVinci Resolve Studio 19.1', icon_url: '/assets/logo/icon-192.png', accent: '#E5484D' },
    { id: 's11', name: 'Affinity Photo', icon_url: '/assets/logo/icon-192.png', accent: '#7C5CFF' },
    { id: 's12', name: 'Firefox Developer Edition', icon_url: '/assets/logo/icon-192.png', accent: '#E5A024' },
  ];
  renderAppsGrid();

  // 2. Extreme Telemetry Spikes
  updateStatWidget('cpu', 94, [20, 35, 60, 85, 94]);
  updateStatWidget('ram', 78, [70, 72, 75, 76, 78]);
  updateStatWidget('gpu', 45, [15, 25, 30, 40, 45]);

  // 3. Audio & Mixer
  state.masterAudio.level = 82;
  state.masterAudio.muted = false;
  renderMasterVolumeUI(true);

  state.audioSessions = [
    { id: 'obs', name: 'OBS Studio 64-bit Broadcaster.exe', level: 90, muted: false, accent: '#7C5CFF' },
    { id: 'audiodg', name: 'Windows Audio Device Graph Isolation.exe', level: 100, muted: false, accent: '#22C58B' },
    { id: 'game', name: 'Cyberpunk2077_DirectX12_V1.63.exe', level: 65, muted: false, accent: '#E5A024' },
    { id: 'discord', name: 'Discord.exe', level: 80, muted: true, accent: '#5865F2' },
  ];
  renderAppVolumes(state.audioSessions);

  // 4. Now Playing Media Player
  updateNowPlayingUI({
    has_media: true,
    title: "That's So True",
    artist: "Gracie Abrams",
    album: "The Secret of Us (Deluxe)",
    status: "Playing",
    app: "Spotify",
    position_ms: 40509,
    duration_ms: 166300,
    thumb_url: "/api/media/thumbnail",
  });

  // 5. OBS Studio Cockpit
  updateObsUI({
    connected: true,
    port: 4455,
    streaming: true,
    stream_timecode: "01:24:18",
    stream_dropped_frames: 12,
    stream_kbits: 6200,
    recording: true,
    record_paused: false,
    record_timecode: "01:24:18",
    virtual_cam: false,
    replay_buffer: true,
    studio_mode: false,
    current_program_scene: "Main Gaming",
    current_preview_scene: "Just Chatting",
    scenes: ["Main Gaming", "Just Chatting", "Starting Soon", "BRB (Intermission)", "Ending Credits"],
    audio_inputs: [
      { name: "Mic / Aux (Shure SM7B)", kind: "wasapi_input_capture", muted: false, volume_mul: 0.88, volume_db: -1.1 },
      { name: "Desktop Audio (Game Audio)", kind: "wasapi_output_capture", muted: false, volume_mul: 1.0, volume_db: 0.0 },
      { name: "Music / Spotify (Stream Output)", kind: "wasapi_process_output_capture", muted: false, volume_mul: 0.65, volume_db: -3.7 },
      { name: "Discord Voice (Squad Chat)", kind: "wasapi_process_output_capture", muted: true, volume_mul: 0.80, volume_db: -1.9 },
    ],
    scene_items: [
      { id: 1, name: "Webcam (Sony A6400 4K CamLink)", type: "dshow_input", enabled: true },
      { id: 2, name: "Game Capture (Palworld-WinGDK-Shipping.exe)", type: "window_capture", enabled: true },
      { id: 3, name: "Stream Overlay & Animated Alerts", type: "browser_source", enabled: true },
      { id: 4, name: "Live Twitch / YouTube Chat Box", type: "browser_source", enabled: true },
      { id: 5, name: "Sub Goal & Donation Tracker", type: "browser_source", enabled: false },
    ],
  });
}

async function boot() {
  await loadIconSprite();
  initSheet();
  initLoginScreen(() => showApp());
  initHomeScreen();
  initMixerScreen();
  initControlsScreen();
  initObsScreen();

  setOnUnauthorized(() => logout());
  subscribe((topic) => {
    if (topic === 'connection') updateConnectionUI();
  });

  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.onclick = () => logout();
  }

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.onclick = (e) => {
      e.preventDefault();
      switchTab(btn.dataset.tab);
    };
  });

  const tabbar = document.querySelector('.tabbar');
  if (tabbar) {
    tabbar.addEventListener('click', (e) => {
      const btn = e.target.closest('.tab-btn');
      if (btn && btn.dataset.tab) {
        switchTab(btn.dataset.tab);
      }
    });
  }

  const params = new URLSearchParams(window.location.search);
  const targetTab = params.get('tab');

  // Emil Break-UI stress test flag (?stress=1)
  if (params.has('stress')) {
    localStorage.setItem('pc_remote_token', 'stress-token');
    enableBreakUiStressTest();
    const normTab = (targetTab === 'controls' || targetTab === 'extras') ? 'extras' : targetTab;
    if (normTab) switchTab(normTab);
    return;
  }

  if (state.token) {
    try {
      const data = await api.get('/apps');
      state.presets = data.presets || [];
      state.defaultPin = Boolean(data.default_pin);
      if (data.hostname) state.hostname = data.hostname;
      showApp();
    } catch (_) {
      logout();
    }
  } else {
    logout();
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
}

boot();
