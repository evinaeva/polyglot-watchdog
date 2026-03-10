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

async function loadPulls() {
  const { domain, runId } = pullsQuery();
  document.getElementById('pullsBackToRunHub').href = `/workflow?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('pullsOpenContexts').href = `/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('pullsOpenIssues').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  if (!domain || !runId) {
    pullsTable.classList.add('hidden');
    setPullsStatus('Missing required query params: domain and run_id.', 'error');
    return;
  }

  setPullsStatus('Loading items/pulls…');
  const response = await fetch(`/api/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    pullsTable.classList.add('hidden');
    setPullsStatus(`Not ready: ${payload.error}.`, 'warning');
    return;
  }
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
    tr.innerHTML = `<td>${row.item_id || ''}</td><td>${row.url || ''}</td><td>${row.language || ''}</td><td>${row.state || ''}</td><td>${row.element_type || ''}</td><td>${row.decision || ''}</td><td></td>`;
    const controls = document.createElement('div');
    controls.innerHTML = `<select><option value="eligible">eligible</option><option value="exclude">exclude</option><option value="needs-fix">needs-fix</option></select> <button type="button">Save</button>`;
    const select = controls.querySelector('select');
    const button = controls.querySelector('button');
    button.addEventListener('click', async () => {
      try {
        await saveRule(domain, runId, row, select.value);
        setPullsStatus(`Saved decision for ${row.item_id}.`, 'ok');
        await loadPulls();
      } catch (err) {
        setPullsStatus(err.message, 'error');
      }
    });
    tr.lastElementChild.appendChild(controls);
    pullsBody.appendChild(tr);
  }
  pullsTable.classList.remove('hidden');
}

loadPulls();
