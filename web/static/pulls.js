const pullsStatus = document.getElementById('pullsStatus');
const pullsTable = document.getElementById('pullsTable');
const pullsBody = pullsTable.querySelector('tbody');

function pullsQuery() {
  const params = new URLSearchParams(window.location.search);
  return { domain: (params.get('domain') || '').trim(), runId: (params.get('run_id') || '').trim() };
}


function setPullsStatus(message, cls = '') {
  pullsStatus.className = cls;
  pullsStatus.textContent = message;
}

async function loadPulls() {
  const { domain, runId } = pullsQuery();
  document.getElementById('pullsBackToRunHub').href = `/runs?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('pullsOpenContexts').href = `/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('pullsOpenIssues').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  const response = await fetch(`/api/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) {
    pullsTable.classList.add('hidden');
    setPullsStatus(payload.error || `Failed to load pulls (${response.status})`, 'error');
    return;
  }
  const rows = payload.rows || [];
  pullsBody.innerHTML = '';
  if (!rows.length) {
    pullsTable.classList.add('hidden');
    setPullsStatus('No items/pulls found for this run.', 'empty');
    return;
  }
  setPullsStatus(`Loaded ${rows.length} items/pulls.`, 'ok');
  for (const row of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.item_id || ''}</td><td>${row.url || ''}</td><td>${row.language || ''}</td><td>${row.state || ''}</td><td>${row.element_type || ''}</td><td>${row.decision || ''}</td>`;
    pullsBody.appendChild(tr);
  }
  pullsTable.classList.remove('hidden');
}

loadPulls();
