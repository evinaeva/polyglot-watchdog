const wfDomain = document.getElementById('wfDomain');
const wfRefreshUrls = document.getElementById('wfRefreshUrls');
const wfSavedUrls = document.getElementById('wfSavedUrls');
const wfStartCapture = document.getElementById('wfStartCapture');
const wfGenerateDataset = document.getElementById('wfGenerateDataset');
const wfContinuePulls = document.getElementById('wfContinuePulls');
const wfStatus = document.getElementById('wfStatus');
const wfStatusSummary = document.getElementById('wfStatusSummary');
const wfPayload = document.getElementById('wfPayload');
const wfTransition = document.getElementById('wfTransition');
const wfExistingRuns = document.getElementById('wfExistingRuns');
const wfUseExistingRun = document.getElementById('wfUseExistingRun');
const wfRefreshRuns = document.getElementById('wfRefreshRuns');
const wfRunsStatus = document.getElementById('wfRunsStatus');

let lastPayload = null;
let activeRunId = '';
let pollTimer = null;
let availableRuns = [];

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

function setStatus(message, cls = '') {
  wfStatus.className = cls;
  wfStatus.textContent = message;
}

function readCaptureStatus(payload) {
  return String(((payload || {}).capture || {}).status || '').trim();
}

function isCaptureTerminal(status) {
  return ['ready', 'empty', 'failed'].includes(status);
}

function humanCaptureStatus(status) {
  if (status === 'in_progress') return 'Running';
  if (status === 'ready' || status === 'empty') return 'Completed';
  if (status === 'failed') return 'Failed';
  return 'Not started';
}

function renderStatus(payload) {
  const capture = payload.capture || {};
  const run = payload.run || {};
  const status = readCaptureStatus(payload);
  const human = humanCaptureStatus(status);
  const cls = status === 'failed' ? 'error' : status === 'in_progress' ? 'warning' : status === 'ready' || status === 'empty' ? 'ok' : '';
  setStatus(`Capture status: ${human}`, cls);

  const rows = [
    ['Domain', wfDomain.value || run.domain || '—'],
    ['Capture run', activeRunId || run.run_id || '—'],
    ['Contexts processed', capture.contexts ?? '—'],
    ['Items processed', capture.items ?? '—'],
    ['Worker jobs running', run.jobs_running ?? '—'],
    ['Worker jobs failed', run.jobs_failed ?? '—'],
  ];

  const updatedAt = capture.updated_at || run.updated_at || payload.updated_at || capture.last_update || run.last_update || payload.last_update || capture.last_updated_at || run.last_updated_at || payload.last_updated_at || capture.timestamp || run.timestamp || payload.timestamp;
  if (updatedAt) rows.push(['Last update', updatedAt]);

  wfStatusSummary.innerHTML = rows.map(([label, value]) => `<dt>${label}</dt><dd>${value}</dd>`).join('');
}

function renderTechnicalDetails(payload) {
  wfPayload.textContent = JSON.stringify(payload || {}, null, 2);
}

function setContinueLink(domain, runId, enabled) {
  if (!domain || !runId || !enabled) {
    wfContinuePulls.href = '#';
    wfContinuePulls.setAttribute('aria-disabled', 'true');
    return;
  }
  wfContinuePulls.href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  wfContinuePulls.setAttribute('aria-disabled', 'false');
}

function setActionAvailability(payload) {
  const captureStatus = readCaptureStatus(payload);
  const captureReady = captureStatus === 'ready' || captureStatus === 'empty';

  wfGenerateDataset.disabled = !captureReady;
  setContinueLink(wfDomain.value.trim(), activeRunId, captureReady);
}

function setRunsStatus(message) {
  wfRunsStatus.textContent = message || '';
}

function parseCreatedAt(value) {
  const raw = String(value || '').trim();
  if (!raw) return Number.NaN;
  const ts = Date.parse(raw);
  return Number.isFinite(ts) ? ts : Number.NaN;
}

function sortRunsNewestFirst(runs) {
  return [...runs].sort((a, b) => {
    const aTs = parseCreatedAt((a || {}).created_at);
    const bTs = parseCreatedAt((b || {}).created_at);
    if (Number.isFinite(aTs) && Number.isFinite(bTs) && aTs !== bTs) return bTs - aTs;
    if (Number.isFinite(aTs) && !Number.isFinite(bTs)) return -1;
    if (!Number.isFinite(aTs) && Number.isFinite(bTs)) return 1;
    const aRunId = String((a || {}).run_id || '');
    const bRunId = String((b || {}).run_id || '');
    return bRunId.localeCompare(aRunId);
  });
}

function deriveRunState(run) {
  const jobs = Array.isArray(run.jobs) ? run.jobs : [];
  const hasRunning = jobs.some((job) => {
    const status = String((job || {}).status || '').toLowerCase();
    return status === 'running' || status === 'queued';
  });
  return hasRunning ? 'running' : 'idle';
}

function renderExistingRuns() {
  const selected = activeRunId;
  wfExistingRuns.innerHTML = '';

  if (!availableRuns.length) {
    wfExistingRuns.innerHTML = '<option value="">No runs found</option>';
    wfUseExistingRun.disabled = true;
    setRunsStatus('No existing runs found for this domain yet.');
    return;
  }

  for (const run of availableRuns) {
    const runId = String((run || {}).run_id || '').trim();
    if (!runId) continue;
    const option = document.createElement('option');
    option.value = runId;
    const createdAt = String((run || {}).created_at || '').trim() || 'created time unknown';
    const jobsCount = Array.isArray((run || {}).jobs) ? run.jobs.length : 0;
    option.textContent = `${runId} (${deriveRunState(run)} · jobs: ${jobsCount} · ${createdAt})`;
    wfExistingRuns.appendChild(option);
  }

  if (!wfExistingRuns.options.length) {
    wfExistingRuns.innerHTML = '<option value="">No runs found</option>';
    wfUseExistingRun.disabled = true;
    setRunsStatus('No existing runs found for this domain yet.');
    return;
  }

  if (selected && availableRuns.some((run) => String(run.run_id || '') === selected)) {
    wfExistingRuns.value = selected;
  }

  wfUseExistingRun.disabled = !wfExistingRuns.value;
  setRunsStatus(`Existing runs available: ${availableRuns.length}.`);
}

async function loadExistingRuns() {
  const domain = wfDomain.value.trim();
  availableRuns = [];
  renderExistingRuns();
  if (!domain) return;

  const response = await fetch(`/api/capture/runs?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || 'failed to load runs');

  const runs = Array.isArray(payload.runs) ? payload.runs : [];
  availableRuns = sortRunsNewestFirst(runs);
  renderExistingRuns();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      await loadWorkflowStatus();
      const captureStatus = readCaptureStatus(lastPayload || {});
      if (isCaptureTerminal(captureStatus)) {
        stopPolling();
        await loadExistingRuns();
      }
    } catch (error) {
      setStatus(error.message || 'Failed to refresh status', 'error');
      stopPolling();
    }
  }, 1000);
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

async function loadSavedUrls() {
  const domain = wfDomain.value.trim();
  if (!domain) {
    wfSavedUrls.value = '';
    return;
  }

  const response = await fetch(`/api/seed-urls?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `failed to load saved urls (${response.status})`);

  const urls = Array.isArray(payload.urls) ? payload.urls : [];
  const activeUrls = urls
    .filter((row) => row && row.active !== false && row.url)
    .map((row) => row.url);
  wfSavedUrls.value = activeUrls.join('\n');
}

async function loadWorkflowStatus() {
  const domain = wfDomain.value.trim();
  const runId = activeRunId.trim();
  if (!domain || !runId) {
    setStatus('Not started', 'warning');
    wfStatusSummary.innerHTML = '';
    renderTechnicalDetails({});
    setActionAvailability({});
    return;
  }

  const response = await fetch(`/api/workflow/status?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `failed to load workflow status (${response.status})`);

  lastPayload = payload;
  renderStatus(payload);
  renderTechnicalDetails(payload);
  setActionAvailability(payload);
}

async function postAction(path, payload) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await safeReadPayload(response);
  wfTransition.textContent = JSON.stringify(data, null, 2);
  if (!response.ok) {
    const detail = data.error || data.message || `${path} failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
}

async function initWorkflow() {
  await loadDomains();
  const query = q();
  if (query.domain) wfDomain.value = query.domain;
  activeRunId = query.runId;

  await loadSavedUrls();
  await loadExistingRuns();
  await loadWorkflowStatus();

  wfDomain.addEventListener('change', async () => {
    activeRunId = '';
    setQuery(wfDomain.value.trim(), '');
    await loadSavedUrls();
    await loadExistingRuns();
    await loadWorkflowStatus();
    stopPolling();
  });

  wfRefreshUrls.addEventListener('click', loadSavedUrls);
  wfRefreshRuns.addEventListener('click', loadExistingRuns);

  wfExistingRuns.addEventListener('change', () => {
    wfUseExistingRun.disabled = !wfExistingRuns.value;
  });

  wfUseExistingRun.addEventListener('click', async () => {
    const selectedRunId = String(wfExistingRuns.value || '').trim();
    if (!selectedRunId) {
      setStatus('Choose an existing run first.', 'warning');
      return;
    }
    activeRunId = selectedRunId;
    setQuery(wfDomain.value.trim(), activeRunId);
    await loadWorkflowStatus();
  });

  wfStartCapture.addEventListener('click', async () => {
    const domain = wfDomain.value.trim();
    if (!domain) {
      setStatus('Select a domain first.', 'warning');
      return;
    }
    setStatus('Starting capture…', 'warning');
    const result = await postAction('/api/workflow/start-capture', { domain, language: 'en', viewport_kind: 'desktop', state: 'baseline' });
    activeRunId = String(result.run_id || '').trim();
    setQuery(domain, activeRunId);
    await loadExistingRuns();
    await loadWorkflowStatus();
    startPolling();
  });

  wfGenerateDataset.addEventListener('click', async () => {
    const domain = wfDomain.value.trim();
    if (!domain || !activeRunId) {
      setStatus('Start capture first.', 'warning');
      return;
    }
    setStatus('Preparing captured data…', 'warning');
    await postAction('/api/workflow/generate-eligible-dataset', { domain, run_id: activeRunId });
    await loadWorkflowStatus();
  });

  const currentCapture = readCaptureStatus(lastPayload || {});
  if (activeRunId && !isCaptureTerminal(currentCapture)) startPolling();
}

initWorkflow().catch((err) => setStatus(err.message, 'error'));
