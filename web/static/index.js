const applyBtn = document.getElementById('applyIssueQuery');
const exportBtn = document.getElementById('exportIssues');
const queryInput = document.getElementById('issueQuery');
const domainInput = document.getElementById('domainInput');
const runIdInput = document.getElementById('runIdInput');
const languageFilter = document.getElementById('languageFilter');
const severityFilter = document.getElementById('severityFilter');
const typeFilter = document.getElementById('typeFilter');
const stateFilter = document.getElementById('stateFilter');
const urlFilter = document.getElementById('urlFilter');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');

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
  });
}

async function loadIssues() {
  const response = await fetch(`/api/issues?${buildParams().toString()}`);
  const payload = await response.json();
  const issues = payload.issues || [];

  tbody.innerHTML = '';
  for (const issue of issues) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${issue.id || ''}</td><td>${issue.category || ''}</td><td>${issue.evidence?.url || ''}</td><td>${issue.message || ''}</td>`;
    tbody.appendChild(tr);
  }

  table.classList.remove('hidden');
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
