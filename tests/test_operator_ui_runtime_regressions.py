import json
import re
import subprocess
import textwrap
import types
import sys
from pathlib import Path


def _run_node_json(script: str) -> dict:
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout.strip())


def test_urls_runtime_uses_live_typed_domain_for_continue_and_api_mutations():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name){ if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
              contains(name){ return classes.has(name); },
            },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            querySelector(){ return makeElement('qs'); },
            querySelectorAll(){ return []; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
          };
        }

        const els = {
          domainInput: makeElement('domainInput'),
          domainSavedToggle: makeElement('domainSavedToggle'),
          domainSavedMenu: makeElement('domainSavedMenu'),
          loadButton: makeElement('loadButton'),
          replaceButton: makeElement('replaceButton'),
          addButton: makeElement('addButton'),
          clearButton: makeElement('clearButton'),
          urlsMultiline: makeElement('urlsMultiline'),
          updatedAt: makeElement('updatedAt'),
          savedUrlsBody: makeElement('savedUrlsBody'),
          errorBox: makeElement('errorBox'),
          statusBox: makeElement('statusBox'),
          continueFirstRun: makeElement('continueFirstRun'),
        };
        els.domainSavedMenu.classList.add('hidden');
        els.domainInput.value = '';

        const documentListeners = {};
        const payloads = [];

        const sandbox = {
          console,
          URLSearchParams,
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          window: { i18n: { t: (_k, fallback) => fallback } },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url, init = {}) => {
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['bongacams.com', 'typed.example'], last_used_first_run_domain: 'typed.example' }) };
            }
            if (url.startsWith('/api/recipes?')) {
              return { ok: true, json: async () => ({ recipes: [] }) };
            }
            if (url.startsWith('/api/seed-urls?')) {
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            }
            if (url === '/api/seed-urls/add') {
              payloads.push(JSON.parse(init.body || '{}'));
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          const preselectedAfterLoad = els.domainInput.value;
          els.domainInput.value = 'typed.example';
          els.domainInput.dispatch('input');
          els.urlsMultiline.value = 'https://typed.example/a';
          await els.addButton.click();
          console.log(JSON.stringify({
            preselectedAfterLoad,
            continueHref: els.continueFirstRun.href,
            addPayloadDomain: payloads[0] ? payloads[0].domain : '',
            defaultValueStillExpected: els.domainInput.value,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["preselectedAfterLoad"] == "typed.example"
    assert out["continueHref"] == "/workflow?domain=typed.example"
    assert out["addPayloadDomain"] == "typed.example"
    assert out["defaultValueStillExpected"] == "typed.example"


def test_workflow_runtime_uses_canonical_screenshot_view_url_and_safe_empty_state_and_run_label():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfContextsBody.children = [];

        const document = {
          getElementById: (id) => els[id],
          createElement: (tag) => {
            const el = makeElement(tag);
            if (tag === 'tr') {
              Object.defineProperty(el, 'innerHTML', {
                set(value) {
                  this._innerHTML = value;
                  this.lastElementChild = { appendChild(){} };
                },
                get() { return this._innerHTML || ''; },
              });
            }
            return el;
          },
        };

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document,
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) return { ok: true, json: async () => ({ runs: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        const labelDisplay = sandbox.formatRunLabel('run-123', 'First_run_18:31|24.03.2026');
        const labelFallback = sandbox.formatRunLabel('run-123', 'none');

        sandbox.renderContextsRows('example.com', 'run-123', [{
          url: 'https://example.com',
          language: 'en',
          state: 'baseline',
          viewport_kind: 'desktop',
          user_tier: 'guest',
          elements_count: 1,
          screenshot_view_url: '/api/page-screenshot?domain=example.com&run_id=run-123&page_id=p1',
          storage_uri: 'gs://should-not-be-used',
          review_status: {},
        }]);

        sandbox.renderContextsRows('example.com', 'run-123', [{
          url: 'https://example.com/empty',
          language: 'en',
          state: 'baseline',
          viewport_kind: 'desktop',
          user_tier: 'guest',
          elements_count: 1,
          screenshot_view_url: '',
          storage_uri: 'gs://still-not-used',
          review_status: {},
        }]);

        const firstHtml = els.wfContextsBody.children[0]._innerHTML || '';
        const secondHtml = els.wfContextsBody.children[1]._innerHTML || '';

        console.log(JSON.stringify({ labelDisplay, labelFallback, firstHtml, secondHtml }));
        """
    )
    out = _run_node_json(script)
    assert out["labelDisplay"] == "First_run_18:31|24.03.2026"
    assert out["labelFallback"] == "run-123"
    assert '/api/page-screenshot?domain=example.com&run_id=run-123&page_id=p1' in out["firstHtml"]
    assert 'gs://should-not-be-used' not in out["firstHtml"]
    assert 'open</a>' not in out["secondHtml"]


def test_en_standard_helper_and_pulls_success_message_runtime_flow():
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    sys.modules.setdefault(
        "jsonschema",
        types.SimpleNamespace(validate=lambda *_a, **_k: None, ValidationError=Exception, Draft7Validator=object),
    )
    from app.skeleton_server import _en_standard_display_name_today

    label = _en_standard_display_name_today()
    assert re.fullmatch(r"EN_standard_\d{2}:\d{2}\|\d{2}\.\d{2}\.\d{4}", label)

    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          return el;
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.pullsTable.querySelector = () => ({ innerHTML: '', appendChild(){}, children: [] });

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-1' }, addEventListener(){} },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener() {},
          },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url, init = {}) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            if (url === '/api/workflow/generate-eligible-dataset') return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
            if (url.startsWith('/api/workflow/status?')) {
              return {
                ok: true,
                status: 200,
                json: async () => ({
                  eligible_dataset: { status: 'ready', en_standard_display_name: 'EN_standard_18:31|24.03.2026' },
                  run: { en_standard_display_name: '' },
                }),
              };
            }
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);

        (async () => {
          await sandbox.triggerEligibleDatasetGeneration('example.com', 'run-1');
          console.log(JSON.stringify({ statusMessage: els.pullsPrepareCapturedDataStatus.textContent }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["statusMessage"] == "Captured data prepared successfully: EN_standard_18:31|24.03.2026."


def test_pulls_top_and_bottom_next_step_links_receive_same_runtime_href():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return { innerHTML: '', appendChild(){} }; },
          };
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-77' }, addEventListener(){} },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created'), addEventListener(){} },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);

        console.log(JSON.stringify({ top: els.continueCheckLanguages.href, bottom: els.continueCheckLanguagesBottom.href }));
        """
    )
    out = _run_node_json(script)
    expected = "/check-languages?domain=example.com&en_run_id=run-77"
    assert out["top"] == expected
    assert out["bottom"] == expected


def test_urls_saved_domain_menu_filters_malformed_values_and_supports_selection():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name){ if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
              contains(name){ return classes.has(name); },
            },
            setAttribute(){},
            contains(){ return false; },
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            querySelector(){ return this.children.find((child) => child.className === 'domain-saved-option') || null; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type, payload = {}){ if (listeners[type]) return listeners[type]({ target: this, ...payload }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            focus(){},
          };
        }

        const els = {
          domainInput: makeElement('domainInput'),
          domainSavedToggle: makeElement('domainSavedToggle'),
          domainSavedMenu: makeElement('domainSavedMenu'),
          loadButton: makeElement('loadButton'),
          replaceButton: makeElement('replaceButton'),
          addButton: makeElement('addButton'),
          clearButton: makeElement('clearButton'),
          urlsMultiline: makeElement('urlsMultiline'),
          updatedAt: makeElement('updatedAt'),
          savedUrlsBody: makeElement('savedUrlsBody'),
          errorBox: makeElement('errorBox'),
          statusBox: makeElement('statusBox'),
          continueFirstRun: makeElement('continueFirstRun'),
        };
        els.domainSavedMenu.classList.add('hidden');

        const documentListeners = {};
        const sandbox = {
          console,
          URLSearchParams,
          URL,
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          window: { i18n: { t: (_k, fallback) => fallback } },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url) => {
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['good.example', 'bhttps://evinaeva.github.io/polyglot-watchdog-testsite/'], last_used_first_run_domain: '' }) };
            }
            if (url.startsWith('/api/recipes?')) return { ok: true, json: async () => ({ recipes: [] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            return { ok: true, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          els.domainSavedToggle.click();
          const savedValues = els.domainSavedMenu.children.map((child) => child.textContent);
          const firstOption = els.domainSavedMenu.children.find((child) => child.className === 'domain-saved-option');
          if (firstOption) firstOption.click();
          console.log(JSON.stringify({
            savedValues,
            selectedDomain: els.domainInput.value,
            continueHref: els.continueFirstRun.href,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert "good.example" in out["savedValues"]
    assert "bhttps://evinaeva.github.io/polyglot-watchdog-testsite/" not in out["savedValues"]
    assert out["selectedDomain"] == "good.example"
    assert out["continueHref"] == "/workflow?domain=good.example"


def test_pulls_advanced_primary_labels_are_readable_and_user_tier_defaults_to_free():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return { addEventListener(){}, value: 'exclude' }; },
            focus(){},
          };
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.pullsTable.querySelector = () => ({ innerHTML: '', appendChild(){}, children: [] });

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-1' }, addEventListener(){} },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => {
              const el = makeElement(tag);
              if (tag === 'tr') {
                Object.defineProperty(el, 'innerHTML', {
                  set(value) {
                    this._innerHTML = value;
                    this.lastElementChild = { appendChild(){} };
                  },
                  get() { return this._innerHTML || ''; },
                });
              }
              return el;
            },
            addEventListener() {},
          },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        const source = fs.readFileSync('web/static/pulls.js', 'utf8');
        vm.runInContext(source, sandbox);
        console.log(JSON.stringify({
          defaultTier: sandbox.formatUserTier(''),
          summary: sandbox.captureContextSummary({ language: 'en', viewport_kind: 'desktop', state: 'baseline', user_tier: '' }),
          hasReadableAdvancedLabel: source.includes('Capture context:'),
          hasTechnicalDisclosure: source.includes('Technical IDs'),
        }));
        """
    )
    out = _run_node_json(script)
    assert out["defaultTier"] == "Free"
    assert out["summary"] == "EN · Desktop · baseline · Free"
    assert out["hasReadableAdvancedLabel"] is True
    assert out["hasTechnicalDisclosure"] is True
