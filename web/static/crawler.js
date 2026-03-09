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

async function saveReview(ctx, status, comment) {
  if (!ctx.language) throw new Error("language required for exact-context review");
  await callApi('/api/capture/review', 'POST', {
    domain: domainInput.value.trim(),
    capture_context_id: ctx.capture_context_id,
    language: ctx.language,
    status,
    reviewer: 'operator-ui',
    timestamp: new Date().toISOString().replace('.000', ''),
    comment,
  });
}

async function triggerRerun(ctx) {
  if (!ctx.language) throw new Error("language required for exact-context rerun");
  await callApi('/api/capture/rerun', 'POST', {
    domain: domainInput.value.trim(),
    run_id: runIdInput.value.trim(),
    url: ctx.url,
    viewport_kind: ctx.viewport_kind,
    state: ctx.state,
    user_tier: ctx.user_tier || null,
    language: ctx.language,
    capture_context_id: ctx.capture_context_id,
  });
}

async function loadContexts() {
  const runId = (runIdInput.value || '').trim();
  if (!runId) return;
  const data = await callApi(`/api/capture/contexts?domain=${encodeURIComponent(domainInput.value.trim())}&run_id=${encodeURIComponent(runId)}`);
  contextsBody.innerHTML = '';
  for (const ctx of data.contexts || []) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${ctx.capture_context_id || ''}</td><td>${ctx.url || ''}</td><td>${ctx.language || ''}</td><td>${ctx.state || ''}</td><td>${ctx.viewport_kind || ''}</td><td>${ctx.user_tier || ''}</td><td>${ctx.elements_count || 0}</td><td>${ctx.storage_uri || ''}</td><td><input data-kind="comment" placeholder="review comment" /></td><td><button data-kind="approve">approve</button><button data-kind="reject">reject</button><button data-kind="rerun">rerun</button></td>`;
    tr.querySelector('[data-kind="approve"]').addEventListener('click', async () => {
      await saveReview(ctx, 'approved', tr.querySelector('[data-kind="comment"]').value);
    });
    tr.querySelector('[data-kind="reject"]').addEventListener('click', async () => {
      await saveReview(ctx, 'rejected', tr.querySelector('[data-kind="comment"]').value);
    });
    tr.querySelector('[data-kind="rerun"]').addEventListener('click', async () => {
      await triggerRerun(ctx);
      await loadRuns();
    });
    contextsBody.appendChild(tr);
  }
}

planButton.addEventListener('click', planJobs);
startButton.addEventListener('click', startJobs);
refreshButton.addEventListener('click', async () => {
  try {
    setError('');
    await loadRuns();
    await loadContexts();
  } catch (err) {
    setError(err.message);
  }
});
