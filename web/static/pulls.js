const pullsStatus = document.getElementById('pullsStatus');
const pullsTable = document.getElementById('pullsTable');
const pullsBody = pullsTable.querySelector('tbody');
const pullsUrlSearch = document.getElementById('pullsUrlSearch');
const pullsElementTypeFilter = document.getElementById('pullsElementTypeFilter');
const pullsLanguageSummary = document.getElementById('pullsLanguageSummary');
const pullsWorkflowContextSummary = document.getElementById('pullsWorkflowContextSummary');
const pullsIdHelp = document.getElementById('pullsIdHelp');

let allPullRows = [];

// Defensive fallback: backend /api/pulls already excludes script rows; keep this to avoid leaking script rows in UI if backend regresses.

const DECISION_TO_UI = {
  eligible: 'Keep',
  ALWAYS_COLLECT: 'Keep',
  exclude: 'Ignore',
  IGNORE_ENTIRE_ELEMENT: 'Ignore',
  'needs-fix': 'Needs Fix',
  MASK_VARIABLE: 'Needs Fix',
};

function pullsQuery() {
  const params = new URLSearchParams(window.location.search);
  return { domain: (params.get('domain') || '').trim(), runId: (params.get('run_id') || '').trim() };
}

function setPullsStatus(message, cls = '') {
  pullsStatus.className = cls;
  pullsStatus.textContent = message;
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function decisionToValue(decision) {
  const raw = String(decision || '').trim();
  if (raw === 'ALWAYS_COLLECT') return 'eligible';
  if (raw === 'IGNORE_ENTIRE_ELEMENT') return 'exclude';
  if (raw === 'MASK_VARIABLE') return 'needs-fix';
  if (raw === 'eligible' || raw === 'exclude' || raw === 'needs-fix') return raw;
  return '';
}

function decisionToLabel(decision) {
  return DECISION_TO_UI[String(decision || '').trim()] || '';
}

function updateWorkflowSummary(domain, runId) {
  const parts = [];
  if (domain) parts.push(`domain: ${domain}`);
  if (runId) parts.push(`run: ${runId}`);
  pullsWorkflowContextSummary.textContent = parts.length
    ? `Workflow context: ${parts.join(' · ')}.`
    : 'Workflow context: none.';
}

function updateLanguageSummary(rows) {
  const languages = [...new Set(rows.map((row) => String(row.language || '').trim()).filter(Boolean))].sort();
  if (!languages.length) {
    pullsLanguageSummary.textContent = 'Language: —';
  } else if (languages.length === 1) {
    pullsLanguageSummary.textContent = `Language: ${languages[0]}`;
  } else {
    pullsLanguageSummary.textContent = `Language: Mixed (${languages.join(', ')})`;
  }
  pullsLanguageSummary.classList.remove('hidden');
}

function updateElementTypeFilter(rows) {
  const selected = String(pullsElementTypeFilter.value || '');
  const options = [...new Set(rows.map((row) => String(row.element_type || '').trim()).filter(Boolean))].sort();
  pullsElementTypeFilter.innerHTML = '<option value="">All types</option>';
  for (const type of options) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    pullsElementTypeFilter.appendChild(option);
  }
  if (selected && options.includes(selected)) pullsElementTypeFilter.value = selected;
}

async function saveRule(domain, runId, row, decision) {
  const payload = {
    domain,
    run_id: runId,
    item_id: row.item_id,
    url: row.url,
    decision,
    capture_context_id: row.capture_context_id || '',
    state: row.state || '',
    language: row.language || '',
    viewport_kind: row.viewport_kind || '',
    user_tier: row.user_tier || null,
  };
  const response = await fetch('/api/rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await safeReadPayload(response);
  if (!response.ok) throw new Error(data.message || data.error || 'Failed to save rule');
}

function filteredRows() {
  const query = String(pullsUrlSearch.value || '').trim().toLowerCase();
  const typeFilter = String(pullsElementTypeFilter.value || '').trim();
  return allPullRows.filter((row) => {
    if (query && !String(row.url || '').toLowerCase().includes(query)) return false;
    if (typeFilter && String(row.element_type || '') !== typeFilter) return false;
    return true;
  });
}

function renderRows(domain, runId) {
  const rows = filteredRows();
  const totalCount = allPullRows.length;
  pullsBody.innerHTML = '';

  if (!rows.length) {
    pullsTable.classList.add('hidden');
    setPullsStatus('No items match current filters.', 'empty');
    return;
  }

  for (const row of rows) {
    const tr = document.createElement('tr');
    const selected = decisionToValue(row.decision);
    tr.innerHTML = `
      <td>${escapeHtml(row.url)}</td>
      <td>${escapeHtml(row.item_id)}</td>
      <td>${escapeHtml(row.element_type)}</td>
      <td>${escapeHtml(row.text || '')}</td>
      <td>${escapeHtml(decisionToLabel(row.decision))}</td>
      <td></td>`;

    const controls = document.createElement('div');
    controls.innerHTML = `
      <label>
        <span class="hidden">Decision</span>
        <select>
          <option value="">Choose</option>
          <option value="eligible" ${selected === 'eligible' ? 'selected' : ''}>Keep</option>
          <option value="exclude" ${selected === 'exclude' ? 'selected' : ''}>Ignore</option>
          <option value="needs-fix" ${selected === 'needs-fix' ? 'selected' : ''}>Needs Fix</option>
        </select>
      </label>
      <button type="button">Save selection</button>
      <details>
        <summary>Advanced</summary>
        <div>capture_context_id: ${escapeHtml(row.capture_context_id)}</div>
        <div>viewport_kind: ${escapeHtml(row.viewport_kind)}</div>
        <div>user_tier: ${escapeHtml(row.user_tier)}</div>
      </details>`;

    const select = controls.querySelector('select');
    const button = controls.querySelector('button');
    button.addEventListener('click', async () => {
      if (!select.value) {
        setPullsStatus('Please choose a decision before saving.', 'warning');
        return;
      }
      try {
        await saveRule(domain, runId, row, select.value);
        row.decision = select.value;
        setPullsStatus('Selection saved.', 'ok');
        renderRows(domain, runId);
      } catch (err) {
        setPullsStatus(err.message, 'error');
      }
    });
    tr.lastElementChild.appendChild(controls);
    pullsBody.appendChild(tr);
  }

  pullsTable.classList.remove('hidden');
  setPullsStatus(`Showing ${rows.length} of ${totalCount} items.`, 'ok');
}

async function loadPulls() {
  const { domain, runId } = pullsQuery();
  updateWorkflowSummary(domain, runId);
  const query = new URLSearchParams({ domain, run_id: runId }).toString();

  const primaryLinks = {
    pullsBackToRunHub: `/workflow?${query}`,
    continueCheckLanguages: `/check-languages?${query}`,
  };
  Object.entries(primaryLinks).forEach(([id, href]) => {
    const link = document.getElementById(id);
    if (link) link.href = href;
  });

  const technicalLinks = {
    pullsOpenContexts: `/contexts?${query}`,
    pullsOpenIssues: `/?${query}`,
  };
  Object.entries(technicalLinks).forEach(([id, href]) => {
    const link = document.getElementById(id);
    if (link) link.href = href;
  });

  if (!domain || !runId) {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus('Missing required query params: domain and run_id.', 'error');
    return;
  }

  setPullsStatus('Loading items…');
  const response = await fetch(`/api/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus(`Not ready: ${payload.error}.`, 'warning');
    return;
  }
  if (!response.ok) {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus(payload.error || `Failed to load pulls (${response.status})`, 'error');
    return;
  }

  allPullRows = (payload.rows || []).filter((row) => String((row || {}).element_type || '').toLowerCase() !== 'script');
  updateElementTypeFilter(allPullRows);
  updateLanguageSummary(allPullRows);
  pullsIdHelp.textContent = 'Item/Element ID is generated by compute_item_id in pipeline/interactive_capture.py: a deterministic SHA-1 hash of domain, URL, CSS selector, canonical bbox JSON, and element type (text content is excluded).';

  if (!allPullRows.length) {
    pullsTable.classList.add('hidden');
    setPullsStatus('No items found for this run.', 'empty');
    return;
  }
  renderRows(domain, runId);
}

pullsUrlSearch.addEventListener('input', () => {
  const { domain, runId } = pullsQuery();
  renderRows(domain, runId);
});

pullsElementTypeFilter.addEventListener('change', () => {
  const { domain, runId } = pullsQuery();
  renderRows(domain, runId);
});

loadPulls();
