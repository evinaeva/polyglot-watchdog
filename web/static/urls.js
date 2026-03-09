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
  updatedAt.textContent = data.updated_at || '-';
  urlsMultiline.value = urls.map((row) => row.url || '').filter(Boolean).join('\n');
  savedUrlsBody.innerHTML = '';

  for (const row of urls) {
    const tr = document.createElement('tr');
    const hasRecipe = Array.isArray(row.recipe_ids) && row.recipe_ids.length > 0;
    const invalid = !row.url || !/^https?:\/\//.test(row.url);
    tr.innerHTML = `
      <td><input data-field="url" value="${row.url || ''}" /></td>
      <td><input data-field="recipe_ids" value="${(row.recipe_ids || []).join(',')}" placeholder="recipe ids,comma" /></td>
      <td><input type="checkbox" data-field="active" ${row.active !== false ? 'checked' : ''} /></td>
      <td>${hasRecipe ? 'has_recipe' : '-'}</td>
      <td>${invalid ? 'invalid' : 'valid'}</td>
      <td>
        <button class="save-row">Save</button>
        <button class="delete-row">Delete</button>
      </td>`;
    tr.querySelector('.save-row').addEventListener('click', async () => {
      const url = tr.querySelector('[data-field="url"]').value.trim();
      const recipeIds = tr.querySelector('[data-field="recipe_ids"]').value.split(',').map((x) => x.trim()).filter(Boolean);
      const active = tr.querySelector('[data-field="active"]').checked;
      const payload = await callApi('/api/seed-urls/row-upsert', 'POST', {
        domain: domainInput.value,
        row: { url, recipe_ids: recipeIds, active },
      });
      render(payload);
    });
    tr.querySelector('.delete-row').addEventListener('click', async () => {
      const url = tr.querySelector('[data-field="url"]').value.trim();
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
