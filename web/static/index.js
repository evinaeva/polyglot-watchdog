const applyBtn = document.getElementById('applyIssueQuery');
const exportBtn = document.getElementById('exportIssues');
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
const issueError = document.getElementById('issueError');
const issueDetail = document.getElementById('issueDetail');

function setError(message) {
  issueError.textContent = message || '';
  issueError.classList.toggle('hidden', !message);
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

async function loadIssueDetail(issueId) {
  const params = new URLSearchParams({
    domain: (domainInput.value || '').trim(),
    run_id: (runIdInput.value || '').trim(),
    id: issueId,
  });
  const response = await fetch(`/api/issues/detail?${params.toString()}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Issue detail failed (${response.status})`);
  const dd = data.drilldown || {};
  issueDetail.innerHTML = `<h3>Issue drill-down</h3><pre>${JSON.stringify({
    issue: data.issue,
    screenshot_uri: dd.screenshot_uri || '',
    page: dd.page || null,
    element: dd.element || null,
    artifact_refs: dd.artifact_refs || {},
  }, null, 2)}</pre>`;
}

async function loadIssues() {
  try {
    setError('');
    issueDetail.innerHTML = '';
    const response = await fetch(`/api/issues?${buildParams().toString()}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Issues query failed (${response.status})`);
    const issues = payload.issues || [];
    tbody.innerHTML = '';
    for (const issue of issues) {
      const tr = document.createElement('tr');
      const btn = document.createElement('button');
      btn.textContent = 'Open';
      btn.addEventListener('click', async () => {
        try { await loadIssueDetail(issue.id || ''); } catch (err) { setError(err.message); }
      });
      tr.innerHTML = `<td>${issue.id || ''}</td><td>${issue.category || ''}</td><td>${issue.evidence?.url || ''}</td><td>${issue.message || ''}</td><td>${issue.severity || ''}</td><td>${issue.capture_context_id || issue.evidence?.item_id || ''}</td><td></td>`;
      tr.lastElementChild.appendChild(btn);
      tbody.appendChild(tr);
    }
    table.classList.remove('hidden');
  } catch (err) {
    setError(err.message);
    tbody.innerHTML = '';
    table.classList.remove('hidden');
  }
}

applyBtn.addEventListener('click', loadIssues);
exportBtn.addEventListener('click', async () => {
  const response = await fetch(`/api/issues/export?${buildParams().toString()}`);
  const payload = await response.json();
  const blob = new Blob([JSON.stringify(payload.issues || [], null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'issues-export.json';
  a.click();
  URL.revokeObjectURL(url);
});

exportCsvBtn.addEventListener('click', async () => {
  const params = buildParams();
  params.set('format', 'csv');
  const response = await fetch(`/api/issues/export?${params.toString()}`);
  const text = await response.text();
  const blob = new Blob([text], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'issues-export.csv';
  a.click();
  URL.revokeObjectURL(url);
});
