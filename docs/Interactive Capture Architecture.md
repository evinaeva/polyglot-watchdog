Below is the final contract-aligned design document.
It assumes the existing contract (watchdog_contract_v1.0) remains authoritative and unchanged. All decisions below explicitly respect the invariants you listed.

The goal of this document is to remove ambiguity and prevent multiple interpretations during implementation.

Polyglot Watchdog – Interactive Capture Architecture
Final Implementation Specification (v1.0)

This document defines the final architecture and operational process for extending the existing Polyglot Watchdog pipeline to support scripted UI interactions and multiple UI states per URL while remaining compliant with:

contract/watchdog_contract_v1.0.md

contract/schemas/*.schema.json

The system is cloud-only (GCP) and must not introduce local or developer-specific workflows.

Crawler improvements (Phase 0 automatic discovery) are explicitly deferred.
All URLs are managed via a manually curated seed URL list through the UI.

The design prioritizes:

strict determinism

compatibility with the existing contract

scalability to dozens of languages

reproducibility across runs

operational practicality for a very small team

1. FINAL DEFINITION OF DONE (v1.0)

The system is considered v1.0 complete when all items below are implemented.

1.1 URL Management

Seed URLs must be managed via UI:

/urls

Requirements:

UI allows adding, removing, editing URLs.

URLs are stored in a domain-scoped configuration artifact.

Each URL may optionally have associated interaction recipes.

Crawler-based discovery is not required for v1.0.

1.2 Capture Context Model

The capture context is defined exactly as required by the contract:

(url, viewport_kind, state, user_tier)

Each capture context must produce:

exactly one full-page screenshot

a page artifact

element extraction artifacts

The system must enforce:

1 capture context = 1 screenshot

No exceptions.

1.3 Baseline Capture

For every seed URL and for every configured:

language

viewport

user tier

the system must capture the baseline state:

state = "baseline"

Baseline capture must:

navigate to the URL

wait for page stabilization

extract DOM

extract elements

capture a full-page screenshot

generate artifacts required by Phase 1.

1.4 Scripted Interaction Capture

The system must support manual Playwright interaction scripts ("recipes").

Recipes may produce multiple UI states from a single URL.

Each meaningful UI configuration must be captured as a separate state.

Example states:

baseline
modal_signup_open
gallery_photos_open
gallery_videos_open
comments_panel_open
avatar_picker_open
messages_panel_open
accordion_specs_expanded
notification_toast_visible

Each state must produce a separate capture context.

1.5 Universal Sections (EN-only)

Universal sections must be generated according to the contract.

Examples:

header

footer

navigation menus

Universal section collapsing must:

run after baseline EN capture

be deterministic

use stable fingerprinting.

The universal sections artifact must only use EN baseline captures.

1.6 Annotation Phase

Phase 2 annotation must support:

baseline items

universal section items

scripted-state items

Annotators must see:

URL
state
language
user tier
viewport

Universal sections must appear as collapsed reusable groups.

1.7 Eligible Dataset Build

Phase 3 dataset construction must include:

baseline states

scripted states

universal sections

Dataset eligibility must remain deterministic.

1.8 Target Language Pull

All recipes defined on the reference language must be executed for:

all target languages

The system must assume UI parity across languages.

Failure to reproduce a state on another language must be flagged as a capture failure.

1.9 Pairing

Pairing must operate using:

item_id

as defined by the contract.

Pairing must remain deterministic.

1.10 Issue Generation

Phase 6 is the translation-QA layer for CHECK LANGUAGES and the persisted source of SEE ERRORS.

Phase 6 must:

compare curated EN reference content against curated target-language content

consume OCR text only for approved `<img>` elements

treat OCR as a text source, not as the primary comparison target

run AI-assisted and deterministic checks over suspicious localization pairs

preserve evidence for later operator review

Working review classes for Phase 6 are:

SPELLING

GRAMMAR

MEANING

PLACEHOLDER

OCR_NOISE

OTHER

The current persisted `issues` schema remains authoritative for the top-level artifact shape; finer review classes may be preserved in evidence until the schema is revised.

Detailed design notes live in:

`docs/PHASE6_TRANSLATION_QA.md`

1.11 Deferred (Allowed)

The following are explicitly deferred without blocking v1.0:

broader OCR expansion beyond approved `<img>` flow

OCR on full-page screenshots or arbitrary visual regions

Phase 0 crawler improvements

Automated discovery improvements are not required.

automated overlay removal

Advertising overlays will not be automatically removed.

2. SCRIPTED INTERACTIONS MODEL
2.1 State Dimension Mapping

Scripted interactions are represented using the existing state dimension.

No new dimension is introduced.

Capture context remains:

(url, viewport_kind, state, user_tier)

This preserves compatibility with the contract.

2.2 State Naming Convention

All state names must follow a strict format.

<base_state>
<component>_<action>
<component>_<action>_<identifier>

Examples:

Baseline:

baseline

Modal states:

modal_signup_open
modal_pricing_open
modal_upgrade_prompt_open

Panels:

messages_panel_open
settings_panel_open
profile_panel_open

Galleries:

gallery_photos_open
gallery_videos_open

Accordion elements:

accordion_specs_expanded
accordion_faq_expanded

Notifications:

toast_success_visible
toast_error_visible

Menu states:

menu_main_open
menu_profile_open

Rules:

lowercase only

underscores only

no whitespace

stable names across languages

2.3 Recipe Model

A recipe is a Playwright script that produces deterministic UI states.

Recipes consist of:

steps
capture points

Steps perform actions.

Capture points define states.

Example conceptual recipe:

navigate /profile

capture_state("baseline")

click gallery_photos
wait photos_grid_visible
capture_state("gallery_photos_open")

click gallery_videos
wait videos_grid_visible
capture_state("gallery_videos_open")

click comments_tab
wait comments_loaded
capture_state("comments_panel_open")

Each capture point generates:

one capture context
one screenshot
one page artifact
one elements artifact
2.4 Handling DOM and Bounding Box Changes

DOM and layout changes between states are expected.

Since item_id depends on:

css_selector
bbox
element_type

items appearing in different states will generate different item_ids.

This behavior is acceptable.

The system treats states as independent capture contexts.

2.5 Overlay Elements

Overlay UI elements include:

modal dialogs

cookie banners

blocking advertisements

If an overlay blocks core page content, the capture is considered invalid.

Invalid captures must be labeled:

blocked_by_overlay

Such captures must not enter the annotation pipeline.

They must be eligible for manual re-run.

2.6 Scheduling Scripted Captures

Scripted captures are executed:

only for URLs with attached recipes

Execution order:

baseline capture

recipe execution

capture points produce states

Recipes are executed for:

every language
every user tier
every viewport
3. ARTIFACTS AND SCHEMAS

Only contract-safe extensions are introduced.

Maximum new artifacts: 3

3.1 Artifact: seed_urls

Type: configuration artifact

Purpose:

Stores the manually curated URL list.

Schema:

{
  domain: string,
  urls: [
    {
      url: string,
      description: string?,
      recipe_ids: [string]?
    }
  ]
}

Storage key:

gs://watchdog-config/{domain}/seed_urls.v1.json

Versioning:

seed_urls.v1.json
seed_urls.v2.json
3.2 Artifact: interaction_recipes

Type: configuration artifact.

Stores Playwright interaction definitions.

Schema outline:

{
  recipe_id: string,
  url_pattern: string,
  steps: [
    {
      action: string,
      selector: string?,
      wait_for: string?
    }
  ],
  capture_points: [
    {
      state: string
    }
  ]
}

Storage key:

gs://watchdog-config/{domain}/recipes/{recipe_id}.v1.json
3.3 Artifact: capture_review_status

Purpose:

Stores manual review results for capture contexts.

Schema:

{
  capture_context_id: string,
  status: enum("valid","blocked_by_overlay","retry_requested"),
  reviewer: string,
  timestamp: string
}

Storage:

gs://watchdog-review/{domain}/capture_status/{capture_context_id}.json
4. EXECUTION FLOW
4.1 Seed URL Management

Operators maintain URLs through the UI.

Changes update:

seed_urls artifact
4.2 Phase 1 – Baseline Pull

Input:

seed_urls
languages
viewports
user tiers

Output:

pages
elements
screenshots

State:

baseline
4.3 Universal Sections

Run only for:

EN baseline captures

Input:

EN baseline pages

Output:

universal_sections artifact
4.4 Scripted Pulls

Input:

interaction_recipes

Execution:

for each url with recipe
for each language
for each user tier
for each viewport

Recipes produce multiple states.

Each state produces a capture context.

4.5 Capture Review

Operators review screenshots in the UI.

If an advertising popup blocks content:

mark capture_context = blocked_by_overlay

UI allows:

re-run specific capture context
4.6 Phase 2 Annotation

Annotators see:

URL
state
language
viewport
user tier

Universal sections appear collapsed.

4.7 Phase 3 Dataset Build

Dataset includes:

baseline items
scripted-state items
universal section items

Eligibility rules remain deterministic.

4.8 Target Pull and Pairing

Target languages use identical:

recipes
states
URLs

Pairing uses:

item_id

The comparison model is:

EN reference ↔ target-language item

For approved image-based items, OCR text is attached to the item and participates in the same EN ↔ target comparison flow.

4.9 Phase 6 Issue Generation

Phase 6 is expected to generate persisted review candidates rather than an exhaustive dump of all pairs.

Required Phase 6 behavior:

AI-assisted checking for spelling, grammar, and likely meaning mismatch

deterministic placeholder and formatting checks

OCR text handling only for approved `<img>` items

baseline OCR path via OCR.Space `engine 3`

evidence-rich persisted issues for later review in SEE ERRORS

If a detailed review class does not fit the current coarse top-level issue enum, the finer class should still be preserved in evidence.
5. RISK REGISTER
1 Playwright Flakiness

Cause: timing issues
Impact: unstable captures
Mitigation: explicit wait conditions.

2 Selector Fragility

Cause: DOM changes
Impact: recipes break
Mitigation: prefer stable attributes.

3 Dynamic Content

Cause: personalized UI
Impact: inconsistent DOM
Mitigation: deterministic test accounts.

4 A/B Testing

Cause: variant UI
Impact: state mismatch
Mitigation: disable experiments where possible.

5 i18n Layout Shifts

Cause: text length differences
Impact: bbox differences
Mitigation: treat states independently.

6 Cookie Framework Variations

Cause: different consent UI
Impact: blocking overlays
Mitigation: manual overlay review.

7 Modal Overlay Capture

Cause: modal hides main content
Impact: invalid screenshot
Mitigation: overlay detection + rerun.

8 SPA Routing

Cause: networkidle unreliable
Impact: incomplete state capture
Mitigation: wait for specific DOM elements.

9 Time-dependent Content

Cause: rotating banners
Impact: inconsistent items
Mitigation: ignore ephemeral elements.

10 Determinism Regressions

Cause: unordered outputs
Impact: pairing failures
Mitigation: deterministic sorting.

11 Universal Section False Positives

Cause: repeated components misidentified
Impact: missing page content
Mitigation: strict fingerprint thresholds.

12 State Explosion

Cause: large number of meaningful UI states
Impact: processing cost
Mitigation: rely on operator-defined recipes.

6. RECOMMENDED NEXT IMPLEMENTATION STEPS
1 Seed URL System

Goal: manual URL management
Scope: UI + config artifact
Validation: artifact stored in GCS.

2 Recipe Storage Layer

Goal: store interaction scripts
Scope: recipe artifact schema
Validation: recipe retrieval works.

3 Playwright Recipe Runner

Goal: execute recipes
Scope: capture points -> states
Validation: states produce screenshots.

4 Capture Context Generator

Goal: enforce contract context structure
Scope: (url, viewport, state, tier)
Validation: deterministic context ids.

5 Screenshot + DOM Capture

Goal: generate Phase 1 artifacts
Validation: schema validation passes.

6 Screenshot Review UI

Goal: detect overlay-blocked captures
Validation: user marks screenshot invalid.

7 Target Language Execution

Goal: run recipes across all languages
Validation: states reproduced.

8 Deterministic Ordering

Goal: enforce item ordering
Validation: hash stability across runs.

9 Universal Sections Processor

Goal: detect shared sections
Validation: stable fingerprints.

10 Issue Generation Extension

Goal: add new issue categories
Validation: overlay issues reported.