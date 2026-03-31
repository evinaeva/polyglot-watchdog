const applyBtn = document.getElementById('applyIssueQuery');
const exportCsvBtn = document.getElementById('exportIssuesCsv');
const queryInput = document.getElementById('issueQuery');
const domainInput = document.getElementById('domainInput');
const persistedResultSelect = document.getElementById('persistedResultSelect');
const refreshPersistedResults = document.getElementById('refreshPersistedResults');
const runIdInput = document.getElementById('runIdInput');
const languageFilter = document.getElementById('languageFilter');
const severityFilter = document.getElementById('severityFilter');
const typeFilter = document.getElementById('typeFilter');
const stateFilter = document.getElementById('stateFilter');
const urlFilter = document.getElementById('urlFilter');
const domainFilter = document.getElementById('domainFilter');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');
const issueStatus = document.getElementById('issueStatus');
const issueCount = document.getElementById('issueCount');
const issuesBackToCheckLanguages = document.getElementById('issuesBackToCheckLanguages');
const workflowContextSummary = document.getElementById('workflowContextSummary');

const workflowContext = {
  domain: '',
  runId: '',
};
let persistedResults = [];
const tallinnDateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Tallinn',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

function queryParamsFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return {
    domain: (params.get('domain') || '').trim(),
    runId: (params.get('run_id') || '').trim(),
  };
}

function setStatus(message, cls = '') {
  issueStatus.className = cls;
  issueStatus.textContent = message || '';
}

function clearIssuesView() {
  tbody.innerHTML = '';
  table.classList.add('hidden');
  issueCount.textContent = '';
  issueCount.classList.add('hidden');
}

function formatUtcTimestampForUi(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  const parts = tallinnDateTimeFormatter.formatToParts(parsed);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
}

function activeDomain() {
  return (domainInput.value || workflowContext.domain || '').trim();
}

function activeRunId() {
  return (runIdInput.value || workflowContext.runId || '').trim();
}

function buildParams() {
  return new URLSearchParams({
    domain: activeDomain(),
    run_id: activeRunId(),
    q: (queryInput.value || '').trim(),
    language: (languageFilter.value || '').trim(),
    severity: (severityFilter.value || '').trim(),
    type: (typeFilter.value || '').trim(),
    state: (stateFilter.value || '').trim(),
    url: (urlFilter.value || '').trim(),
    domain_filter: (domainFilter.value || '').trim(),
  });
}

function updateWorkflowSummary() {
  if (!workflowContextSummary) return;
  const domain = activeDomain();
  const runId = activeRunId();
  if (!domain && !runId) {
    workflowContextSummary.textContent = 'Workflow context: none (provide filters and click Apply).';
    return;
  }
  const contextParts = [];
  if (domain) contextParts.push(`domain: ${domain}`);
  if (runId) contextParts.push(`run: ${runId}`);
  workflowContextSummary.textContent = `Workflow context: ${contextParts.join(' · ')}.`;
}

function syncDefaultsFromQuery() {
  const { domain, runId } = queryParamsFromLocation();
  workflowContext.domain = domain;
  workflowContext.runId = runId;
  domainInput.value = domain;
  runIdInput.value = '';

  const params = new URLSearchParams();
  if (workflowContext.domain) params.set('domain', workflowContext.domain);
  if (workflowContext.runId) params.set('run_id', workflowContext.runId);
  const hasWorkflowContext = Boolean(workflowContext.domain || workflowContext.runId);
  const basePath = hasWorkflowContext ? '/check-languages' : '/pulls';
  issuesBackToCheckLanguages.href = `${basePath}${params.toString() ? `?${params.toString()}` : ''}`;

  updateWorkflowSummary();
}

function resultOptionLabel(result) {
  const runId = String((result || {}).run_id || '').trim();
  const createdAt = formatUtcTimestampForUi(result.created_at);
  const displayLabel = String((result || {}).display_label || '').trim();
  if (createdAt && displayLabel && displayLabel !== runId) return `${createdAt} · ${displayLabel} · ${runId}`;
  if (createdAt) return `${createdAt} · ${runId}`;
  if (displayLabel && displayLabel !== runId) return `${displayLabel} · ${runId}`;
  return runId;
}

function renderPersistedResultOptions(selectedRunId = '') {
  if (!persistedResultSelect) return;
  persistedResultSelect.innerHTML = '';
  if (!persistedResults.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No persisted results available';
    persistedResultSelect.appendChild(option);
    persistedResultSelect.disabled = true;
    return;
  }
  persistedResultSelect.disabled = false;
  const hasPreferred = selectedRunId && persistedResults.some((row) => String(row.run_id || '') === selectedRunId);
  const preferredRunId = hasPreferred ? selectedRunId : String((persistedResults[0] || {}).run_id || '').trim();
  if (selectedRunId && !hasPreferred) {
    const option = document.createElement('option');
    option.value = selectedRunId;
    option.textContent = `${selectedRunId} · current selection`;
    option.selected = true;
    persistedResultSelect.appendChild(option);
  }
  for (const result of persistedResults) {
    const runId = String(result.run_id || '').trim();
    if (!runId) continue;
    const option = document.createElement('option');
    option.value = runId;
    option.textContent = resultOptionLabel(result);
    option.selected = !selectedRunId || hasPreferred ? runId === preferredRunId : false;
    persistedResultSelect.appendChild(option);
  }
  if (selectedRunId && !hasPreferred) {
    runIdInput.value = selectedRunId;
    return;
  }
  if (preferredRunId) runIdInput.value = preferredRunId;
}

async function loadPersistedResults(preferredRunId = '') {
  const domain = activeDomain();
  persistedResults = [];
  renderPersistedResultOptions('');
  if (!domain) return;
  const response = await fetch(`/api/issues/results?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `Failed to load persisted results (${response.status})`);
  const rows = Array.isArray(payload.results) ? payload.results : [];
  persistedResults = rows;
  renderPersistedResultOptions(preferredRunId);
}

function issueLabel(issue) {
  return issue.message || issue.category || issue.id || '';
}

async function loadIssues() {
  updateWorkflowSummary();
  setStatus('Loading…');
  issueCount.classList.add('hidden');
  tbody.innerHTML = '';
  const response = await fetch(`/api/issues?${buildParams().toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    table.classList.add('hidden');
    setStatus('Not ready: issues.json artifact is missing. Run phase 6 or wait for pipeline.', 'warning');
    return;
  }
  if (!response.ok) {
    table.classList.add('hidden');
    setStatus(payload.error || `Issues query failed (${response.status})`, 'error');
    return;
  }
  const issues = payload.issues || [];
  issueCount.textContent = `Count: ${payload.count || 0}`;
  issueCount.classList.remove('hidden');
  if (!issues.length) {
    table.classList.add('hidden');
    setStatus('No issues found for current filters.', 'empty');
    return;
  }
  setStatus('Issues loaded.', 'ok');
  for (const issue of issues) {
    const tr = document.createElement('tr');
    const detailHref = `/issues/detail?${new URLSearchParams({
      domain: activeDomain(),
      run_id: activeRunId(),
      id: String(issue.id || ''),
    }).toString()}`;
    tr.innerHTML = `<td>${issueLabel(issue)}</td><td>${issue.evidence?.url || ''}</td><td>${issue.language || ''}</td><td>${issue.severity || ''}</td><td><a href="${detailHref}">Open details</a></td>`;
    tbody.appendChild(tr);
  }
  table.classList.remove('hidden');
}

applyBtn.addEventListener('click', () => {
  const params = buildParams();
  window.history.replaceState({}, '', `/?${params.toString()}`);
  updateWorkflowSummary();
  loadIssues().catch((err) => setStatus(err.message, 'error'));
});

if (runIdInput) {
  runIdInput.addEventListener('input', () => {
    updateWorkflowSummary();
  });
}

if (domainInput) {
  domainInput.addEventListener('input', () => {
    updateWorkflowSummary();
    const preferredRunId = String(workflowContext.runId || '').trim();
    loadPersistedResults(preferredRunId)
      .then(() => {
        if (!persistedResults.length) {
          clearIssuesView();
          setStatus('No persisted issue results found for this domain.', 'empty');
          return;
        }
        loadIssues().catch((err) => setStatus(err.message, 'error'));
      })
      .catch((err) => setStatus(err.message, 'error'));
  });
}

if (persistedResultSelect) {
  persistedResultSelect.addEventListener('change', () => {
    runIdInput.value = String(persistedResultSelect.value || '').trim();
    updateWorkflowSummary();
    const params = buildParams();
    window.history.replaceState({}, '', `/?${params.toString()}`);
    loadIssues().catch((err) => setStatus(err.message, 'error'));
  });
}

if (refreshPersistedResults) {
  refreshPersistedResults.addEventListener('click', () => {
    const previousRunId = activeRunId();
    setStatus('Loading persisted results…');
    loadPersistedResults(previousRunId)
      .then(() => {
        if (!persistedResults.length) {
          clearIssuesView();
          setStatus('No persisted issue results found for this domain.', 'empty');
          return;
        }
        const nextRunId = activeRunId();
        if (nextRunId !== previousRunId) {
          loadIssues().catch((err) => setStatus(err.message, 'error'));
          return;
        }
        setStatus('Persisted issue results loaded.', 'ok');
      })
      .catch((err) => setStatus(err.message, 'error'));
  });
}

if (exportCsvBtn) {
  exportCsvBtn.addEventListener('click', async () => {
    const params = buildParams();
    params.set('format', 'csv');
    const response = await fetch(`/api/issues/export?${params.toString()}`);
    if (!response.ok) {
      const payload = await safeReadPayload(response);
      setStatus(payload.error || `Export failed (${response.status})`, 'error');
      return;
    }
    const text = await response.text();
    const blob = new Blob([text], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'issues-export.csv';
    a.click();
    URL.revokeObjectURL(url);
  });
}

syncDefaultsFromQuery();
loadPersistedResults()
  .then(() => {
    if (activeDomain() && activeRunId()) return loadIssues();
    if (activeDomain() && !persistedResults.length) {
      clearIssuesView();
      setStatus('No persisted issue results found for this domain.', 'empty');
    }
    return null;
  })
  .catch((err) => setStatus(err.message, 'error'));
