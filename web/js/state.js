export const state = {
  token: localStorage.getItem('pc_remote_token') || null,
  hostname: 'My PC',
  defaultPin: false,
  connection: 'connected', // 'connected' | 'reconnecting' | 'offline'
  activeTab: 'main',       // 'main' | 'volumes' | 'extras'
  editMode: false,

  presets: [],
  installedAppsCache: null,

  masterAudio: {
    level: 50,
    muted: false,
  },

  discord: {
    muted: false,
    deafened: false,
  },

  audioSessions: [],

  statsHistory: {
    cpu: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ram: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    gpu: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
};

const listeners = new Set();

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function notifyStateChange(topic = 'all') {
  listeners.forEach((fn) => {
    try {
      fn(topic, state);
    } catch (e) {
      console.error(e);
    }
  });
}

export function setConnectionState(status) {
  if (state.connection !== status) {
    state.connection = status;
    notifyStateChange('connection');
  }
}
