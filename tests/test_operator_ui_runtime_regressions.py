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


def test_urls_drawer_keeps_url_domain_for_row_mutations_when_recipe_domain_changes():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            checked: true,
            disabled: false,
            files: [{ name: 'r.json' }],
            children: [],
            options: [],
            selectedOptions: [],
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
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this, key: '' }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            querySelectorAll(){ return []; },
          };
          return el;
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
          recipeDrawer: makeElement('recipeDrawer'),
          closeRecipeDrawer: makeElement('closeRecipeDrawer'),
          recipeDrawerUrl: makeElement('recipeDrawerUrl'),
          recipeDomainSelect: makeElement('recipeDomainSelect'),
          recipeAttachToggle: makeElement('recipeAttachToggle'),
          recipeFileInput: makeElement('recipeFileInput'),
          uploadRecipeButton: makeElement('uploadRecipeButton'),
          attachedRecipesList: makeElement('attachedRecipesList'),
          allRecipesList: makeElement('allRecipesList'),
        };
        els.domainInput.value = 'domain-a.com';
        els.recipeDomainSelect.value = 'domain-a.com';
        els.domainSavedMenu.classList.add('hidden');

        const documentListeners = {};
        const calls = [];
        const seedRows = {
          'domain-a.com': { urls: [{ url: 'https://domain-a.com/u', recipe_ids: ['a-r1'], active: true }], updated_at: '2026-03-01T00:00:00Z' },
          'domain-b.com': { urls: [{ url: 'https://domain-b.com/u', recipe_ids: ['b-r1'], active: true }], updated_at: '2026-03-01T00:00:00Z' },
        };

        const sandbox = {
          console,
          URLSearchParams,
          FormData: class { constructor(){ this.map = new Map(); } append(k,v){ this.map.set(k,v); } },
          window: { i18n: { t: (_k, fb) => fb }, confirm: () => true },
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url, init = {}) => {
            calls.push({ url, init });
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['domain-a.com', 'domain-b.com'] }) };
            }
            if (url.startsWith('/api/recipes?')) return { ok: true, json: async () => ({ recipes: [{ recipe_id: 'b-r1' }] }) };
            if (url.startsWith('/api/seed-urls?')) {
              const domain = decodeURIComponent(url.split('domain=')[1] || '');
              return { ok: true, json: async () => seedRows[domain] || { urls: [], updated_at: '' } };
            }
            if (url === '/api/seed-urls/row-upsert') {
              const payload = JSON.parse(init.body || '{}');
              return { ok: true, json: async () => ({ urls: [{ url: payload.row.url, recipe_ids: payload.row.recipe_ids, active: true }], updated_at: '2026-03-02T00:00:00Z' }) };
            }
            if (url === '/api/recipes/upload') {
              return { ok: true, json: async () => ({ status: 'ok', recipe_id: 'b-r1', overwrote: false }) };
            }
            if (url === '/api/recipes/delete') return { ok: true, json: async () => ({ status: 'ok' }) };
            if (url === '/api/seed-urls/add' || url === '/api/seed-urls/clear' || url === '/api/seed-urls/delete' || url === '/api/seed-urls') {
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-01T00:00:00Z' }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          await sandbox.load();
          sandbox.openRecipeDrawer('https://domain-a.com/u');
          els.recipeDomainSelect.value = 'domain-b.com';
          await sandbox.loadRecipeManagementData();
          await sandbox.upsertRowRecipes('https://domain-a.com/u', ['a-r1', 'b-r1']);
          const recipeCalls = calls.filter((row) => row.url.startsWith('/api/recipes?domain='));
          console.log(JSON.stringify({
            rowUpsertDomain: JSON.parse(calls.find((row) => row.url === '/api/seed-urls/row-upsert').init.body).domain,
            recipeFetchDomain: recipeCalls.length ? recipeCalls[recipeCalls.length - 1].url : '',
            seedFetchUsedRecipeDomain: calls.some((row) => row.url === '/api/seed-urls?domain=domain-b.com'),
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["rowUpsertDomain"] == "domain-a.com"
    assert out["recipeFetchDomain"].endswith("domain-b.com")
    assert out["seedFetchUsedRecipeDomain"] is False


def test_workflow_runtime_formats_utc_timestamps_in_tallinn_with_dst():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(){},
            addEventListener(){},
            querySelector(){ return makeElement('qs'); },
          };
        }

        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          fetch: async () => ({ ok: true, json: async () => ({ runs: [], items: [], contexts: [], capture: { status: 'not_started' }, run: {} }) }),
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        console.log(JSON.stringify({
          winter: sandbox.formatUtcTimestampForUi('2026-01-15T10:00:00Z'),
          summer: sandbox.formatUtcTimestampForUi('2026-07-15T10:00:00Z'),
        }));
        """
    )
    out = _run_node_json(script)
    assert out["winter"] == "2026-01-15 12:00"
    assert out["summer"] == "2026-07-15 13:00"


def test_workflow_runtime_sorting_uses_raw_utc_timestamp_not_display_value():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          return {
            id, value: '', href: '', innerHTML: '', textContent: '', className: '', dataset: {}, disabled: false,
            classList: { add(){}, remove(){}, toggle(){} }, setAttribute(){}, appendChild(){}, addEventListener(){},
            querySelector(){ return makeElement('qs'); },
          };
        }
        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          fetch: async () => ({ ok: true, json: async () => ({ runs: [], items: [], contexts: [], capture: { status: 'not_started' }, run: {} }) }),
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);
        const out = sandbox.sortRunsNewestFirst([
          { run_id: 'older', created_at: '2026-01-15T10:00:00Z' },
          { run_id: 'newer', created_at: '2026-01-15T11:00:00Z' },
        ]);
        console.log(JSON.stringify({ first: out[0].run_id, second: out[1].run_id }));
        """
    )
    out = _run_node_json(script)
    assert out["first"] == "newer"
    assert out["second"] == "older"


def test_workflow_existing_runs_default_selection_prefers_newest_and_handles_empty_states():
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
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          if (id === 'wfExistingRuns') {
            Object.defineProperty(el, 'innerHTML', {
              set(value) {
                this._innerHTML = value;
                this.children = [];
                this.options = [];
                this.value = '';
                if (String(value).includes('No runs found')) {
                  this.options.push({ value: '' });
                }
              },
              get() { return this._innerHTML || ''; },
            });
          }
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';

        const runsPayloads = [
          { runs: [
            { run_id: 'run-older', created_at: '2026-03-10T10:00:00Z' },
            { run_id: 'run-newest', created_at: '2026-03-12T10:00:00Z' },
            { run_id: 'run-middle', created_at: '2026-03-11T10:00:00Z' },
          ] },
          { runs: [{ run_id: 'run-only', created_at: '2026-03-20T10:00:00Z' }] },
          { runs: [] },
          { runs: [
            { run_id: 'run-a', created_at: '2026-03-01T10:00:00Z' },
            { run_id: 'run-z-newest', created_at: '2026-03-30T10:00:00Z' },
            { run_id: 'run-m', created_at: '2026-03-15T10:00:00Z' },
          ] },
        ];
        let runsCallIndex = 0;

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => makeElement(tag),
          },
          fetch: async (url) => {
            if (url.startsWith('/api/capture/runs?')) {
              const payload = runsPayloads[Math.min(runsCallIndex, runsPayloads.length - 1)];
              runsCallIndex += 1;
              return { ok: true, json: async () => payload };
            }
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);

        (async () => {
          await sandbox.loadExistingRuns();
          const multiDefault = els.wfExistingRuns.value;
          const multiOptions = els.wfExistingRuns.options.map((opt) => opt.value);
          els.wfExistingRuns.value = 'run-middle';
          els.wfExistingRuns.disabled = false;

          await sandbox.loadExistingRuns();
          const singleDefault = els.wfExistingRuns.value;
          const singleDisabled = els.wfUseExistingRun.disabled;

          await sandbox.loadExistingRuns();
          const emptyDefault = els.wfExistingRuns.value;
          const emptyDisabled = els.wfUseExistingRun.disabled;
          const emptyStatus = els.wfRunsStatus.textContent;

          await sandbox.loadExistingRuns();
          const unsortedDefault = els.wfExistingRuns.value;
          const unsortedOptions = els.wfExistingRuns.options.map((opt) => opt.value);

          console.log(JSON.stringify({
            multiDefault,
            multiOptions,
            singleDefault,
            singleDisabled,
            emptyDefault,
            emptyDisabled,
            emptyStatus,
            unsortedDefault,
            unsortedOptions,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["multiDefault"] == "run-newest"
    assert out["multiOptions"] == ["run-newest", "run-middle", "run-older"]
    assert out["singleDefault"] == "run-only"
    assert out["singleDisabled"] is False
    assert out["emptyDefault"] == ""
    assert out["emptyDisabled"] is True
    assert out["emptyStatus"] == "No existing runs found for this domain yet."
    assert out["unsortedDefault"] == "run-z-newest"
    assert out["unsortedOptions"] == ["run-z-newest", "run-m", "run-a"]


def test_workflow_existing_runs_preserves_active_selected_run_on_reload():
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
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          if (id === 'wfExistingRuns') {
            Object.defineProperty(el, 'innerHTML', {
              set(value) {
                this._innerHTML = value;
                this.children = [];
                this.options = [];
                this.value = '';
                if (String(value).includes('No runs found')) this.options.push({ value: '' });
              },
              get() { return this._innerHTML || ''; },
            });
          }
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));

        const runPayload = {
          runs: [
            { run_id: 'run-older', created_at: '2026-03-10T10:00:00Z' },
            { run_id: 'run-newest', created_at: '2026-03-12T10:00:00Z' },
            { run_id: 'run-middle', created_at: '2026-03-11T10:00:00Z' },
          ],
        };

        const sandbox = {
          console,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-middle' }, history: { replaceState(){} } },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => makeElement(tag),
          },
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) return { ok: true, json: async () => runPayload };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'ready' }, run: { run_id: 'run-middle' } }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);

        (async () => {
          await sandbox.initWorkflow();
          els.wfExistingRuns.value = 'run-middle';
          await els.wfUseExistingRun.click();
          await sandbox.loadExistingRuns();
          const afterReload = els.wfExistingRuns.value;
          console.log(JSON.stringify({ afterReload }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["afterReload"] == "run-middle"


def test_upsert_job_status_keeps_utc_storage_timestamps(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    sys.modules.setdefault(
        "jsonschema",
        types.SimpleNamespace(validate=lambda *_a, **_k: None, ValidationError=Exception, Draft7Validator=object),
    )
    from app.skeleton_server import _upsert_job_status

    state = {"runs": []}

    def fake_load(_domain):
        return state

    def fake_save(_domain, payload):
        state.clear()
        state.update(payload)

    monkeypatch.setattr("app.skeleton_server._load_runs", fake_load)
    monkeypatch.setattr("app.skeleton_server._save_runs", fake_save)
    monkeypatch.setattr("app.skeleton_server.time.strftime", lambda *_args, **_kwargs: "2026-01-15T10:00:00Z")

    _upsert_job_status("example.com", "r1", {"job_id": "j1", "status": "queued"})

    run = state["runs"][0]
    job = run["jobs"][0]
    assert run["created_at"] == "2026-01-15T10:00:00Z"
    assert job["created_at"] == "2026-01-15T10:00:00Z"
    assert job["updated_at"] == "2026-01-15T10:00:00Z"


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
          window: { location: { search: '?domain=example.com&run_id=run-77' }, history: { replaceState(){} }, addEventListener(){} },
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

        setTimeout(() => {
          console.log(JSON.stringify({ top: els.continueCheckLanguages.href, bottom: els.continueCheckLanguagesBottom.href }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    expected = "/check-languages?domain=example.com&en_run_id=run-77"
    assert out["top"] == expected
    assert out["bottom"] == expected


def test_workflow_defaults_to_latest_run_by_timestamp_and_preserves_manual_selection_for_pulls_link():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            _value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            get value(){ return this._value; },
            set value(v){ this._value = String(v || ''); },
          };
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfSavedUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';
        els.wfExistingRuns.options = [];
        Object.defineProperty(els.wfExistingRuns, 'innerHTML', {
          set(value) { this._innerHTML = value; if (value === '') { this.children = []; this.options = []; this._value = ''; } },
          get() { return this._innerHTML || ''; },
        });

        const historyUrls = [];

        const sandbox = {
          console,
          URLSearchParams,
          window: {
            location: { search: '?domain=example.com' },
            history: { replaceState: (_s, _t, url) => historyUrls.push(url) },
          },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) {
              return {
                ok: true,
                json: async () => ({
                  runs: [
                    { run_id: 'run-aaa', created_at: '2026-03-27T10:00:00Z', jobs: [] },
                    { run_id: 'run-zzz', created_at: '2026-03-28T10:00:00Z', jobs: [] },
                  ],
                }),
              };
            }
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'ready' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        (async () => {
          await new Promise((resolve) => setTimeout(resolve, 0));
          const defaultSelected = els.wfExistingRuns.value;
          const defaultContinueHref = els.wfContinuePulls.href;
          els.wfExistingRuns.value = 'run-aaa';
          await els.wfUseExistingRun.dispatch('click');
          const manualContinueHref = els.wfContinuePulls.href;
          console.log(JSON.stringify({ defaultSelected, defaultContinueHref, manualContinueHref, historyUrls }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["defaultSelected"] == "run-zzz"
    assert out["defaultContinueHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["manualContinueHref"].endswith("domain=example.com&run_id=run-aaa")
    assert any("run_id=run-aaa" in entry for entry in out["historyUrls"])


def test_pulls_respects_explicit_run_and_uses_latest_timestamp_when_missing_and_keeps_single_resolved_run():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function runScenario(search, mutateSearchAfterInit = '') {
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
              dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
              querySelector(){ return { innerHTML: '', appendChild(){} }; },
            };
          }

          const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
          const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
          const pullCalls = [];
          const runsCalls = [];
          const replaced = [];
          const generatedRunIds = [];

          const sandbox = {
            console,
            URLSearchParams,
            window: {
              location: { search },
              history: { replaceState: (_s, _t, url) => replaced.push(url) },
              addEventListener() {},
            },
            document: { getElementById: (id) => els[id], createElement: () => makeElement('created'), addEventListener(){} },
            safeReadPayload: async (response) => response.json(),
            setTimeout: (fn) => { fn(); return 1; },
            clearTimeout: () => {},
            ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
            fetch: async (url, init = {}) => {
              if (url.startsWith('/api/pulls?')) {
                pullCalls.push(url);
                return { ok: true, status: 200, json: async () => ({ rows: [] }) };
              }
              if (url.startsWith('/api/capture/runs?')) {
                runsCalls.push(url);
                return { ok: true, status: 200, json: async () => ({
                  runs: [
                    { run_id: 'run-zzz', created_at: '2026-03-27T10:00:00Z' },
                    { run_id: 'run-aaa', created_at: '2026-03-28T10:00:00Z' },
                  ],
                }) };
              }
              if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
              if (url.startsWith('/api/workflow/status?')) {
                return { ok: true, status: 200, json: async () => ({ eligible_dataset: { status: 'ready', en_standard_display_name: 'EN_standard_10:00|29.03.2026' }, run: {} }) };
              }
              if (url === '/api/workflow/generate-eligible-dataset') {
                if (init?.body) {
                  const parsed = JSON.parse(init.body);
                  generatedRunIds.push(parsed.run_id || '');
                }
                return {
                  ok: true,
                  status: 200,
                  json: async () => ({ status: 'started' }),
                  text: async () => '',
                  body: {
                    getReader: () => ({
                      read: async () => ({ done: true, value: null }),
                    }),
                  },
                };
              }
              return { ok: true, status: 200, json: async () => ({}) };
            },
          };

          vm.createContext(sandbox);
          vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);
          return new Promise((resolve) => setTimeout(async () => {
            if (mutateSearchAfterInit) sandbox.window.location.search = mutateSearchAfterInit;
            await els.pullsPrepareCapturedData.dispatch('click');
            resolve({
              pullCalls,
              runsCalls,
              replaced,
              summary: els.pullsWorkflowContextSummary.textContent,
              contextHref: els.pullsOpenContexts.href,
              issuesHref: els.pullsOpenIssues.href,
              nextHref: els.continueCheckLanguages.href,
              prepareStatus: els.pullsPrepareCapturedDataStatus.textContent,
              generatedRunIds,
            });
          }, 0));
        }

        (async () => {
          const explicit = await runScenario('?domain=example.com&run_id=run-zzz', '?domain=example.com&run_id=run-aaa');
          const inferred = await runScenario('?domain=example.com');
          console.log(JSON.stringify({ explicit, inferred }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert any("run_id=run-zzz" in call for call in out["explicit"]["pullCalls"])
    assert out["explicit"]["runsCalls"] == []
    assert "run: run-zzz" in out["explicit"]["summary"]
    assert out["explicit"]["contextHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["explicit"]["issuesHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["explicit"]["nextHref"].endswith("domain=example.com&en_run_id=run-zzz")
    assert out["explicit"]["prepareStatus"] == "Captured data prepared successfully: EN_standard_10:00|29.03.2026."
    assert out["explicit"]["generatedRunIds"] == ["run-zzz"]
    assert any("run_id=run-aaa" in call for call in out["inferred"]["pullCalls"])
    assert len(out["inferred"]["runsCalls"]) == 1
    assert any("run_id=run-aaa" in url for url in out["inferred"]["replaced"])
    assert out["inferred"]["generatedRunIds"] == ["run-aaa"]


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
