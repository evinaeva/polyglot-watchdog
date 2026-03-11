const domainInput = document.getElementById('domainInput');
const loadButton = document.getElementById('loadButton');
const replaceButton = document.getElementById('replaceButton');
const addButton = document.getElementById('addButton');
const clearButton = document.getElementById('clearButton');
const urlsMultiline = document.getElementById('urlsMultiline');
const updatedAt = document.getElementById('updatedAt');
const savedUrlsBody = document.getElementById('savedUrlsBody');
const errorBox = document.getElementById('errorBox');
let recipes = [];

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

function setError(message) {
  errorBox.textContent = message || '';
  errorBox.classList.toggle('hidden', !message);
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
    saveButton.className = 'save-row';
    saveButton.textContent = 'Save';
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-row';
    deleteButton.textContent = 'Delete';
    actionsCell.appendChild(saveButton);
    actionsCell.appendChild(deleteButton);

    tr.append(urlCell, recipesCell, activeCell, hasRecipeCell, statusCell, actionsCell);

    tr.querySelector('.save-row').addEventListener('click', async () => {
      const url = tr.querySelector('[data-field="URL"]').value.trim();
      const recipeIds = Array.from(tr.querySelector('[data-field="recipe_ids"]').selectedOptions)
        .map((opt) => opt.value.trim())
        .filter(Boolean);
      const active = tr.querySelector('[data-field="active"]').checked;
      const payload = await callApi('/api/seed-urls/row-upsert', 'POST', {
        domain: domainInput.value,
        row: { url, recipe_ids: recipeIds, active },
      });
      render(payload);
    });
    tr.querySelector('.delete-row').addEventListener('click', async () => {
      const url = tr.querySelector('[data-field="URL"]').value.trim();
      const payload = await callApi('/api/seed-urls/delete', 'POST', { domain: domainInput.value, url });
      render(payload);
    });
    savedUrlsBody.appendChild(tr);
  }
}

async function load() {
  setError('');
  try {
    recipes = (await callApi(`/api/recipes?domain=${encodeURIComponent(domainInput.value)}`, 'GET')).recipes || [];
    const data = await callApi(`/api/seed-urls?domain=${encodeURIComponent(domainInput.value)}`, 'GET');
    render(data);
  } catch (error) {
    setError(error.message || 'Failed to load');
  }
}

async function mutate(path, payload) {
  setError('');
  try {
    const method = path === '/api/seed-urls' ? 'PUT' : 'POST';
    const data = await callApi(path, method, payload);
    render(data);
  } catch (error) {
    setError(error.message || 'Request failed');
  }
}

loadButton.addEventListener('click', load);
replaceButton.addEventListener('click', () => mutate('/api/seed-urls', { domain: domainInput.value, urls_multiline: urlsMultiline.value }));
addButton.addEventListener('click', () => mutate('/api/seed-urls/add', { domain: domainInput.value, urls_multiline: urlsMultiline.value }));
clearButton.addEventListener('click', () => mutate('/api/seed-urls/clear', { domain: domainInput.value }));

document.addEventListener('pw:i18n:ready', load);
