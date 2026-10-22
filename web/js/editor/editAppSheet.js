import { state } from '../state.js';
import { api } from '../api.js';
import { icon } from '../ui/icons.js';
import { openSheet, closeSheet } from '../ui/sheet.js';
import { showToast } from '../ui/toast.js';

export function openEditAppSheet(preset, { onUpdated, onDeleteRequest }) {
  openSheet({
    title: `Edit "${preset.name}"`,
    renderBody(bodyEl) {
      bodyEl.innerHTML = `
        <div class="edit-icon-preview-row">
          <img id="edit-sheet-icon-img" class="edit-icon-preview" src="${preset.icon_url}" alt="">
          <div style="display:flex; flex-direction:column; gap:6px; flex:1;">
            <span style="font-size:13px; font-weight:700;">App Icon</span>
            <span style="font-size:11.5px; color:var(--text-muted);">Extracted automatically or upload your own</span>
            <div>
              <input type="file" id="custom-icon-file" accept="image/*" style="display:none;">
              <button type="button" id="btn-upload-icon" class="secondary-btn" style="height:34px; font-size:12px;">
                ${icon('upload')} <span>Custom Icon…</span>
              </button>
            </div>
          </div>
        </div>

        <div class="form-field">
          <label class="form-label">Button Label</label>
          <input type="text" id="edit-app-name" class="text-input" value="">
        </div>

        <div class="form-field">
          <label class="form-label">Target (${preset.type})</label>
          <input type="text" id="edit-app-target" class="text-input" value="">
        </div>

        <div style="display:flex; gap:10px; margin-top:18px;">
          <button type="button" id="btn-delete-app" class="secondary-btn" style="color:var(--danger); border-color:rgba(239,68,68,0.35);">
            ${icon('trash-2')} <span>Remove</span>
          </button>
          <button type="button" id="btn-save-edit" class="primary-btn" style="flex:1;">
            ${icon('check')} <span>Save Changes</span>
          </button>
        </div>
      `;

      const nameInput = bodyEl.querySelector('#edit-app-name');
      const targetInput = bodyEl.querySelector('#edit-app-target');
      const fileInput = bodyEl.querySelector('#custom-icon-file');
      const uploadBtn = bodyEl.querySelector('#btn-upload-icon');
      const previewImg = bodyEl.querySelector('#edit-sheet-icon-img');

      nameInput.value = preset.name;
      targetInput.value = preset.target;

      uploadBtn.onclick = () => fileInput.click();

      fileInput.onchange = async () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
          uploadBtn.disabled = true;
          const res = await api.upload(`/apps/${preset.id}/icon`, formData);
          if (res && res.preset) {
            Object.assign(preset, res.preset);
            previewImg.src = `${res.preset.icon_url}&t=${Date.now()}`;
            if (typeof onUpdated === 'function') onUpdated(preset);
            showToast('Custom icon updated');
          }
        } catch (err) {
          showToast(err.message || 'Icon upload failed', { type: 'error' });
        } finally {
          uploadBtn.disabled = false;
        }
      };

      bodyEl.querySelector('#btn-save-edit').onclick = async () => {
        const newName = nameInput.value.trim();
        const newTarget = targetInput.value.trim();
        if (!newName || !newTarget) {
          showToast('Label and target cannot be empty', { type: 'error' });
          return;
        }
        try {
          const res = await api.patch(`/apps/${preset.id}`, {
            name: newName,
            target: newTarget,
          });
          if (res && res.preset) {
            Object.assign(preset, res.preset);
            if (typeof onUpdated === 'function') onUpdated(preset);
            closeSheet();
            showToast('Saved changes');
          }
        } catch (err) {
          showToast(err.message || 'Save failed', { type: 'error' });
        }
      };

      bodyEl.querySelector('#btn-delete-app').onclick = () => {
        closeSheet();
        if (typeof onDeleteRequest === 'function') {
          onDeleteRequest(preset);
        }
      };
    },
  });
}
