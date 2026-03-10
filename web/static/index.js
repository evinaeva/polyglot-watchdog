const applyBtn = document.getElementById('applyIssueQuery');
const exportCsvBtn = document.getElementById('exportIssuesCsv');
const queryInput = document.getElementById('issueQuery');
const domainInput = document.getElementById('domainInput');
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
const issuesBackToRunHub = document.getElementById('issuesBackToRunHub');


function queryParamsFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return { domain: (params.get('domain') || '').trim(), runId: (params.get('run_id') || '').trim() };
}

function setStatus(message, cls = '') {
  issueStatus.className = cls;
  issueStatus.textContent = message || '';
}

function buildParams() {
  return new URLSearchParams({
    domain: (domainInput.value || '').trim(),
    run_id: (runIdInput.value || '').trim(),
    q: (queryInput.value || '').trim(),
    language: (languageFilter.value || '').trim(),
    severity: (severityFilter.value || '').trim(),
    type: (typeFilter.value || '').trim(),
    state: (stateFilter.value || '').trim(),
    url: (urlFilter.value || '').trim(),
    domain_filter: (domainFilter.value || '').trim(),
  });
}

function syncDefaultsFromQuery() {
  const { domain, runId } = queryParamsFromLocation();
  domainInput.value = domain;
  runIdInput.value = runId;
  issuesBackToRunHub.href = `/runs?${new URLSearchParams({ domain }).toString()}`;
}

async function loadIssues() {
  setStatus('Loading…');
  issueCount.classList.add('hidden');
  tbody.innerHTML = '';
  const response = await fetch(`/api/issues?${buildParams().toString()}`);
  const payload = await safeReadPayload(response)
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
    const detailHref = `/issues/detail?${new URLSearchParams({ domain: domainInput.value.trim(), run_id: runIdInput.value.trim(), id: String(issue.id || '') }).toString()}`;
    tr.innerHTML = `<td>${issue.id || ''}</td><td>${issue.category || ''}</td><td>${issue.evidence?.url || ''}</td><td>${issue.message || ''}</td><td>${issue.severity || ''}</td><td>${issue.language || ''}</td><td>${issue.state || ''}</td><td><a href="${detailHref}">Open detail</a></td>`;
    tbody.appendChild(tr);
  }
  table.classList.remove('hidden');
}

applyBtn.addEventListener('click', () => {
  const params = buildParams();
  window.history.replaceState({}, '', `/?${params.toString()}`);
  loadIssues().catch((err) => setStatus(err.message, 'error'));
});

exportCsvBtn.addEventListener('click', async () => {
  const params = buildParams();
  params.set('format', 'csv');
  const response = await fetch(`/api/issues/export?${params.toString()}`);
  if (!response.ok) {
    const payload = await safeReadPayload(response)
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

syncDefaultsFromQuery();
if (domainInput.value && runIdInput.value) {
  loadIssues().catch((err) => setStatus(err.message, 'error'));
}
