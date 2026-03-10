const wfDomain = document.getElementById('wfDomain');
const wfRun = document.getElementById('wfRun');
const wfLoad = document.getElementById('wfLoad');
const wfRefresh = document.getElementById('wfRefresh');
const wfStartCapture = document.getElementById('wfStartCapture');
const wfGenerateDataset = document.getElementById('wfGenerateDataset');
const wfGenerateIssues = document.getElementById('wfGenerateIssues');
const wfRerunContext = document.getElementById('wfRerunContext');
const wfRerunUrl = document.getElementById('wfRerunUrl');
const wfRerun = document.getElementById('wfRerun');
const wfStatus = document.getElementById('wfStatus');
const wfPayload = document.getElementById('wfPayload');
const wfTransition = document.getElementById('wfTransition');

const wfOpenContexts = document.getElementById('wfOpenContexts');
const wfOpenPulls = document.getElementById('wfOpenPulls');
const wfOpenIssues = document.getElementById('wfOpenIssues');
const wfOpenIssueDetail = document.getElementById('wfOpenIssueDetail');

let lastPayload = null;

function q() {
  const p = new URLSearchParams(window.location.search);
  return { domain: (p.get('domain') || '').trim(), runId: (p.get('run_id') || '').trim() };
}

function setQuery(domain, runId) {
  const p = new URLSearchParams(window.location.search);
  p.set('domain', domain || '');
  if (runId) p.set('run_id', runId); else p.delete('run_id');
  window.history.replaceState({}, '', `/workflow?${p.toString()}`);
}

function setLinks(domain, runId) {
  const qstr = new URLSearchParams({ domain, run_id: runId }).toString();
  wfOpenContexts.href = `/contexts?${qstr}`;
  wfOpenPulls.href = `/pulls?${qstr}`;
  wfOpenIssues.href = `/?${qstr}`;
  const firstId = (((lastPayload || {}).issues || {}).first_issue_id || '').trim();
  wfOpenIssueDetail.href = firstId ? `/issues/detail?${new URLSearchParams({ domain, run_id: runId, id: firstId }).toString()}` : '#';
}

function renderState(status) {
  if (!status) return 'not_started';
  return String(status);
}

function setStatus(msg, cls = '') {
  wfStatus.className = cls;
  wfStatus.textContent = msg;
}

function setActionAvailability(payload) {
  const capture = payload.capture || {};
  const eligible = payload.eligible_dataset || {};
  const captureReady = capture.status === 'ready' || capture.status === 'empty';
  const datasetReady = eligible.status === 'ready' || eligible.status === 'empty';

  wfGenerateDataset.disabled = !captureReady;
  wfGenerateIssues.disabled = !datasetReady;

  if (!captureReady) {
    wfOpenContexts.href = '#';
    wfOpenPulls.href = '#';
    wfOpenIssues.href = '#';
    wfOpenIssueDetail.href = '#';
  }
}

async function loadDomains() {
  const response = await fetch('/api/domains');
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || 'failed to load domains');
  wfDomain.innerHTML = '';
  for (const d of payload.items || []) {
    const o = document.createElement('option');
    o.value = d;
    o.textContent = d;
    wfDomain.appendChild(o);
  }
}

function renderPayload(payload) {
  const summary = {
    seed_urls: renderState(payload.seed_urls?.status),
    run: renderState(payload.run?.status),
    capture: renderState(payload.capture?.status),
    review: renderState(payload.review?.status),
    annotation: renderState(payload.annotation?.status),
    eligible_dataset: renderState(payload.eligible_dataset?.status),
    issues: renderState(payload.issues?.status),
    next_recommended_action: payload.next_recommended_action,
    state_enum: payload.state_enum || [],
  };
  wfPayload.textContent = JSON.stringify(summary, null, 2);
}

async function loadWorkflowStatus() {
  const domain = (wfDomain.value || '').trim();
  const runId = (wfRun.value || '').trim();
  if (!domain || !runId) {
    setStatus('Select domain and run id first.', 'warning');
    return;
  }
  setStatus('Loading workflow status…', '');
  setLinks(domain, runId);
  const response = await fetch(`/api/workflow/status?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) {
    setStatus(payload.error || `Failed to load workflow status (${response.status})`, 'error');
    return;
  }
  lastPayload = payload;
  renderPayload(payload);
  const capture = payload.capture || {};
  if (capture.status === 'failed') {
    const remediation = Array.isArray(capture.remediation) ? capture.remediation.join('; ') : '';
    setStatus(`Capture FAILED: ${capture.error || 'unknown error'}. ${remediation}`.trim(), 'error');
  } else if (capture.status === 'in_progress') {
    setStatus(`Capture in progress. Next action: ${payload.next_recommended_action || 'wait_for_capture'}`, 'warning');
  } else if (capture.status === 'not_ready') {
    setStatus(`Capture not ready. Next action: ${payload.next_recommended_action || 'start_capture'}`, 'warning');
  } else {
    setStatus(`Ready. Next action: ${payload.next_recommended_action || 'none'}`, 'ok');
  }
  setLinks(domain, runId);
}


async function postAction(path, payload) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await safeReadPayload(response);
  if (!response.ok) {
    const detail = data.error || data.message || `${path} failed (${response.status})`;
    wfTransition.textContent = JSON.stringify(data, null, 2);
    throw new Error(detail);
  }
  wfTransition.textContent = JSON.stringify(data, null, 2);
  await loadWorkflowStatus();
}

async function initWorkflow() {
  await loadDomains();
  const query = q();
  if (query.domain) wfDomain.value = query.domain;
  if (query.runId) wfRun.value = query.runId;

  wfLoad.addEventListener('click', async () => {
    setQuery(wfDomain.value.trim(), wfRun.value.trim());
    await loadWorkflowStatus();
  });
  wfRefresh.addEventListener('click', loadWorkflowStatus);

  wfStartCapture.addEventListener('click', async () => {
    const domain = wfDomain.value.trim();
    const runId = wfRun.value.trim();
    await postAction('/api/workflow/start-capture', { domain, run_id: runId, language: 'en', viewport_kind: 'desktop', state: 'baseline' });
    const pollUntil = Date.now() + 30000;
    while (Date.now() < pollUntil) {
      await loadWorkflowStatus();
      const captureState = (((lastPayload || {}).capture || {}).status || '').trim();
      if (['ready', 'empty', 'failed'].includes(captureState)) break;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  });

  wfGenerateDataset.addEventListener('click', async () => {
    await postAction('/api/workflow/generate-eligible-dataset', { domain: wfDomain.value.trim(), run_id: wfRun.value.trim() });
  });

  wfGenerateIssues.addEventListener('click', async () => {
    const domain = wfDomain.value.trim();
    const runId = wfRun.value.trim();
    await postAction('/api/workflow/generate-issues', { domain, run_id: runId, en_run_id: runId });
  });

  wfRerun.addEventListener('click', async () => {
    const domain = wfDomain.value.trim();
    const runId = wfRun.value.trim();
    const url = wfRerunUrl.value.trim();
    const contextId = wfRerunContext.value.trim();
    await postAction('/api/workflow/rerun-context', {
      domain,
      run_id: runId,
      url,
      capture_context_id: contextId,
      viewport_kind: 'desktop',
      state: 'baseline',
      language: 'en',
      user_tier: null,
    });
  });

  if (wfDomain.value && wfRun.value) await loadWorkflowStatus();
}

initWorkflow().catch((err) => setStatus(err.message, 'error'));
