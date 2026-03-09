const PAGE_SIZE = 20;
let allRows = [];
let filteredRows = [];
let currentPage = 1;

const domainDropdown = document.getElementById('domainDropdown');
const collectPullsButton = document.getElementById('collectPullsButton');
const runIdInput = document.getElementById('runIdInput');
const pullRows = document.getElementById('pullRows');
const pageLabel = document.getElementById('pageLabel');
const prevPage = document.getElementById('prevPage');
const nextPage = document.getElementById('nextPage');
const pullError = document.getElementById('pullError');

const urlFilter = document.getElementById('urlFilter');
const stateFilter = document.getElementById('stateFilter');
const languageFilter = document.getElementById('languageFilter');
const viewportFilter = document.getElementById('viewportFilter');
const tierFilter = document.getElementById('tierFilter');

const DECISIONS = {
  eligible: 'ALWAYS_COLLECT',
  exclude: 'IGNORE_ENTIRE_ELEMENT',
  'needs-fix': 'MASK_VARIABLE',
};

function setPullError(message) {
  pullError.textContent = message || '';
  pullError.classList.toggle('hidden', !message);
}

function applyFilters() {
  const urlText = urlFilter.value.trim().toLowerCase();
  const state = stateFilter.value.trim().toLowerCase();
  const language = languageFilter.value.trim().toLowerCase();
  const viewport = viewportFilter.value.trim().toLowerCase();
  const tier = tierFilter.value.trim().toLowerCase();
  filteredRows = allRows.filter((row) => {
    if (urlText && !String(row.url || '').toLowerCase().includes(urlText)) return false;
    if (state && state !== String(row.state || '').toLowerCase()) return false;
    if (language && language !== String(row.language || '').toLowerCase()) return false;
    if (viewport && viewport !== String(row.viewport_kind || '').toLowerCase()) return false;
    if (tier && tier !== String(row.user_tier || '').toLowerCase()) return false;
    return true;
  });
  currentPage = 1;
  renderRows();
}

function decisionLabel(ruleType) {
  if (ruleType === 'ALWAYS_COLLECT') return 'eligible';
  if (ruleType === 'IGNORE_ENTIRE_ELEMENT') return 'exclude';
  if (ruleType === 'MASK_VARIABLE') return 'needs-fix';
  return '';
}

function renderRows() {
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const rows = filteredRows.slice(start, start + PAGE_SIZE);
  pullRows.innerHTML = '';

  for (const row of rows) {
    const tr = document.createElement('tr');
    const decision = decisionLabel(row.decision);
    const notFound = row.not_found ? 'NOT FOUND (rerun)' : '';
    tr.innerHTML = `
      <td>${row.item_id || ''}</td>
      <td>${row.url || ''}</td>
      <td>${row.state || ''}</td>
      <td>${row.language || ''}</td>
      <td>${row.viewport_kind || ''}</td>
      <td>${row.user_tier || ''}</td>
      <td>${row.element_type || ''}</td>
      <td>${row.text || ''}</td>
      <td>${notFound}</td>
      <td>
        <select data-item-id="${row.item_id}" class="decision-select">
          <option value="" ${decision === '' ? 'selected' : ''}>--</option>
          <option value="eligible" ${decision === 'eligible' ? 'selected' : ''}>eligible</option>
          <option value="exclude" ${decision === 'exclude' ? 'selected' : ''}>exclude</option>
          <option value="needs-fix" ${decision === 'needs-fix' ? 'selected' : ''}>needs-fix</option>
        </select>
      </td>`;
    pullRows.appendChild(tr);
  }

  pageLabel.textContent = `Page ${currentPage} / ${totalPages}`;
  bindRowInteractions();
}

function bindRowInteractions() {
  document.querySelectorAll('.decision-select').forEach((select) => {
    select.addEventListener('change', async (event) => {
      const itemId = event.target.getAttribute('data-item-id');
      const selected = event.target.value;
      const ruleType = DECISIONS[selected] || '';
      if (!ruleType) return;
      const row = allRows.find((entry) => entry.item_id === itemId);
      await fetch('/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: domainDropdown.value,
          run_id: (runIdInput.value || '').trim(),
          item_id: itemId,
          url: row?.url || '',
          state: row?.state || '',
          language: row?.language || '',
          viewport_kind: row?.viewport_kind || '',
          user_tier: row?.user_tier || null,
          rule_type: ruleType,
        }),
      });
      if (row) row.decision = ruleType;
    });
  });
}

async function loadDomains() {
  const response = await fetch('/api/domains');
  const payload = await response.json();
  domainDropdown.innerHTML = '';
  for (const domain of payload.items || []) {
    const option = document.createElement('option');
    option.value = domain;
    option.textContent = domain;
    domainDropdown.appendChild(option);
  }
}

async function loadPullRows() {
  const domain = domainDropdown.value;
  const runId = (runIdInput.value || '').trim();
  if (!runId) {
    setPullError('run_id is required');
    allRows = [];
    filteredRows = [];
    renderRows();
    return;
  }
  setPullError('');
  const params = new URLSearchParams({
    domain,
    run_id: runId,
    url: urlFilter.value,
    state: stateFilter.value,
    language: languageFilter.value,
    viewport_kind: viewportFilter.value,
    user_tier: tierFilter.value,
  });
  const response = await fetch(`/api/pulls?${params.toString()}`);
  const payload = await response.json();
  if (!response.ok) {
    setPullError(payload.error || `Failed to load pulls (${response.status})`);
    allRows = [];
    filteredRows = [];
    renderRows();
    return;
  }
  allRows = (payload.rows || []).sort((a, b) => String(a.item_id || '').localeCompare(String(b.item_id || '')));
  applyFilters();
}

collectPullsButton.addEventListener('click', loadPullRows);
prevPage.addEventListener('click', () => { currentPage = Math.max(1, currentPage - 1); renderRows(); });
nextPage.addEventListener('click', () => { const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE)); currentPage = Math.min(totalPages, currentPage + 1); renderRows(); });
[urlFilter, stateFilter, languageFilter, viewportFilter, tierFilter].forEach((input) => {
  input.addEventListener('input', applyFilters);
  input.addEventListener('change', applyFilters);
});

document.addEventListener('pw:i18n:ready', () => { loadDomains(); renderRows(); });
