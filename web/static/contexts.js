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

async function saveReview(domain, runId, row, statusValue) {
  const payload = {
    domain,
    run_id: runId,
    capture_context_id: row.capture_context_id,
    language: row.language || 'en',
    status: statusValue,
    reviewer: 'operator',
    timestamp: new Date().toISOString(),
  };
  const response = await fetch('/api/capture/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await safeReadPayload(response);
  if (!response.ok) throw new Error(data.error || 'Failed to save review');
}

async function loadContexts() {
  const { domain, runId } = queryValues();
  document.getElementById('backToRunHub').href = `/workflow?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('openIssuesLink').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('openPullsLink').href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  if (!domain || !runId) {
    contextSetStatus('Missing required query params: domain and run_id', 'error');
    return;
  }
  contextSetStatus('Loading contexts…');
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
    const reviewStatus = (row.review_status || {}).status || '';
    tr.innerHTML = `<td>${row.url || ''}</td><td>${row.language || ''}</td><td>${row.state || ''}</td><td>${row.viewport_kind || ''}</td><td>${row.user_tier || ''}</td><td>${row.elements_count || 0}</td><td>${screenshot}</td><td></td>`;
    const controls = document.createElement('div');
    controls.innerHTML = `<select><option value="valid">valid</option><option value="blocked_by_overlay">blocked_by_overlay</option><option value="not_found">not_found</option></select> <button type="button">Save</button> <span>${reviewStatus}</span>`;
    const select = controls.querySelector('select');
    const button = controls.querySelector('button');
    if (reviewStatus) select.value = reviewStatus;
    button.addEventListener('click', async () => {
      try {
        await saveReview(domain, runId, row, select.value);
        contextSetStatus(`Saved review for ${row.capture_context_id}`, 'ok');
        await loadContexts();
      } catch (err) {
        contextSetStatus(err.message, 'error');
      }
    });
    tr.lastElementChild.appendChild(controls);
    contextsBody.appendChild(tr);
  }
  contextsTable.classList.remove('hidden');
}

loadContexts();
