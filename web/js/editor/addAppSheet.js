import { state } from '../state.js';
import { api } from '../api.js';
import { icon } from '../ui/icons.js';
import { openSheet, closeSheet } from '../ui/sheet.js';
import { showToast } from '../ui/toast.js';

export function openAddAppSheet(onPresetAdded) {
  let currentTab = 'pc'; // 'pc' | 'url' | 'path'

  openSheet({
    title: 'Add to Stream Deck',
    renderBody(bodyEl) {
      bodyEl.innerHTML = `
        <div class="sheet-tabs">
          <button type="button" class="sheet-tab-btn active" data-tab="pc">
            ${icon('app-window')} <span>PC Apps</span>
          </button>
          <button type="button" class="sheet-tab-btn" data-tab="url">
            ${icon('globe')} <span>Website</span>
          </button>
          <button type="button" class="sheet-tab-btn" data-tab="path">
            ${icon('folder')} <span>Path</span>
          </button>
        </div>
        <div id="add-sheet-tab-content"></div>
      `;

      const tabContent = bodyEl.querySelector('#add-sheet-tab-content');
      const tabBtns = bodyEl.querySelectorAll('.sheet-tab-btn');

      const renderActiveTab = () => {
        tabBtns.forEach((b) => b.classList.toggle('active', b.dataset.tab === currentTab));
        if (currentTab === 'pc') {
          renderPcAppsTab(tabContent, onPresetAdded);
        } else if (currentTab === 'url') {
          renderWebsiteTab(tabContent, onPresetAdded);
        } else {
          renderPathTab(tabContent, onPresetAdded);
        }
      };

      tabBtns.forEach((btn) => {
        btn.onclick = () => {
          currentTab = btn.dataset.tab;
          renderActiveTab();
        };
      });

      renderActiveTab();
    },
  });
}

async function renderPcAppsTab(container, onPresetAdded) {
  container.innerHTML = `
    <div class="input-action-row" style="margin-bottom: 12px;">
      <div class="search-box-wrap" style="flex:1; margin-bottom:0;">
        ${icon('search')}
        <input type="text" id="pc-app-search" class="text-input" placeholder="Search installed PC apps…" autocomplete="off">
      </div>
      <button type="button" id="btn-refresh-installed" class="icon-pill-btn" title="Refresh installed apps">
        ${icon('refresh-cw')}
      </button>
    </div>
    <div id="discovered-apps-list" class="discovered-apps-list">
      <div class="empty-state-box">
        <span>Scanning installed applications…</span>
      </div>
    </div>
  `;

  const searchInput = container.querySelector('#pc-app-search');
  const refreshBtn = container.querySelector('#btn-refresh-installed');
  const listEl = container.querySelector('#discovered-apps-list');

  const drawList = (apps, filterText = '') => {
    const q = filterText.trim().toLowerCase();
    const filtered = q
      ? apps.filter((a) => a.name.toLowerCase().includes(q))
      : apps;

    if (!filtered.length) {
      listEl.innerHTML = `
        <div class="empty-state-box">
          ${icon('search')}
          <span>No matching apps found</span>
        </div>
      `;
      return;
    }

    listEl.innerHTML = '';
    filtered.slice(0, 120).forEach((app) => {
      const row = document.createElement('div');
      row.className = 'discovered-app-row';
      row.innerHTML = `
        <div class="discovered-app-left">
          <img class="discovered-app-icon" src="${app.icon_url}" alt="" loading="lazy">
          <span class="discovered-app-name"></span>
        </div>
        <span class="discovered-add-pill">+ Add</span>
      `;
      row.querySelector('.discovered-app-name').textContent = app.name;
      row.onclick = async () => {
        try {
          const res = await api.post('/apps', {
            name: app.name,
            type: 'shell_app',
            target: app.app_id,
          });
          if (res && res.preset) {
            state.presets.push(res.preset);
            if (typeof onPresetAdded === 'function') onPresetAdded(res.preset);
            closeSheet();
            showToast(`Added ${app.name}`);
          }
        } catch (err) {
          showToast(err.message || 'Could not add app', { type: 'error' });
        }
      };
      listEl.appendChild(row);
    });
  };

  const fetchInstalled = async (forceRefresh = false) => {
    try {
      if (!forceRefresh && Array.isArray(state.installedAppsCache) && state.installedAppsCache.length) {
        drawList(state.installedAppsCache, searchInput.value);
        return;
      }
      listEl.innerHTML = `<div class="empty-state-box"><span>Loading PC applications…</span></div>`;
      const data = await api.get(`/apps/installed${forceRefresh ? '?refresh=true' : ''}`);
      state.installedAppsCache = data.apps || [];
      drawList(state.installedAppsCache, searchInput.value);
    } catch (err) {
      listEl.innerHTML = `<div class="empty-state-box"><span>Failed to load installed apps</span></div>`;
    }
  };

  searchInput.oninput = () => {
    drawList(state.installedAppsCache || [], searchInput.value);
  };

  refreshBtn.onclick = () => fetchInstalled(true);

  await fetchInstalled(false);
}

function renderWebsiteTab(container, onPresetAdded) {
  container.innerHTML = `
    <div class="form-field">
      <label class="form-label">Website URL</label>
      <input type="url" id="web-url-input" class="text-input" placeholder="https://youtube.com or twitch.tv">
    </div>
    <div class="form-field">
      <label class="form-label">Button Label</label>
      <input type="text" id="web-name-input" class="text-input" placeholder="e.g. YouTube">
    </div>
    <button type="button" id="btn-save-web" class="primary-btn" style="width:100%; margin-top:6px;">
      ${icon('plus')} <span>Add Website Key</span>
    </button>
  `;

  const urlInput = container.querySelector('#web-url-input');
  const nameInput = container.querySelector('#web-name-input');
  let nameManuallyEdited = false;

  nameInput.oninput = () => {
    nameManuallyEdited = nameInput.value.trim().length > 0;
  };

  urlInput.oninput = () => {
    if (nameManuallyEdited) return;
    try {
      const raw = urlInput.value.trim();
      if (!raw) return;
      const u = new URL(raw.includes('://') ? raw : `https://${raw}`);
      const host = u.hostname.replace(/^www\./i, '').split('.')[0];
      if (host) {
        nameInput.value = host.charAt(0).toUpperCase() + host.slice(1);
      }
    } catch (_) {}
  };

  container.querySelector('#btn-save-web').onclick = async () => {
    const target = urlInput.value.trim();
    const name = nameInput.value.trim();
    if (!target || !name) {
      showToast('Enter both a URL and label', { type: 'error' });
      return;
    }
    try {
      const res = await api.post('/apps', { name, type: 'url', target });
      if (res && res.preset) {
        state.presets.push(res.preset);
        if (typeof onPresetAdded === 'function') onPresetAdded(res.preset);
        closeSheet();
        showToast(`Added ${res.preset.name}`);
      }
    } catch (err) {
      showToast(err.message || 'Failed to add website', { type: 'error' });
    }
  };
}

function renderPathTab(container, onPresetAdded) {
  container.innerHTML = `
    <div class="form-field">
      <label class="form-label">Launch Type</label>
      <div class="sheet-tabs" id="path-type-tabs" style="margin-bottom:0;">
        <button type="button" class="sheet-tab-btn active" data-ptype="app">App (.exe)</button>
        <button type="button" class="sheet-tab-btn" data-ptype="folder">Folder</button>
        <button type="button" class="sheet-tab-btn" data-ptype="steam">Steam URI</button>
      </div>
    </div>
    <div class="form-field">
      <label class="form-label">Target Path or URI</label>
      <input type="text" id="path-target-input" class="text-input" placeholder="C:\\Program Files\\...\\app.exe">
    </div>
    <div class="form-field">
      <label class="form-label">Button Label</label>
      <input type="text" id="path-name-input" class="text-input" placeholder="My App">
    </div>
    <button type="button" id="btn-save-path" class="primary-btn" style="width:100%; margin-top:6px;">
      ${icon('plus')} <span>Add Key to Deck</span>
    </button>
  `;

  let selectedType = 'app';
  const typeBtns = container.querySelectorAll('#path-type-tabs .sheet-tab-btn');
  const targetInput = container.querySelector('#path-target-input');
  const nameInput = container.querySelector('#path-name-input');

  typeBtns.forEach((btn) => {
    btn.onclick = () => {
      selectedType = btn.dataset.ptype;
      typeBtns.forEach((b) => b.classList.toggle('active', b === btn));
      if (selectedType === 'folder') {
        targetInput.placeholder = 'D:\\Projects or %USERPROFILE%\\Downloads';
      } else if (selectedType === 'steam') {
        targetInput.placeholder = 'steam://rungameid/730';
      } else {
        targetInput.placeholder = 'C:\\Program Files\\...\\app.exe';
      }
    };
  });

  container.querySelector('#btn-save-path').onclick = async () => {
    const target = targetInput.value.trim();
    const name = nameInput.value.trim();
    if (!target || !name) {
      showToast('Enter both a target path and label', { type: 'error' });
      return;
    }
    try {
      const res = await api.post('/apps', { name, type: selectedType, target });
      if (res && res.preset) {
        state.presets.push(res.preset);
        if (typeof onPresetAdded === 'function') onPresetAdded(res.preset);
        closeSheet();
        showToast(`Added ${res.preset.name}`);
      }
    } catch (err) {
      showToast(err.message || 'Failed to add key', { type: 'error' });
    }
  };
}
