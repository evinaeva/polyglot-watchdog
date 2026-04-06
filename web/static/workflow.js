const wfDomain = document.getElementById('wfDomain');
const wfRefreshUrls = document.getElementById('wfRefreshUrls');
const wfSavedUrls = document.getElementById('wfSavedUrls');
const wfStartCapture = document.getElementById('wfStartCapture');
const wfContinuePulls = document.getElementById('wfContinuePulls');
const wfStatus = document.getElementById('wfStatus');
const wfStatusSummary = document.getElementById('wfStatusSummary');
const wfExistingRuns = document.getElementById('wfExistingRuns');
const wfUseExistingRun = document.getElementById('wfUseExistingRun');
const wfRunsStatus = document.getElementById('wfRunsStatus');
const wfContextsStatus = document.getElementById('wfContextsStatus');
const wfContextsTable = document.getElementById('wfContextsTable');
const wfContextsBody = document.getElementById('wfContextsBody');

let lastPayload = null;
let activeRunId = '';
let pollTimer = null;
let availableRuns = [];
const tallinnDateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Tallinn',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

function formatUtcTimestampForUi(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  const parts = tallinnDateTimeFormatter.formatToParts(parsed);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
}

function normalizeDisplayName(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return '';
  const lowered = raw.toLowerCase();
  return (lowered === 'none' || lowered === 'null') ? '' : raw;
}

function formatRunLabel(runId, displayName) {
  const safeRunId = String(runId || '').trim();
  const safeDisplayName = normalizeDisplayName(displayName);
  if (safeDisplayName) return safeDisplayName;
  return safeRunId || '—';
}

function runDisplayName(run) {
  if (!run || typeof run !== 'object') return '';
  const direct = normalizeDisplayName(run.display_name);
  if (direct) return direct;
  const metadata = run.metadata && typeof run.metadata === 'object' ? run.metadata : {};
  return normalizeDisplayName(metadata.display_name);
}

function metadataFirstRunMarker(run) {
  const metadata = run && typeof run.metadata === 'object' ? run.metadata : {};
  const candidates = [metadata.kind, metadata.flow, metadata.stage];
  return candidates.some((value) => {
    const marker = String(value || '').trim().toLowerCase();
    return marker === 'first_run' || marker === 'first-run' || marker === 'firstrun';
  });
}

function isFirstRunDisplayName(displayName) {
  return /^first[_\s-]?run_/i.test(String(displayName || '').trim());
}

function isFirstRunCaptureJob(job) {
  const type = String((job || {}).type || '').trim().toLowerCase();
  const phase = String((job || {}).phase || '').trim();
  const jobId = String((job || {}).job_id || '').trim().toLowerCase();
  const isCaptureLike = type === 'capture' || phase === '1' || jobId.startsWith('phase1-');
  if (!isCaptureLike) return false;
  const context = job && typeof job.context === 'object' ? job.context : {};
  const language = String(context.language || '').trim().toLowerCase();
  const state = String(context.state || '').trim().toLowerCase();
  return language === 'en' && state === 'baseline';
}

function isFirstRunEntry(run) {
  if (metadataFirstRunMarker(run)) return true;
  const jobs = Array.isArray((run || {}).jobs) ? run.jobs : [];
  if (jobs.some(isFirstRunCaptureJob)) return true;
  const displayName = runDisplayName(run);
  // Fallback for legacy/manual runs where machine markers are absent in `/api/capture/runs`.
  return isFirstRunDisplayName(displayName);
}

function formatFirstRunOptionLabel(run) {
  const raw = String((run || {}).created_at || '').trim();
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return 'First run';
  const parts = tallinnDateTimeFormatter.formatToParts(parsed);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `First run ${map.hour}:${map.minute}, ${map.day}.${map.month}.${map.year}`;
}

function resolveDefaultSelectedRunId(runs, requestedRunId) {
  const requested = String(requestedRunId || '').trim();
  if (requested && runs.some((run) => String((run || {}).run_id || '').trim() === requested)) return requested;
  return String(((runs[0] || {}).run_id) || '').trim();
}

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
  const runId = activeRunId || run.run_id || '';
  const runLabel = formatRunLabel(runId, run.display_name);
  const status = readCaptureStatus(payload);
  const human = humanCaptureStatus(status);
  const cls = status === 'failed' ? 'error' : status === 'in_progress' ? 'warning' : status === 'ready' || status === 'empty' ? 'ok' : '';
  setStatus(`Capture status: ${human}`, cls);

  const rows = [
    ['Domain', wfDomain.value || run.domain || '—'],
    ['Capture run', runLabel],
    ['Contexts processed', capture.contexts ?? '—'],
    ['Items processed', capture.items ?? '—'],
    ['Worker jobs running', run.jobs_running ?? '—'],
    ['Worker jobs failed', run.jobs_failed ?? '—'],
  ];

  const updatedAt = capture.updated_at || run.updated_at || payload.updated_at || capture.last_update || run.last_update || payload.last_update || capture.last_updated_at || run.last_updated_at || payload.last_updated_at || capture.timestamp || run.timestamp || payload.timestamp;
  if (updatedAt) rows.push(['Last update', formatUtcTimestampForUi(updatedAt)]);

  wfStatusSummary.innerHTML = rows.map(([label, value]) => `<dt>${label}</dt><dd>${value}</dd>`).join('');
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

  setContinueLink(wfDomain.value.trim(), activeRunId, captureReady);
}

function setRunsStatus(message) {
  wfRunsStatus.textContent = message || '';
}

function setContextsStatus(message, cls = '') {
  wfContextsStatus.className = cls;
  wfContextsStatus.textContent = message || '';
}

function renderContextsRows(domain, runId, contexts) {
  wfContextsBody.innerHTML = '';
  for (const row of contexts) {
    const tr = document.createElement('tr');
    const screenshotHref = String(row.screenshot_view_url || '').trim();
    const screenshot = screenshotHref ? `<a href="${screenshotHref}" target="_blank" rel="noopener">open</a>` : '';
    const reviewStatus = (row.review_status || {}).status || '';
    tr.innerHTML = `<td>${row.url || ''}</td><td>${row.language || ''}</td><td>${row.state || ''}</td><td>${row.viewport_kind || ''}</td><td>${row.user_tier || ''}</td><td>${row.elements_count || 0}</td><td>${screenshot}</td><td></td>`;

    const controls = document.createElement('div');
    controls.innerHTML = '<select><option value="valid">valid</option><option value="blocked_by_overlay">blocked_by_overlay</option><option value="not_found">not_found</option></select> <button type="button">Save</button> <span></span>';
    const select = controls.querySelector('select');
    const button = controls.querySelector('button');
    const current = controls.querySelector('span');
    current.textContent = reviewStatus;
    if (reviewStatus) select.value = reviewStatus;

    button.addEventListener('click', async () => {
      try {
        await postCaptureReview(domain, runId, row, select.value);
        setContextsStatus(`Saved review for ${row.capture_context_id}`, 'ok');
        await loadContexts();
      } catch (error) {
        setContextsStatus(error.message || 'Failed to save review', 'error');
      }
    });

    tr.lastElementChild.appendChild(controls);
    wfContextsBody.appendChild(tr);
  }
}

async function loadContexts() {
  const domain = wfDomain.value.trim();
  const runId = activeRunId.trim();

  if (!domain || !runId) {
    wfContextsBody.innerHTML = '';
    wfContextsTable.classList.add('hidden');
    setContextsStatus('Select or start a run to review contexts.', 'warning');
    return;
  }

  const response = await fetch(`/api/capture/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    wfContextsBody.innerHTML = '';
    wfContextsTable.classList.add('hidden');
    setContextsStatus('Not ready: page_screenshots artifact is missing. Run capture or wait for pipeline artifacts.', 'warning');
    return;
  }
  if (!response.ok) {
    wfContextsBody.innerHTML = '';
    wfContextsTable.classList.add('hidden');
    setContextsStatus(payload.error || `Failed to load contexts (${response.status})`, 'error');
    return;
  }

  const contexts = Array.isArray(payload.contexts) ? payload.contexts : [];
  if (!contexts.length) {
    wfContextsBody.innerHTML = '';
    wfContextsTable.classList.add('hidden');
    setContextsStatus('No contexts found for this run.', 'empty');
    return;
  }

  renderContextsRows(domain, runId, contexts);
  wfContextsTable.classList.remove('hidden');
  setContextsStatus(`Loaded ${contexts.length} contexts.`, 'ok');
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
    if (selected) {
      setRunsStatus('No first-run entries found. Keeping current run context.');
      return;
    }
    setRunsStatus('No existing runs found for this domain yet.');
    return;
  }

  for (const run of availableRuns) {
    const runId = String((run || {}).run_id || '').trim();
    if (!runId) continue;
    const option = document.createElement('option');
    option.value = runId;
    option.textContent = formatFirstRunOptionLabel(run);
    wfExistingRuns.appendChild(option);
  }

  if (!wfExistingRuns.options.length) {
    wfExistingRuns.innerHTML = '<option value="">No runs found</option>';
    wfUseExistingRun.disabled = true;
    setRunsStatus('No existing runs found for this domain yet.');
    return;
  }

  const hasSelected = selected && availableRuns.some((run) => String((run || {}).run_id || '').trim() === selected);
  if (hasSelected) {
    wfExistingRuns.value = selected;
  } else if (selected) {
    wfExistingRuns.value = '';
    wfUseExistingRun.disabled = true;
    setRunsStatus('Current run is not in the First run list. Keeping current run context.');
    return;
  } else {
    const nextSelectedRunId = resolveDefaultSelectedRunId(availableRuns, selected);
    if (nextSelectedRunId) {
      wfExistingRuns.value = nextSelectedRunId;
      if (activeRunId !== nextSelectedRunId) {
        activeRunId = nextSelectedRunId;
        setQuery(wfDomain.value.trim(), activeRunId);
      }
    } else {
      activeRunId = '';
      setQuery(wfDomain.value.trim(), activeRunId);
    }
  }

  wfUseExistingRun.disabled = !wfExistingRuns.value;
  setRunsStatus('');
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
  availableRuns = sortRunsNewestFirst(runs).filter(isFirstRunEntry);
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
    if (wfSavedUrls) wfSavedUrls.value = '';
    return;
  }

  const response = await fetch(`/api/seed-urls?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `failed to load saved urls (${response.status})`);

  const urls = Array.isArray(payload.urls) ? payload.urls : [];
  const activeUrls = urls
    .filter((row) => row && row.active !== false && row.url)
    .map((row) => row.url);
  if (wfSavedUrls) wfSavedUrls.value = activeUrls.join('\n');
}

async function loadWorkflowStatus() {
  const domain = wfDomain.value.trim();
  const runId = activeRunId.trim();
  if (!domain || !runId) {
    setStatus('Not started', 'warning');
    wfStatusSummary.innerHTML = '';
    setActionAvailability({});
    await loadContexts();
    return;
  }

  const response = await fetch(`/api/workflow/status?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `failed to load workflow status (${response.status})`);

  lastPayload = payload;
  renderStatus(payload);
  setActionAvailability(payload);
  await loadContexts();
}

async function postAction(path, payload) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await safeReadPayload(response);
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


  const currentCapture = readCaptureStatus(lastPayload || {});
  if (activeRunId && !isCaptureTerminal(currentCapture)) startPolling();
}

initWorkflow().catch((err) => setStatus(err.message, 'error'));
