const contextsStatus = document.getElementById('contextsStatus');
const contextsTable = document.getElementById('contextsTable');
const contextsBody = contextsTable.querySelector('tbody');

function queryValues() {
  const params = new URLSearchParams(window.location.search);
  return { domain: (params.get('domain') || '').trim(), runId: (params.get('run_id') || '').trim() };
}


function contextSetStatus(message, cls = '') {
  contextsStatus.className = cls;
  contextsStatus.textContent = message;
}

async function loadContexts() {
  const { domain, runId } = queryValues();
  document.getElementById('backToRunHub').href = `/runs?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('openIssuesLink').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('openPullsLink').href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  if (!domain || !runId) {
    contextSetStatus('Missing required query params: domain and run_id', 'error');
    return;
  }
  const response = await fetch(`/api/capture/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    contextsTable.classList.add('hidden');
    contextSetStatus('Not ready: page_screenshots artifact is missing. Run capture or wait for pipeline artifacts.', 'warning');
    return;
  }
  if (!response.ok) {
    contextsTable.classList.add('hidden');
    contextSetStatus(payload.error || `Failed to load contexts (${response.status})`, 'error');
    return;
  }
  const contexts = payload.contexts || [];
  contextsBody.innerHTML = '';
  if (!contexts.length) {
    contextsTable.classList.add('hidden');
    contextSetStatus('No contexts found for this run.', 'empty');
    return;
  }
  contextSetStatus(`Loaded ${contexts.length} contexts.`, 'ok');
  for (const row of contexts) {
    const tr = document.createElement('tr');
    const screenshot = row.storage_uri ? `<a href="${row.storage_uri}" target="_blank" rel="noopener">open</a>` : '';
    tr.innerHTML = `<td>${row.url || ''}</td><td>${row.language || ''}</td><td>${row.state || ''}</td><td>${row.viewport_kind || ''}</td><td>${row.user_tier || ''}</td><td>${row.elements_count || 0}</td><td>${screenshot}</td>`;
    contextsBody.appendChild(tr);
  }
  contextsTable.classList.remove('hidden');
}

loadContexts();
