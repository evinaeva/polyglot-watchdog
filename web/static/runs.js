const domainSelect = document.getElementById('runDomainSelect');
const refreshRunsBtn = document.getElementById('refreshRuns');
const runHubError = document.getElementById('runHubError');
const runsTable = document.getElementById('runsTable');
const runsBody = runsTable.querySelector('tbody');
const selectedRunId = document.getElementById('selectedRunId');
const selectedOpenContexts = document.getElementById('selectedOpenContexts');
const selectedOpenPulls = document.getElementById('selectedOpenPulls');
const selectedOpenIssues = document.getElementById('selectedOpenIssues');
const selectedExportCsv = document.getElementById('selectedExportCsv');

function runHubSetError(message) {
  runHubError.textContent = message || '';
  runHubError.classList.toggle('hidden', !message);
}


function runQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    domain: (params.get('domain') || '').trim(),
    runId: (params.get('run_id') || '').trim(),
  };
}

function runScopedLink(path, domain, runId) {
  return `${path}?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
}

function syncSelectedRunLinks(domain, runId) {
  const enabled = !!(domain && runId);
  selectedRunId.value = runId || '';
  selectedOpenContexts.href = enabled ? runScopedLink('/contexts', domain, runId) : '#';
  selectedOpenPulls.href = enabled ? runScopedLink('/pulls', domain, runId) : '#';
  selectedOpenIssues.href = enabled ? runScopedLink('/', domain, runId) : '#';
  selectedExportCsv.href = enabled
    ? `/api/issues/export?${new URLSearchParams({ domain, run_id: runId, format: 'csv' }).toString()}`
    : '#';
}

function setSelectedRun(runId) {
  const params = new URLSearchParams(window.location.search);
  const domain = (domainSelect.value || '').trim();
  params.set('domain', domain);
  if (runId) params.set('run_id', runId); else params.delete('run_id');
  window.history.replaceState({}, '', `/runs?${params.toString()}`);
  syncSelectedRunLinks(domain, runId);
}

async function loadDomains() {
  const response = await fetch('/api/domains');
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || 'Failed to load domains');
  const items = payload.items || [];
  domainSelect.innerHTML = '';
  for (const domain of items) {
    const option = document.createElement('option');
    option.value = domain;
    option.textContent = domain;
    domainSelect.appendChild(option);
  }
  const selected = runQuery().domain;
  if (selected && items.includes(selected)) domainSelect.value = selected;
}

async function loadRuns() {
  const domain = (domainSelect.value || '').trim();
  if (!domain) {
    runsBody.innerHTML = '';
    runsTable.classList.add('hidden');
    setSelectedRun('');
    return;
  }
  const response = await fetch(`/api/capture/runs?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || 'Failed to load runs');
  const runs = payload.runs || [];
  runsBody.innerHTML = '';
  const selectedFromUrl = runQuery().runId;
  let hasSelected = false;
  for (const run of runs) {
    const runId = String(run.run_id || '');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${runId}</td><td>${run.created_at || ''}</td><td>${(run.jobs || []).length}</td><td></td>`;
    const actions = document.createElement('div');
    actions.innerHTML = [
      `<button type="button" data-run-select="${runId}">Select</button>`,
      `<a href="${runScopedLink('/contexts', domain, runId)}">Open Contexts</a>`,
      `<a href="${runScopedLink('/pulls', domain, runId)}">Open Items/Pulls</a>`,
      `<a href="${runScopedLink('/', domain, runId)}">Open Issues</a>`,
      `<a href="/api/issues/export?${new URLSearchParams({ domain, run_id: runId, format: 'csv' }).toString()}">Export Issues CSV</a>`,
    ].join(' | ');
    tr.lastElementChild.appendChild(actions);
    runsBody.appendChild(tr);
    if (selectedFromUrl && runId === selectedFromUrl) hasSelected = true;
  }
  runsBody.querySelectorAll('button[data-run-select]').forEach((button) => {
    button.addEventListener('click', () => setSelectedRun(button.getAttribute('data-run-select') || ''));
  });
  runsTable.classList.remove('hidden');
  if (hasSelected) syncSelectedRunLinks(domain, selectedFromUrl);
  else if (runs.length) setSelectedRun(String(runs[0].run_id || ''));
  else setSelectedRun('');
}

async function initRunHub() {
  try {
    runHubSetError('');
    await loadDomains();
    await loadRuns();
    domainSelect.addEventListener('change', async () => {
      setSelectedRun('');
      await loadRuns();
    });
    refreshRunsBtn.addEventListener('click', loadRuns);
  } catch (err) {
    runHubSetError(err.message);
  }
}

initRunHub();
