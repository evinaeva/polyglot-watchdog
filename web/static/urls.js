const domainInput = document.getElementById('domainInput');
const loadButton = document.getElementById('loadButton');
const replaceButton = document.getElementById('replaceButton');
const addButton = document.getElementById('addButton');
const clearButton = document.getElementById('clearButton');
const urlsMultiline = document.getElementById('urlsMultiline');
const updatedAt = document.getElementById('updatedAt');
const savedUrlsBody = document.getElementById('savedUrlsBody');
const errorBox = document.getElementById('errorBox');
const statusBox = document.getElementById('statusBox');
let recipes = [];

const SAVE_SUCCESS_TIMEOUT_MS = 2000;
const ACTIVATION_TIMEOUT_MS = 1200;
const saveStateTimers = new WeakMap();

function formatUpdatedAt(value) {
  if (typeof value !== 'string') return '—';
  const trimmed = value.trim();
  if (!trimmed) return '—';
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) return '—';
  const day = String(parsed.getUTCDate()).padStart(2, '0');
  const month = String(parsed.getUTCMonth() + 1).padStart(2, '0');
  const year = String(parsed.getUTCFullYear());
  return `${day}.${month}.${year}`;
}

function t(key, fallback) {
  return window.i18n?.t?.(key) || fallback;
}

function setStatus(message, type = 'info') {
  if (!statusBox) return;
  statusBox.textContent = message || '';
  statusBox.classList.toggle('hidden', !message);
  statusBox.classList.remove('status-success', 'status-error', 'status-info');
  if (message && type === 'success') {
    statusBox.classList.add('status-success');
  }
  if (message && type === 'error') {
    statusBox.classList.add('status-error');
  }
}

function setError(message) {
  errorBox.textContent = message || '';
  errorBox.classList.toggle('hidden', !message);
}

function setButtonState(button, state, options = {}) {
  if (!button) return;
  const {
    idleLabel = button.dataset.defaultLabel || button.textContent,
    loadingLabel = t('urls.button.saving', 'Saving...'),
    successLabel = t('urls.button.saved', 'Saved'),
    errorLabel = t('urls.button.error', 'Failed'),
    activatedLabel = t('urls.button.done', 'Done'),
    ariaBusy = false,
  } = options;

  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = idleLabel;
  }

  const labels = {
    idle: idleLabel,
    saving: loadingLabel,
    loading: loadingLabel,
    saved: successLabel,
    error: errorLabel,
    activated: activatedLabel,
  };

  button.dataset.state = state;
  button.textContent = labels[state] || idleLabel;
  button.disabled = state === 'saving' || state === 'loading';
  button.setAttribute('aria-busy', ariaBusy || state === 'saving' || state === 'loading' ? 'true' : 'false');
}

function markButtonActivated(button, options = {}) {
  if (!button) return;
  clearTimeout(saveStateTimers.get(button));
  setButtonState(button, 'activated', options);
  const timer = setTimeout(() => {
    setButtonState(button, 'idle', options);
    saveStateTimers.delete(button);
  }, ACTIVATION_TIMEOUT_MS);
  saveStateTimers.set(button, timer);
}

function bindDirtyReset(tr, saveButton) {
  const resetSaveState = () => {
    if (saveButton.dataset.state === 'saved') {
      clearTimeout(saveStateTimers.get(saveButton));
      setButtonState(saveButton, 'idle', {
        idleLabel: t('urls.button.save', 'Save'),
        loadingLabel: t('urls.button.saving', 'Saving...'),
        successLabel: t('urls.button.saved', 'Saved'),
        errorLabel: t('urls.button.error', 'Failed'),
      });
      saveStateTimers.delete(saveButton);
    }
  };

  const urlField = tr.querySelector('[data-field="URL"]');
  const recipeField = tr.querySelector('[data-field="recipe_ids"]');
  const activeField = tr.querySelector('[data-field="active"]');
  [urlField, recipeField, activeField].forEach((field) => {
    if (field) field.addEventListener('input', resetSaveState);
    if (field) field.addEventListener('change', resetSaveState);
  });
}

async function callApi(path, method, payload) {
  const response = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function renderRecipeChips(container, select) {
  container.innerHTML = '';
  const selected = Array.from(select.selectedOptions).map((opt) => ({ id: opt.value, label: opt.textContent || opt.value }));
  if (!selected.length) {
    const empty = document.createElement('span');
    empty.className = 'recipe-chip-empty';
    empty.textContent = 'No recipes selected';
    container.appendChild(empty);
    return;
  }

  for (const item of selected) {
    const chip = document.createElement('span');
    chip.className = 'recipe-chip';
    chip.textContent = item.label;

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'recipe-chip-remove';
    remove.textContent = '×';
    remove.title = `Remove ${item.id}`;
    remove.addEventListener('click', () => {
      const option = Array.from(select.options).find((opt) => opt.value === item.id);
      if (option) option.selected = false;
      renderRecipeChips(container, select);
    });

    chip.appendChild(remove);
    container.appendChild(chip);
  }
}

function buildRecipePicker(row) {
  const wrap = document.createElement('div');
  wrap.className = 'recipe-picker';

  const select = document.createElement('select');
  select.multiple = true;
  select.dataset.field = 'recipe_ids';
  select.className = 'recipe-picker-select';

  const selectedSet = new Set(Array.isArray(row.recipe_ids) ? row.recipe_ids.map(String) : []);
  const knownIds = new Set();
  for (const recipe of recipes) {
    const id = String(recipe.recipe_id || '').trim();
    if (!id) continue;
    knownIds.add(id);
    const option = document.createElement('option');
    option.value = id;
    option.textContent = recipe.url_pattern ? `${id} (${recipe.url_pattern})` : id;
    option.selected = selectedSet.has(id);
    select.appendChild(option);
  }

  for (const id of selectedSet) {
    if (!id || knownIds.has(id)) continue;
    const option = document.createElement('option');
    option.value = id;
    option.textContent = `${id} (missing)`;
    option.selected = true;
    option.dataset.missing = 'true';
    select.appendChild(option);
  }

  const chips = document.createElement('div');
  chips.className = 'recipe-chips';
  renderRecipeChips(chips, select);
  select.addEventListener('change', () => renderRecipeChips(chips, select));

  wrap.appendChild(select);
  wrap.appendChild(chips);
  return wrap;
}

function render(data) {
  const urls = Array.isArray(data.urls) ? data.urls : [];
  updatedAt.textContent = formatUpdatedAt(data.updated_at);
  urlsMultiline.value = urls.map((row) => row.url || '').filter(Boolean).join('\n');
  savedUrlsBody.innerHTML = '';

  for (const row of urls) {
    const tr = document.createElement('tr');
    const hasRecipe = Array.isArray(row.recipe_ids) && row.recipe_ids.length > 0;
    const invalid = !row.url || !/^https?:\/\//.test(row.url);
    const urlCell = document.createElement('td');
    urlCell.className = 'url-cell';
    const urlField = document.createElement('input');
    urlField.dataset.field = 'URL';
    urlField.value = row.url || '';
    urlField.title = row.url || '';
    urlField.addEventListener('input', () => {
      urlField.title = urlField.value;
    });
    urlCell.appendChild(urlField);

    const recipesCell = document.createElement('td');
    recipesCell.appendChild(buildRecipePicker(row));

    const activeCell = document.createElement('td');
    const activeField = document.createElement('input');
    activeField.type = 'checkbox';
    activeField.dataset.field = 'active';
    activeField.checked = row.active !== false;
    activeCell.appendChild(activeField);

    const hasRecipeCell = document.createElement('td');
    hasRecipeCell.textContent = hasRecipe ? 'has_recipe' : '-';

    const statusCell = document.createElement('td');
    statusCell.textContent = invalid ? 'invalid' : 'valid';

    const actionsCell = document.createElement('td');
    const saveButton = document.createElement('button');
    saveButton.className = 'save-row ui-action-button';
    saveButton.textContent = t('urls.button.save', 'Save');
    saveButton.dataset.defaultLabel = t('urls.button.save', 'Save');

    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-row ui-action-button';
    deleteButton.textContent = t('urls.button.delete', 'Delete');
    deleteButton.dataset.defaultLabel = t('urls.button.delete', 'Delete');

    actionsCell.appendChild(saveButton);
    actionsCell.appendChild(deleteButton);

    tr.append(urlCell, recipesCell, activeCell, hasRecipeCell, statusCell, actionsCell);

    saveButton.addEventListener('click', async () => {
      setError('');
      setStatus('');
      setButtonState(saveButton, 'saving', {
        idleLabel: t('urls.button.save', 'Save'),
        loadingLabel: t('urls.button.saving', 'Saving...'),
        successLabel: t('urls.button.saved', 'Saved'),
        errorLabel: t('urls.button.error', 'Failed'),
      });
      try {
        const url = tr.querySelector('[data-field="URL"]').value.trim();
        const recipeIds = Array.from(tr.querySelector('[data-field="recipe_ids"]').selectedOptions)
          .map((opt) => opt.value.trim())
          .filter(Boolean);
        const active = tr.querySelector('[data-field="active"]').checked;
        const payload = await callApi('/api/seed-urls/row-upsert', 'POST', {
          domain: domainInput.value,
          row: { url, recipe_ids: recipeIds, active },
        });
        setButtonState(saveButton, 'saved', {
          idleLabel: t('urls.button.save', 'Save'),
          loadingLabel: t('urls.button.saving', 'Saving...'),
          successLabel: t('urls.button.saved', 'Saved'),
          errorLabel: t('urls.button.error', 'Failed'),
        });
        setStatus(t('urls.status.saved', 'Row saved successfully.'), 'success');
        clearTimeout(saveStateTimers.get(saveButton));
        const timer = setTimeout(() => {
          setButtonState(saveButton, 'idle', {
            idleLabel: t('urls.button.save', 'Save'),
            loadingLabel: t('urls.button.saving', 'Saving...'),
            successLabel: t('urls.button.saved', 'Saved'),
            errorLabel: t('urls.button.error', 'Failed'),
          });
          saveStateTimers.delete(saveButton);
        }, SAVE_SUCCESS_TIMEOUT_MS);
        saveStateTimers.set(saveButton, timer);
        render(payload);
      } catch (error) {
        setButtonState(saveButton, 'error', {
          idleLabel: t('urls.button.save', 'Save'),
          loadingLabel: t('urls.button.saving', 'Saving...'),
          successLabel: t('urls.button.saved', 'Saved'),
          errorLabel: t('urls.button.error', 'Failed'),
        });
        setError(error.message || t('urls.errors.request_failed', 'Request failed'));
        setStatus(t('urls.status.save_failed', 'Save failed.'), 'error');
        setTimeout(() => {
          setButtonState(saveButton, 'idle', {
            idleLabel: t('urls.button.save', 'Save'),
            loadingLabel: t('urls.button.saving', 'Saving...'),
            successLabel: t('urls.button.saved', 'Saved'),
            errorLabel: t('urls.button.error', 'Failed'),
          });
        }, ACTIVATION_TIMEOUT_MS);
      }
    });

    deleteButton.addEventListener('click', async () => {
      setError('');
      setStatus('');
      setButtonState(deleteButton, 'loading', {
        idleLabel: t('urls.button.delete', 'Delete'),
        loadingLabel: t('urls.button.deleting', 'Deleting...'),
        activatedLabel: t('urls.button.deleted', 'Deleted'),
        errorLabel: t('urls.button.error', 'Failed'),
      });
      try {
        const url = tr.querySelector('[data-field="URL"]').value.trim();
        const payload = await callApi('/api/seed-urls/delete', 'POST', { domain: domainInput.value, url });
        setStatus(t('urls.status.deleted', 'Row deleted.'), 'success');
        render(payload);
      } catch (error) {
        setButtonState(deleteButton, 'error', {
          idleLabel: t('urls.button.delete', 'Delete'),
          loadingLabel: t('urls.button.deleting', 'Deleting...'),
          activatedLabel: t('urls.button.deleted', 'Deleted'),
          errorLabel: t('urls.button.error', 'Failed'),
        });
        setError(error.message || t('urls.errors.request_failed', 'Request failed'));
        setStatus(t('urls.status.delete_failed', 'Delete failed.'), 'error');
        setTimeout(() => {
          setButtonState(deleteButton, 'idle', {
            idleLabel: t('urls.button.delete', 'Delete'),
            loadingLabel: t('urls.button.deleting', 'Deleting...'),
            activatedLabel: t('urls.button.deleted', 'Deleted'),
            errorLabel: t('urls.button.error', 'Failed'),
          });
        }, ACTIVATION_TIMEOUT_MS);
      }
    });

    bindDirtyReset(tr, saveButton);
    savedUrlsBody.appendChild(tr);
  }
}

async function load() {
  setError('');
  setStatus('');
  setButtonState(loadButton, 'loading', {
    idleLabel: t('urls.load', 'Load'),
    loadingLabel: t('urls.button.loading', 'Loading...'),
    activatedLabel: t('urls.button.loaded', 'Loaded'),
    errorLabel: t('urls.button.error', 'Failed'),
  });
  try {
    recipes = (await callApi(`/api/recipes?domain=${encodeURIComponent(domainInput.value)}`, 'GET')).recipes || [];
    const data = await callApi(`/api/seed-urls?domain=${encodeURIComponent(domainInput.value)}`, 'GET');
    render(data);
    markButtonActivated(loadButton, {
      idleLabel: t('urls.load', 'Load'),
      loadingLabel: t('urls.button.loading', 'Loading...'),
      activatedLabel: t('urls.button.loaded', 'Loaded'),
      errorLabel: t('urls.button.error', 'Failed'),
    });
    setStatus(t('urls.status.loaded', 'URLs loaded.'), 'success');
  } catch (error) {
    setButtonState(loadButton, 'error', {
      idleLabel: t('urls.load', 'Load'),
      loadingLabel: t('urls.button.loading', 'Loading...'),
      activatedLabel: t('urls.button.loaded', 'Loaded'),
      errorLabel: t('urls.button.error', 'Failed'),
    });
    setError(error.message || t('urls.errors.load_failed', 'Failed to load'));
    setStatus(t('urls.status.load_failed', 'Load failed.'), 'error');
    setTimeout(() => setButtonState(loadButton, 'idle', { idleLabel: t('urls.load', 'Load') }), ACTIVATION_TIMEOUT_MS);
  }
}

async function mutate(path, payload, button, labels) {
  setError('');
  setStatus('');
  setButtonState(button, 'loading', labels);
  try {
    const method = path === '/api/seed-urls' ? 'PUT' : 'POST';
    const data = await callApi(path, method, payload);
    render(data);
    markButtonActivated(button, labels);
    setStatus(t('urls.status.updated', 'Changes applied.'), 'success');
  } catch (error) {
    setButtonState(button, 'error', labels);
    setError(error.message || t('urls.errors.request_failed', 'Request failed'));
    setStatus(t('urls.status.update_failed', 'Action failed.'), 'error');
    setTimeout(() => setButtonState(button, 'idle', labels), ACTIVATION_TIMEOUT_MS);
  }
}

loadButton.classList.add('ui-action-button');
replaceButton.classList.add('ui-action-button');
addButton.classList.add('ui-action-button');
clearButton.classList.add('ui-action-button');

loadButton.addEventListener('click', load);
replaceButton.addEventListener('click', () => mutate('/api/seed-urls', { domain: domainInput.value, urls_multiline: urlsMultiline.value }, replaceButton, {
  idleLabel: t('urls.replace', 'Replace list'),
  loadingLabel: t('urls.button.applying', 'Applying...'),
  activatedLabel: t('urls.button.applied', 'Applied'),
  errorLabel: t('urls.button.error', 'Failed'),
}));
addButton.addEventListener('click', () => mutate('/api/seed-urls/add', { domain: domainInput.value, urls_multiline: urlsMultiline.value }, addButton, {
  idleLabel: t('urls.add', 'Add to list'),
  loadingLabel: t('urls.button.adding', 'Adding...'),
  activatedLabel: t('urls.button.added', 'Added'),
  errorLabel: t('urls.button.error', 'Failed'),
}));
clearButton.addEventListener('click', () => mutate('/api/seed-urls/clear', { domain: domainInput.value }, clearButton, {
  idleLabel: t('urls.clear', 'Clear'),
  loadingLabel: t('urls.button.clearing', 'Clearing...'),
  activatedLabel: t('urls.button.cleared', 'Cleared'),
  errorLabel: t('urls.button.error', 'Failed'),
}));

document.addEventListener('pw:i18n:ready', load);
