const domainInput = document.getElementById('domainInput');
const languagesInput = document.getElementById('languagesInput');
const viewportsInput = document.getElementById('viewportsInput');
const tiersInput = document.getElementById('tiersInput');
const includeRecipes = document.getElementById('includeRecipes');
const runIdInput = document.getElementById('runIdInput');
const planButton = document.getElementById('planButton');
const startButton = document.getElementById('startButton');
const refreshButton = document.getElementById('refreshButton');
const planBody = document.getElementById('planBody');
const runsBody = document.getElementById('runsBody');
const contextsBody = document.getElementById('contextsBody');
const captureError = document.getElementById('captureError');
const reviewStatusFilter = document.getElementById('reviewStatusFilter');

let plannedJobs = [];

function splitCsv(v) { return (v || '').split(',').map((x) => x.trim()).filter(Boolean); }
function setError(message) { captureError.textContent = message || ''; captureError.classList.toggle('hidden', !message); }

async function callApi(path, method = 'GET', payload = null) {
  const response = await fetch(path, {
    method,
    headers: payload ? { 'Content-Type': 'application/json' } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : {};
  if (!response.ok) throw new Error(data.error || `${method} ${path} failed (${response.status})`);
  return data;
}

function statusBadge(status) {
  if (!status) return 'unreviewed';
  if (status === 'blocked_by_overlay') return '⛔ blocked_by_overlay';
  if (status === 'not_found') return '🔎 not_found';
  return status;
}

async function waitForJob(jobId) {
  for (let i = 0; i < 40; i += 1) {
    const payload = await callApi(`/api/job?id=${encodeURIComponent(jobId)}`);
    if (payload.status === 'done' || payload.status === 'succeeded') return payload;
    if (payload.status === 'error' || payload.status === 'failed') throw new Error(payload.error || `Job ${jobId} failed`);
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Job ${jobId} timed out`);
}

async function planJobs() {
  try {
    setError('');
    const payload = {
      domain: domainInput.value.trim(),
      languages: splitCsv(languagesInput.value),
      viewports: splitCsv(viewportsInput.value),
      user_tiers: splitCsv(tiersInput.value),
      include_recipes: includeRecipes.checked,
    };
    const data = await callApi('/api/capture/plan', 'POST', payload);
    plannedJobs = data.jobs || [];
    planBody.innerHTML = '';
    plannedJobs.forEach((job, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${idx + 1}</td><td>${job.url || ''}</td><td>${job.recipe_id || '-'}</td><td>${job.language || ''}</td><td>${job.viewport_kind || ''}</td><td>${job.user_tier || ''}</td><td>${job.state || ''}</td><td>${job.mode || ''}</td>`;
      planBody.appendChild(tr);
    });
  } catch (err) {
    setError(err.message);
  }
}

async function startJobs() {
  try {
    setError('');
    const runId = (runIdInput.value || '').trim() || `run-${Date.now()}`;
    runIdInput.value = runId;
    for (const job of plannedJobs) {
      await callApi('/api/capture/start', 'POST', {
        domain: domainInput.value.trim(),
        run_id: runId,
        language: job.language,
        viewport_kind: job.viewport_kind,
        state: job.state,
        user_tier: job.user_tier,
      });
    }
    await loadRuns();
    await loadContexts();
  } catch (err) {
    setError(err.message);
  }
}

async function loadRuns() {
  const data = await callApi(`/api/capture/runs?domain=${encodeURIComponent(domainInput.value.trim())}`);
  runsBody.innerHTML = '';
  for (const run of data.runs || []) {
    for (const job of run.jobs || []) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${run.run_id}</td><td>${job.job_id || ''}</td><td>${job.status || ''}</td><td>${job.type || 'capture'}</td>`;
      runsBody.appendChild(tr);
    }
  }
}

async function saveReview(ctx, status) {
  if (!ctx.language) throw new Error('language required for exact-context review');
  await callApi('/api/capture/reviews', 'POST', {
    domain: domainInput.value.trim(),
    run_id: runIdInput.value.trim(),
    capture_context_id: ctx.capture_context_id,
    language: ctx.language,
    status,
    reviewer: 'operator-ui',
    timestamp: new Date().toISOString().replace('.000', ''),
  });
}

async function triggerRerun(ctx) {
  if (!ctx.language) throw new Error('language required for exact-context rerun');
  const result = await callApi('/api/capture/rerun', 'POST', {
    domain: domainInput.value.trim(),
    run_id: runIdInput.value.trim(),
    url: ctx.url,
    viewport_kind: ctx.viewport_kind,
    state: ctx.state,
    user_tier: ctx.user_tier || null,
    language: ctx.language,
    capture_context_id: ctx.capture_context_id,
  });
  await loadRuns();
  await waitForJob(result.job_id);
}

async function loadContexts() {
  const runId = (runIdInput.value || '').trim();
  if (!runId) return;
  const data = await callApi(`/api/capture/contexts?domain=${encodeURIComponent(domainInput.value.trim())}&run_id=${encodeURIComponent(runId)}`);
  contextsBody.innerHTML = '';
  const filterValue = (reviewStatusFilter?.value || '').trim();
  for (const ctx of data.contexts || []) {
    const reviewStatus = ctx.review_status?.status || '';
    if (filterValue && filterValue !== reviewStatus) continue;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${ctx.capture_context_id || ''}</td><td>${ctx.url || ''}</td><td>${ctx.language || ''}</td><td>${ctx.state || ''}</td><td>${ctx.viewport_kind || ''}</td><td>${ctx.user_tier || ''}</td><td>${ctx.elements_count || 0}</td><td><a href="${ctx.storage_uri || '#'}" target="_blank">screenshot</a></td><td>${statusBadge(reviewStatus)}</td><td><button data-kind="valid">valid</button><button data-kind="retry_requested">retry_requested</button><button data-kind="blocked_by_overlay">blocked_by_overlay</button><button data-kind="not_found">not_found</button><button data-kind="rerun">rerun</button></td>`;
    tr.querySelector('[data-kind="valid"]').addEventListener('click', async () => { await saveReview(ctx, 'valid'); await loadContexts(); });
    tr.querySelector('[data-kind="retry_requested"]').addEventListener('click', async () => { await saveReview(ctx, 'retry_requested'); await loadContexts(); });
    tr.querySelector('[data-kind="blocked_by_overlay"]').addEventListener('click', async () => { await saveReview(ctx, 'blocked_by_overlay'); await loadContexts(); });
    tr.querySelector('[data-kind="not_found"]').addEventListener('click', async () => { await saveReview(ctx, 'not_found'); await loadContexts(); });
    tr.querySelector('[data-kind="rerun"]').addEventListener('click', async () => { await triggerRerun(ctx); await loadContexts(); });
    contextsBody.appendChild(tr);
  }
}

planButton.addEventListener('click', planJobs);
startButton.addEventListener('click', startJobs);
reviewStatusFilter?.addEventListener('change', loadContexts);
refreshButton.addEventListener('click', async () => {
  try {
    setError('');
    await loadRuns();
    await loadContexts();
  } catch (err) {
    setError(err.message);
  }
});
