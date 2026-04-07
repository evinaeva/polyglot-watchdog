const pullsStatus = document.getElementById('pullsStatus');
const pullsTable = document.getElementById('pullsTable');
const pullsBody = pullsTable.querySelector('tbody');
const pullsUrlSearch = document.getElementById('pullsUrlSearch');
const pullsElementTypeFilter = document.getElementById('pullsElementTypeFilter');
const pullsLanguageSummary = document.getElementById('pullsLanguageSummary');
const pullsWorkflowContextSummary = document.getElementById('pullsWorkflowContextSummary');
const pullsWhitelistInput = document.getElementById('pullsWhitelistInput');
const pullsWhitelistAdd = document.getElementById('pullsWhitelistAdd');
const pullsWhitelistStatus = document.getElementById('pullsWhitelistStatus');
const pullsWhitelistChips = document.getElementById('pullsWhitelistChips');
const pullsFirstRunSelect = document.getElementById('pullsFirstRunSelect');
const pullsDomainSelect = document.getElementById('pullsDomainSelect');
const pullsEnRunSelect = document.getElementById('pullsEnRunSelect');

const pullsPreviewModal = document.getElementById('pullsPreviewModal');
const pullsPreviewOverlay = document.getElementById('pullsPreviewOverlay');
const pullsPreviewClose = document.getElementById('pullsPreviewClose');
const pullsPreviewStatus = document.getElementById('pullsPreviewStatus');
const pullsPreviewImage = document.getElementById('pullsPreviewImage');
const pullsPreviewBbox = document.getElementById('pullsPreviewBbox');
const pullsPreviewDetails = document.getElementById('pullsPreviewDetails');
const pullsScreenshotViewport = document.getElementById('pullsScreenshotViewport');
const pullsScreenshotCanvas = document.getElementById('pullsScreenshotCanvas');
const pullsZoomIn = document.getElementById('pullsZoomIn');
const pullsZoomOut = document.getElementById('pullsZoomOut');
const pullsCenterElement = document.getElementById('pullsCenterElement');
const pullsImageAssetSection = document.getElementById('pullsImageAssetSection');
const pullsImageAsset = document.getElementById('pullsImageAsset');
const pullsImageAssetFallback = document.getElementById('pullsImageAssetFallback');
const pullsImageAssetMeta = document.getElementById('pullsImageAssetMeta');

let allPullRows = [];
let whitelistEntries = [];
let previewResizeObserver = null;
let currentPullsContext = { domain: '', runId: '' };
let previewState = {
  isOpen: false,
  row: null,
  triggerEl: null,
  scaleX: 1,
  scaleY: 1,
  zoom: 1,
  bboxPx: null,
};

const DECISION_TO_UI = {
  eligible: 'Keep',
  ALWAYS_COLLECT: 'Keep',
  exclude: 'Ignore',
  IGNORE_ENTIRE_ELEMENT: 'Ignore',
  'needs-fix': 'Needs Fix',
  MASK_VARIABLE: 'Needs Fix',
};

function pullsQuery() {
  const params = new URLSearchParams(window.location.search);
  return { domain: (params.get('domain') || '').trim(), runId: (params.get('run_id') || '').trim() };
}

function setCurrentPullsContext(domain, runId) {
  currentPullsContext = { domain: String(domain || '').trim(), runId: String(runId || '').trim() };
}

function getCurrentPullsContext() {
  if (currentPullsContext.domain) return { ...currentPullsContext };
  return pullsQuery();
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

async function resolveRunId(domain, explicitRunId) {
  if (explicitRunId) return explicitRunId;
  const response = await fetch(`/api/capture/runs?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `Failed to load runs (${response.status})`);
  const runs = sortRunsNewestFirst(Array.isArray(payload.runs) ? payload.runs : []);
  return String(((runs[0] || {}).run_id) || '').trim();
}

function setPullsStatus(message, cls = '') {
  pullsStatus.className = cls;
  pullsStatus.textContent = message;
}

function setPreviewStatus(message) {
  pullsPreviewStatus.textContent = message;
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function decisionToValue(decision) {
  const raw = String(decision || '').trim();
  if (raw === 'ALWAYS_COLLECT') return 'eligible';
  if (raw === 'IGNORE_ENTIRE_ELEMENT') return 'exclude';
  if (raw === 'MASK_VARIABLE') return 'needs-fix';
  if (raw === 'eligible' || raw === 'exclude' || raw === 'needs-fix') return raw;
  return '';
}

function decisionToLabel(decision) {
  return DECISION_TO_UI[String(decision || '').trim()] || '';
}

function formatViewportKind(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'desktop') return 'Desktop';
  if (normalized === 'mobile') return 'Mobile';
  if (normalized === 'any') return 'Any';
  return normalized ? normalized[0].toUpperCase() + normalized.slice(1) : '—';
}

function formatUserTier(value) {
  const normalized = String(value || '').trim();
  if (!normalized) return 'Free';
  return normalized[0].toUpperCase() + normalized.slice(1);
}

function captureContextSummary(row) {
  const language = String(row.language || '').trim() || '—';
  const state = String(row.state || '').trim() || '—';
  return `${language.toUpperCase()} · ${formatViewportKind(row.viewport_kind)} · ${state} · ${formatUserTier(row.user_tier)}`;
}

function updateWorkflowSummary(domain, runId) {
  const parts = [];
  if (domain) parts.push(`domain: ${domain}`);
  if (runId) parts.push(`run: ${runId}`);
  pullsWorkflowContextSummary.textContent = parts.length
    ? `Workflow context: ${parts.join(' · ')}.`
    : 'Workflow context: none.';
}

function updateOperatorNavigation(domain, runId) {
  const selectedEnRunId = String((pullsEnRunSelect || {}).value || '').trim() || String(runId || '').trim();
  const query = new URLSearchParams({ domain, run_id: runId }).toString();
  const checkLanguagesParams = new URLSearchParams({ domain });
  if (selectedEnRunId) checkLanguagesParams.set('en_run_id', selectedEnRunId);
  const primaryLinks = {
    pullsBackToRunHub: `/workflow?${query}`,
    continueCheckLanguages: `/check-languages?${checkLanguagesParams.toString()}`,
    continueCheckLanguagesBottom: `/check-languages?${checkLanguagesParams.toString()}`,
  };
  Object.entries(primaryLinks).forEach(([id, href]) => {
    const link = document.getElementById(id);
    if (link) link.href = href;
  });

  const technicalLinks = {
    pullsOpenContexts: `/contexts?${query}`,
    pullsOpenIssues: `/?${query}`,
  };
  Object.entries(technicalLinks).forEach(([id, href]) => {
    const link = document.getElementById(id);
    if (link) link.href = href;
  });
}

function updateLanguageSummary(rows) {
  const languages = [...new Set(rows.map((row) => String(row.language || '').trim()).filter(Boolean))].sort();
  if (!languages.length) {
    pullsLanguageSummary.textContent = 'Language: —';
  } else if (languages.length === 1) {
    pullsLanguageSummary.textContent = `Language: ${languages[0]}`;
  } else {
    pullsLanguageSummary.textContent = `Language: Mixed (${languages.join(', ')})`;
  }
  pullsLanguageSummary.classList.remove('hidden');
}

function updateElementTypeFilter(rows) {
  const selected = String(pullsElementTypeFilter.value || '');
  const options = [...new Set(rows.map((row) => String(row.element_type || '').trim()).filter(Boolean))].sort();
  pullsElementTypeFilter.innerHTML = '<option value="">All types</option>';
  for (const type of options) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    pullsElementTypeFilter.appendChild(option);
  }
  if (selected && options.includes(selected)) pullsElementTypeFilter.value = selected;
}


function normalizeElementType(value) {
  return String(value || '').trim();
}

function setWhitelistStatus(message, cls = '') {
  pullsWhitelistStatus.className = `muted ${cls}`.trim();
  pullsWhitelistStatus.textContent = message;
}

function renderWhitelist() {
  const values = [...whitelistEntries];
  pullsWhitelistChips.innerHTML = '';
  if (!values.length) {
    pullsWhitelistChips.textContent = 'No whitelisted element signatures.';
    return;
  }
  for (const entry of values) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'pulls-whitelist-chip';
    chip.textContent = `Remove ${entry.description || entry.tag || 'signature'}`;
    chip.addEventListener('click', async () => {
      const { domain, runId } = getCurrentPullsContext();
      try {
        await removeFromWhitelist(domain, entry.signature_key);
        setWhitelistStatus(`Removed ${entry.description || entry.tag || 'signature'} from whitelist.`, 'ok');
        await reloadPullRows(domain, runId);
        if (!allPullRows.length) {
          pullsTable.classList.add('hidden');
          setPullsStatus('No items found for this run.', 'empty');
          return;
        }
        renderRows(domain, runId);
      } catch (err) {
        setWhitelistStatus(err.message, 'error');
      }
    });
    pullsWhitelistChips.appendChild(chip);
  }
}

async function fetchWhitelist(domain) {
  const response = await fetch(`/api/element-type-whitelist?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || 'Failed to load whitelist');
  return payload.entries || [];
}

async function addToWhitelist(domain, row) {
  const response = await fetch('/api/element-type-whitelist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      domain,
      element_type: row.element_type || '',
      tag: row.tag || '',
      css_selector: row.css_selector || '',
      attributes: row.attributes || null,
    }),
  });
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || payload.message || 'Failed to update whitelist');
  return { entries: payload.entries || [], addedEntry: payload.added_entry || null };
}

async function removeFromWhitelist(domain, signatureKey) {
  const response = await fetch('/api/element-type-whitelist/remove', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, signature_key: signatureKey }),
  });
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || payload.message || 'Failed to update whitelist');
  return payload.entries || [];
}

async function fetchPullsPayload(domain, runId) {
  const response = await fetch(`/api/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`);
  const payload = await safeReadPayload(response);
  return { response, payload };
}

async function reloadPullRows(domain, runId) {
  const { response, payload } = await fetchPullsPayload(domain, runId);
  if (response.status === 404 && payload.status === 'not_ready') {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus(`Not ready: ${payload.error}.`, 'warning');
    allPullRows = [];
    return false;
  }
  if (!response.ok) {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus(payload.error || `Failed to load pulls (${response.status})`, 'error');
    allPullRows = [];
    return false;
  }

  allPullRows = (payload.rows || []).filter((row) => String((row || {}).element_type || '').toLowerCase() !== 'script');
  try {
    whitelistEntries = (await fetchWhitelist(domain)).filter((entry) => entry && typeof entry === 'object');
    renderWhitelist();
    setWhitelistStatus('');
  } catch (err) {
    whitelistEntries = [];
    renderWhitelist();
    setWhitelistStatus(err.message, 'error');
  }
  updateElementTypeFilter(allPullRows);
  updateLanguageSummary(allPullRows);
  return true;
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
  const response = await fetch('/api/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await safeReadPayload(response);
  if (!response.ok) throw new Error(data.message || data.error || 'Failed to save rule');
}

function filteredRows() {
  const query = String(pullsUrlSearch.value || '').trim().toLowerCase();
  const typeFilter = String(pullsElementTypeFilter.value || '').trim();
  return allPullRows.filter((row) => {
    const elementType = normalizeElementType(row.element_type);
    const decisionValue = decisionToValue(row.decision);
    if (decisionValue === 'eligible') return false;
    if (query && !String(row.url || '').toLowerCase().includes(query)) return false;
    if (typeFilter && elementType !== typeFilter) return false;
    return true;
  });
}

function parseSrcsetBestCandidate(srcsetText) {
  const candidates = String(srcsetText || '')
    .split(',')
    .map((chunk, index) => {
      const parts = chunk.trim().split(/\s+/).filter(Boolean);
      if (!parts.length) return null;
      const url = parts[0];
      const descriptor = (parts[1] || '').toLowerCase();
      let width = -1;
      let density = -1;
      if (descriptor.endsWith('w')) {
        width = Number.parseFloat(descriptor.slice(0, -1));
      } else if (descriptor.endsWith('x')) {
        density = Number.parseFloat(descriptor.slice(0, -1));
      }
      return {
        url,
        width: Number.isFinite(width) ? width : -1,
        density: Number.isFinite(density) ? density : -1,
        index,
      };
    })
    .filter(Boolean);

  if (!candidates.length) return '';

  candidates.sort((a, b) => {
    if (b.width !== a.width) return b.width - a.width;
    if (b.density !== a.density) return b.density - a.density;
    return b.index - a.index;
  });
  return candidates[0].url || '';
}

function extractImageAssetUrl(attributes) {
  if (!attributes || typeof attributes !== 'object') return '';
  const srcsetCandidate = parseSrcsetBestCandidate(attributes.srcset || attributes.srcSet || '');
  if (srcsetCandidate) return srcsetCandidate;
  const fallbackKeys = ['src', 'data-src', 'dataSrc'];
  for (const key of fallbackKeys) {
    const value = String(attributes[key] || '').trim();
    if (value) return value;
  }
  return '';
}

function resetImageAssetPreview() {
  pullsImageAssetSection.classList.add('hidden');
  pullsImageAssetMeta.innerHTML = '';
  pullsImageAssetFallback.textContent = '';
  pullsImageAsset.classList.add('hidden');
  pullsImageAsset.removeAttribute('src');
  pullsImageAsset.onload = null;
  pullsImageAsset.onerror = null;
}

function renderImageAsset(row) {
  resetImageAssetPreview();

  const elementType = String(row.element_type || '').toLowerCase();
  const tag = String(row.tag || '').toLowerCase();
  if (!(elementType === 'img' || tag === 'img')) return;

  pullsImageAssetSection.classList.remove('hidden');
  const attrs = (row.attributes && typeof row.attributes === 'object') ? row.attributes : {};
  const assetUrl = extractImageAssetUrl(attrs);
  const metadataKeys = ['src', 'alt', 'width', 'height', 'srcset', 'data-src'];

  for (const key of metadataKeys) {
    if (attrs[key] == null || String(attrs[key]).trim() === '') continue;
    const li = document.createElement('li');
    li.textContent = `${key}: ${String(attrs[key])}`;
    pullsImageAssetMeta.appendChild(li);
  }

  if (!assetUrl) {
    pullsImageAssetFallback.textContent = 'Image asset URL not available; use page screenshot highlight only.';
    return;
  }

  pullsImageAsset.onload = () => {
    pullsImageAsset.classList.remove('hidden');
    pullsImageAssetFallback.textContent = '';
  };
  pullsImageAsset.onerror = () => {
    pullsImageAsset.classList.add('hidden');
    pullsImageAsset.removeAttribute('src');
    pullsImageAssetFallback.textContent = 'Unable to load image asset; use on-page highlight.';
  };
  pullsImageAsset.src = assetUrl;
}

function applyZoom() {
  pullsScreenshotCanvas.style.transform = `scale(${previewState.zoom})`;
  pullsScreenshotCanvas.style.transformOrigin = 'top left';
}

function isModalOpen() {
  return previewState.isOpen && !pullsPreviewModal.classList.contains('hidden');
}

function validBbox(bbox) {
  if (!bbox || typeof bbox !== 'object') return false;
  const x = Number(bbox.x);
  const y = Number(bbox.y);
  const width = Number(bbox.width);
  const height = Number(bbox.height);
  return Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0;
}

function centerToBbox() {
  if (!previewState.bboxPx || !isModalOpen()) return;
  const { left, top, width, height } = previewState.bboxPx;
  const targetX = (left + (width / 2)) * previewState.zoom;
  const targetY = (top + (height / 2)) * previewState.zoom;
  pullsScreenshotViewport.scrollTo({
    left: Math.max(targetX - (pullsScreenshotViewport.clientWidth / 2), 0),
    top: Math.max(targetY - (pullsScreenshotViewport.clientHeight / 2), 0),
    behavior: 'smooth',
  });
}

function hideBbox() {
  previewState.bboxPx = null;
  pullsPreviewBbox.classList.add('hidden');
  pullsPreviewBbox.style.left = '0px';
  pullsPreviewBbox.style.top = '0px';
  pullsPreviewBbox.style.width = '0px';
  pullsPreviewBbox.style.height = '0px';
}

function updateOverlay() {
  if (!isModalOpen()) return;
  const row = previewState.row;
  if (!row) return;

  if (!validBbox(row.bbox)) {
    hideBbox();
    setPreviewStatus('Invalid or missing bbox for this item; screenshot shown without highlight.');
    return;
  }

  const renderedWidth = pullsPreviewImage.clientWidth;
  const renderedHeight = pullsPreviewImage.clientHeight;
  const sourceWidth = Number(pullsPreviewImage.naturalWidth || 0);
  const sourceHeight = Number(pullsPreviewImage.naturalHeight || 0);

  if (!sourceWidth || !sourceHeight) {
    const viewport = row.page_viewport || {};
    const fallbackWidth = Number(viewport.width || 0);
    const fallbackHeight = Number(viewport.height || 0);
    if (!fallbackWidth || !fallbackHeight) {
      hideBbox();
      setPreviewStatus('Missing screenshot dimensions; cannot scale bbox overlay.');
      return;
    }
    previewState.scaleX = renderedWidth / fallbackWidth;
    previewState.scaleY = renderedHeight / fallbackHeight;
  } else {
    previewState.scaleX = renderedWidth / sourceWidth;
    previewState.scaleY = renderedHeight / sourceHeight;
  }
  if (!renderedWidth || !renderedHeight) {
    hideBbox();
    setPreviewStatus('Screenshot is still rendering; bbox overlay will appear shortly.');
    return;
  }

  const left = Number(row.bbox.x) * previewState.scaleX;
  const top = Number(row.bbox.y) * previewState.scaleY;
  const width = Number(row.bbox.width) * previewState.scaleX;
  const height = Number(row.bbox.height) * previewState.scaleY;
  previewState.bboxPx = { left, top, width, height };

  pullsPreviewBbox.classList.remove('hidden');
  pullsPreviewBbox.style.left = `${left}px`;
  pullsPreviewBbox.style.top = `${top}px`;
  pullsPreviewBbox.style.width = `${width}px`;
  pullsPreviewBbox.style.height = `${height}px`;
}

function detailsText(row) {
  return JSON.stringify({
    item_id: row.item_id,
    page_id: row.page_id,
    url: row.url,
    language: row.language,
    state: row.state,
    viewport_kind: row.viewport_kind,
    element_type: row.element_type,
    css_selector: row.css_selector,
    text: row.text,
    bbox: row.bbox,
    screenshot_storage_uri: row.screenshot_storage_uri,
    attributes: row.attributes || null,
  }, null, 2);
}

function startPreviewObservers() {
  if (previewResizeObserver || typeof ResizeObserver === 'undefined') return;
  previewResizeObserver = new ResizeObserver(() => {
    if (!isModalOpen()) return;
    updateOverlay();
  });
  previewResizeObserver.observe(pullsPreviewImage);
  previewResizeObserver.observe(pullsScreenshotViewport);
}

function stopPreviewObservers() {
  if (!previewResizeObserver) return;
  previewResizeObserver.disconnect();
  previewResizeObserver = null;
}

function resetPreviewState() {
  previewState.row = null;
  previewState.isOpen = false;
  previewState.scaleX = 1;
  previewState.scaleY = 1;
  previewState.zoom = 1;
  previewState.bboxPx = null;
  applyZoom();
  setPreviewStatus('');
  pullsPreviewImage.onload = null;
  pullsPreviewImage.onerror = null;
  pullsPreviewImage.removeAttribute('src');
  pullsPreviewDetails.textContent = '';
  hideBbox();
  resetImageAssetPreview();
  pullsScreenshotViewport.scrollTo({ top: 0, left: 0 });
}

function closePreview() {
  if (!isModalOpen()) return;
  pullsPreviewModal.classList.add('hidden');
  stopPreviewObservers();
  const triggerToFocus = previewState.triggerEl;
  previewState.triggerEl = null;
  resetPreviewState();
  if (triggerToFocus && typeof triggerToFocus.focus === 'function') {
    triggerToFocus.focus();
  }
}

function afterImagePainted() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

async function openPreview(row, triggerEl) {
  previewState.row = row;
  previewState.triggerEl = triggerEl || null;
  previewState.isOpen = true;
  previewState.zoom = 1;
  previewState.bboxPx = null;
  applyZoom();

  pullsPreviewModal.classList.remove('hidden');
  pullsPreviewClose.focus();
  pullsPreviewDetails.textContent = detailsText(row);
  hideBbox();
  startPreviewObservers();

  renderImageAsset(row);

  if (!row.screenshot_view_url) {
    setPreviewStatus('No page screenshot is available for this item.');
    return;
  }

  setPreviewStatus('Loading page screenshot…');
  pullsPreviewImage.src = row.screenshot_view_url;

  await new Promise((resolve) => {
    pullsPreviewImage.onload = () => resolve();
    pullsPreviewImage.onerror = () => resolve();
  });

  if (!isModalOpen()) return;

  if (!pullsPreviewImage.naturalWidth || !pullsPreviewImage.naturalHeight) {
    setPreviewStatus('Unable to load page screenshot preview.');
    hideBbox();
    return;
  }

  await afterImagePainted();
  if (!isModalOpen()) return;

  setPreviewStatus('Showing canonical page screenshot with bbox overlay.');
  updateOverlay();
  centerToBbox();
}

function renderRows(domain, runId) {
  const rows = filteredRows();
  const totalCount = allPullRows.length;
  pullsBody.innerHTML = '';

  if (!rows.length) {
    pullsTable.classList.add('hidden');
    setPullsStatus('No items match current filters.', 'empty');
    return;
  }

  for (const row of rows) {
    const tr = document.createElement('tr');
    const selected = decisionToValue(row.decision) || 'eligible';
    tr.innerHTML = `
      <td>${escapeHtml(row.url)}</td>
      <td>${escapeHtml(row.element_type)}</td>
      <td>${escapeHtml(row.text || '')}</td>
      <td>${escapeHtml(decisionToLabel(row.decision))}</td>
      <td></td>`;

    const controls = document.createElement('div');
    controls.innerHTML = `
      <label>
        <span class="hidden">Decision</span>
        <select>
          <option value="">Choose</option>
          <option value="eligible" ${selected === 'eligible' ? 'selected' : ''}>Keep</option>
          <option value="exclude" ${selected === 'exclude' ? 'selected' : ''}>Ignore</option>
          <option value="needs-fix" ${selected === 'needs-fix' ? 'selected' : ''}>Needs Fix</option>
        </select>
      </label>
      <button type="button">Save selection</button>
      <button type="button" class="pulls-whitelist-trigger">Add to whitelist</button>
      <button type="button" class="pulls-preview-trigger">Preview on page</button>
      <details>
        <summary>Advanced</summary>
        <div>Capture context: ${escapeHtml(captureContextSummary(row))}</div>
        <div>Page: ${escapeHtml(row.url || '—')}</div>
        <div>Viewport: ${escapeHtml(formatViewportKind(row.viewport_kind))}</div>
        <div>User tier: ${escapeHtml(formatUserTier(row.user_tier))}</div>
        <details class="pulls-technical-ids">
          <summary>Technical IDs</summary>
          <div>capture_context_id: ${escapeHtml(row.capture_context_id || '—')}</div>
          <div>page_id: ${escapeHtml(row.page_id || '—')}</div>
        </details>
      </details>`;

    const select = controls.querySelector('select');
    const button = controls.querySelector('button');
    const whitelistButton = controls.querySelector('.pulls-whitelist-trigger');
    const previewButton = controls.querySelector('.pulls-preview-trigger');
    button.addEventListener('click', async () => {
      if (!select.value) {
        setPullsStatus('Please choose a decision before saving.', 'warning');
        return;
      }
      try {
        await saveRule(domain, runId, row, select.value);
        row.decision = select.value;
        setPullsStatus('Selection saved.', 'ok');
        renderRows(domain, runId);
      } catch (err) {
        setPullsStatus(err.message, 'error');
      }
    });
    whitelistButton.addEventListener('click', async () => {
      try {
        await saveRule(domain, runId, row, 'eligible');
        const { addedEntry } = await addToWhitelist(domain, row);
        const created = addedEntry || {};
        setWhitelistStatus(`Added ${created.description || row.css_selector || row.element_type} to whitelist.`, 'ok');
        await reloadPullRows(domain, runId);
        if (!allPullRows.length) {
          pullsTable.classList.add('hidden');
          setPullsStatus('No items found for this run.', 'empty');
          return;
        }
        renderRows(domain, runId);
      } catch (err) {
        setWhitelistStatus(err.message, 'error');
      }
    });
    previewButton.addEventListener('click', () => openPreview(row, previewButton));
    tr.lastElementChild.appendChild(controls);
    pullsBody.appendChild(tr);
  }

  pullsTable.classList.remove('hidden');
  setPullsStatus(`Showing ${rows.length} of ${totalCount} items.`, 'ok');
}

async function loadPulls() {
  const { domain, runId: queryRunId } = pullsQuery();
  let runId = queryRunId;
  if (!domain) {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus('Missing required query params: domain and run_id.', 'error');
    return;
  }

  runId = await resolveRunId(domain, queryRunId);
  setCurrentPullsContext(domain, runId);
  if (runId && runId !== queryRunId) {
    const params = new URLSearchParams(window.location.search);
    params.set('domain', domain);
    params.set('run_id', runId);
    window.history.replaceState({}, '', `/pulls?${params.toString()}`);
  }
  if (pullsDomainSelect) pullsDomainSelect.value = domain;
  if (pullsFirstRunSelect && runId) pullsFirstRunSelect.value = runId;

  updateWorkflowSummary(domain, runId);
  updateOperatorNavigation(domain, runId);

  if (!runId) {
    pullsTable.classList.add('hidden');
    pullsLanguageSummary.classList.add('hidden');
    setPullsStatus('Missing required query params: domain and run_id.', 'error');
    return;
  }

  setPullsStatus('Loading items…');
  const loaded = await reloadPullRows(domain, runId);
  if (!loaded) return;

  if (!allPullRows.length) {
    pullsTable.classList.add('hidden');
    setPullsStatus('No items found for this run.', 'empty');
    return;
  }
  renderRows(domain, runId);
}

pullsUrlSearch.addEventListener('input', () => {
  const { domain, runId } = getCurrentPullsContext();
  renderRows(domain, runId);
});

pullsElementTypeFilter.addEventListener('change', () => {
  const { domain, runId } = getCurrentPullsContext();
  renderRows(domain, runId);
});

if (pullsDomainSelect) {
  pullsDomainSelect.addEventListener('change', () => {
    const domain = String(pullsDomainSelect.value || '').trim();
    const params = new URLSearchParams(window.location.search);
    if (domain) params.set('domain', domain);
    params.delete('run_id');
    params.delete('en_run_id');
    window.location.assign(`/pulls?${params.toString()}`);
  });
}

if (pullsFirstRunSelect) {
  pullsFirstRunSelect.addEventListener('change', () => {
    const { domain } = pullsQuery();
    const runId = String(pullsFirstRunSelect.value || '').trim();
    const params = new URLSearchParams(window.location.search);
    if (domain) params.set('domain', domain);
    if (runId) params.set('run_id', runId);
    window.location.assign(`/pulls?${params.toString()}`);
  });
}

if (pullsEnRunSelect) {
  pullsEnRunSelect.addEventListener('change', () => {
    const { domain, runId } = getCurrentPullsContext();
    updateOperatorNavigation(domain, runId);
  });
}


pullsWhitelistAdd.addEventListener('click', async () => {
  setWhitelistStatus('Manual add by type is disabled. Use "Add to whitelist" on a concrete row.', 'warning');
});

pullsPreviewClose.addEventListener('click', closePreview);
pullsPreviewOverlay.addEventListener('click', closePreview);
pullsZoomIn.addEventListener('click', () => {
  if (!isModalOpen()) return;
  previewState.zoom = Math.min(previewState.zoom + 0.2, 3);
  applyZoom();
  centerToBbox();
});
pullsZoomOut.addEventListener('click', () => {
  if (!isModalOpen()) return;
  previewState.zoom = Math.max(previewState.zoom - 0.2, 0.5);
  applyZoom();
  centerToBbox();
});
pullsCenterElement.addEventListener('click', centerToBbox);
window.addEventListener('resize', () => {
  if (isModalOpen()) updateOverlay();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && isModalOpen()) {
    event.preventDefault();
    closePreview();
  }
});

loadPulls();
