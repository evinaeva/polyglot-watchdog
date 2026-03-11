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
const issuesBackToCheckLanguages = document.getElementById('issuesBackToCheckLanguages');
const workflowContextSummary = document.getElementById('workflowContextSummary');

const workflowContext = {
  domain: '',
  runId: '',
};

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
  const checkLanguagesHref = `/check-languages${params.toString() ? `?${params.toString()}` : ''}`;
  const pullsHref = `/pulls${params.toString() ? `?${params.toString()}` : ''}`;
  issuesBackToCheckLanguages.href = checkLanguagesHref;

  fetch(checkLanguagesHref, { method: 'HEAD' })
    .then((response) => {
      if (!response.ok) issuesBackToCheckLanguages.href = pullsHref;
    })
    .catch(() => {
      issuesBackToCheckLanguages.href = pullsHref;
    });

  updateWorkflowSummary();
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
if (activeDomain() && activeRunId()) {
  loadIssues().catch((err) => setStatus(err.message, 'error'));
}
