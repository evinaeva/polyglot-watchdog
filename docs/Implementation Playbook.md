Polyglot Watchdog – Implementation Playbook for Interactive Capture
Purpose

This document translates the architecture specification into an implementation-oriented guide. It is written to reduce ambiguity for engineers building the system and to make explicit how contract constraints must be enforced in code.

This playbook does not override the contract. The contract remains the normative source of truth.

1. Core Implementation Principle

The system must model each meaningful UI configuration as a separate capture context.

A capture context is:

(url, viewport_kind, state, user_tier)

Each capture context must produce exactly:

one full-page screenshot

one page artifact

one elements artifact

This is non-negotiable.

The implementation must never produce multiple screenshots for a single capture context. If a recipe reaches multiple meaningful UI states, each one must become a separate capture context with a distinct state.

2. Recommended Internal Architecture

The implementation should be split into the following logical modules:

2.1 Configuration Layer

Responsible for reading and validating:

seed URLs

recipe definitions

language list

viewport configuration

user tier configuration

2.2 Capture Planner

Responsible for expanding configuration into a deterministic execution plan.

Inputs:

seed URLs

recipes

languages

viewports

user tiers

Outputs:

a deterministic list of capture jobs

Each job must contain:

domain

url

language

viewport_kind

user_tier

state

recipe_id if applicable

capture point identifier if applicable

2.3 Playwright Session Runner

Responsible for:

browser setup

authentication or session initialization for user tier

page navigation

execution of recipe steps

stabilization waits

extraction trigger points

full-page screenshot capture

2.4 DOM Extraction Layer

Responsible for collecting raw page state in a deterministic way.

This layer must:

read the DOM after the page is stabilized

collect visible candidate elements

preserve text exactly as collected

not normalize away double spaces

not blanket-exclude numeric or price content

2.5 Artifact Builder

Responsible for:

page artifact generation

element artifact generation

screenshot storage

deterministic ordering

schema validation

2.6 Review and Rerun Layer

Responsible for:

surfacing screenshots to human review UI

storing review decisions

queuing exact capture-context reruns

2.7 Pairing and Issue Layer

Responsible for:

building datasets

pairing source and target items

generating issue artifacts

3. Recipe Design Model

A recipe is not just “a script for a page.”
A recipe is a deterministic description of:

how to reach one or more UI states

where to capture those states

A recipe should support two types of instructions:

3.1 Action Steps

Examples:

navigate

click

press

scroll

wait_for_selector

wait_for_hidden

wait_for_url

wait_for_function

3.2 Capture Points

A capture point marks the exact moment when the current page state must be serialized into pipeline artifacts.

Conceptually:

capture_state("gallery_photos_open")

This means:

freeze the current capture context with state = gallery_photos_open

collect page artifact

collect elements artifact

capture one full-page screenshot

The recipe runner should not treat capture points as optional logs. A capture point is a first-class pipeline output boundary.

4. Recipe Authoring Rules

To keep recipes maintainable and deterministic, the implementation should enforce the following rules.

4.1 Stable Naming

Each capture point must define a stable state string.

Examples:

baseline

modal_signup_open

gallery_photos_open

gallery_videos_open

comments_panel_open

accordion_faq_expanded

messages_panel_open

4.2 Explicit Waits

After every meaningful UI action, the recipe must include a deterministic wait.

Bad pattern:

click button
sleep 1000

Preferred pattern:

click button
wait_for_selector ".comments-panel"
4.3 No Implicit Capture

The system must never guess that “the page looks different enough, so it should capture now.”

Capture points must be explicit.

4.4 No Infinite Recovery Logic

The runner should not perform uncontrolled retries inside a recipe step chain.

If a required selector or postcondition is not reached, the recipe execution should fail explicitly.

4.5 No Ambiguous Conditional Branching for v1.0

For v1.0, recipe logic should remain mostly linear.
The system should avoid free-form branch logic such as:

if this appears, do A, else do B, else try C

That creates interpretive complexity and weakens determinism.

5. Playwright Runner Recommendations
5.1 Session Isolation

Each capture job should run in an isolated browser context.

This reduces contamination between:

languages

user tiers

URLs

recipes

5.2 Language Control

The implementation should ensure that the target language is actually applied before capture. This may be done through:

locale-aware URL structure

account preference

language switch logic before navigation

a controlled session mechanism

The implementation must not assume that “current session language is probably correct.”

5.3 User Tier Control

The system must establish the expected user tier deterministically:

guest

free

premium

This usually requires separate session initialization paths or credentials.

Tier selection must happen before state capture and must be auditable in logs.

5.4 SPA Stability

The implementation must not rely solely on generic networkidle semantics for SPA pages.

Instead, the runner should support page-specific waits such as:

target panel visible

loader hidden

route marker visible

known component mounted

DOM mutation settled for a short bounded period

5.5 Screenshot Timing

A screenshot should only be taken after:

required target elements are present

transient loaders are gone

the page has reached the intended state

6. Implementing capture_state(...)

The system should implement a dedicated internal primitive similar to:

capture_state(state_name)

The primitive should perform all of the following in a deterministic sequence:

Validate that the state name is legal

Build capture context

Compute deterministic storage key

Extract page content

Extract elements

Sort output deterministically

Capture one full-page screenshot

Validate artifacts against schema

Persist artifacts to GCS

A useful internal shape is:

capture_state(
    domain,
    url,
    language,
    viewport_kind,
    user_tier,
    state,
    page
)

The recipe author should never have to manually orchestrate artifact writing.

7. Deterministic Item Generation

The contract states that:

item_id = sha1(domain + url + css_selector + bbox(x,y,w,h) + element_type)

Text must not be part of item_id.

Implementation implications:

7.1 Bounding Box Must Be Captured Consistently

Bounding boxes must be measured after the page is stable.

7.2 CSS Selector Must Be Stable

The selector generation algorithm must be deterministic.

The system should avoid selector generation strategies that depend on traversal order that can vary across runs.

7.3 Ordering Must Be Deterministic

Before writing output, all items must be sorted deterministically, for example by:

item_id

The system should not preserve browser traversal order unless it is proven stable.

7.4 Fail Fast on Non-Determinism

If the implementation cannot guarantee deterministic selector generation or deterministic output ordering, the pipeline must fail explicitly.

This is better than silently producing divergent artifacts.

8. Text Collection Rules

The implementation must preserve raw collected text in a contract-safe manner.

Explicitly:

do not normalize away double spaces

do not apply “helpful cleanup” that changes the source text

do not blanket-exclude numeric strings

do not blanket-exclude price-like content

Any normalization beyond contract rules risks invalidating downstream translation checks.

9. Overlay Handling

The system must distinguish between:

intentional interactive overlays that are themselves the target of capture

blocking overlays that corrupt the capture

9.1 Intentional Overlays

Examples:

modal intentionally opened by recipe

accordion intentionally expanded

notification toast intentionally triggered

These are valid capture states.

9.2 Blocking Overlays

Examples:

random ad popup

surprise newsletter interstitial

cookie wall that unexpectedly blocks main content

region picker injected at runtime

These are invalid if they prevent correct page capture.

The review system must support a status like:

blocked_by_overlay

Such captures should not proceed into annotation or dataset generation until rerun succeeds.

10. Review and Rerun Implementation

The UI should present screenshots indexed by:

language

URL

state

user tier

viewport

review status

The operator must be able to mark a capture as invalid.

The rerun queue must store the exact capture context, not merely the URL.

A rerun request should preserve:

domain

url

language

viewport_kind

user_tier

state

recipe_id or baseline mode

The rerun must execute the same path that produced the original capture.

11. Universal Sections Implementation

Universal sections are EN-only and are intended to collapse repeated content such as:

header

footer

navigation

Recommended approach:

Start from EN baseline captures only

Extract candidate repeated blocks

Generate stable fingerprints

Group identical or near-identical repeated structures

Choose representative sections deterministically

Deterministic representative selection is important. For example, choose the representative using a stable ordering over page identifiers or fingerprints.

The implementation must not allow universal sections to absorb content that is page-specific.

False positives are dangerous because they can erase meaningful page content from annotation coverage.

12. Annotation View Model

Annotators must be able to understand exactly what they are labeling.

The annotation UI should display:

language

URL

state

user tier

viewport

screenshot

source of item

page-specific

universal section

The UI should make the difference between baseline and scripted states visually obvious.

13. Pairing Logic Across Languages

Because the content is assumed to be functionally equivalent across languages, the expected operational model is:

same seed URLs

same recipes

same state names

same user tiers

same viewports

This means the system should expect the same capture-state inventory across languages.

If a state is missing in a target language, this should be treated as a defect signal, not as an acceptable variation.

Possible causes:

recipe failed

selector drift

overlay blocked content

SPA failed to transition

localization broke the UI

14. Dry Run Implementation

Dry run should be implemented as a real pipeline mode with constrained scope.

Dry run characteristics:

real site

real browser automation

real credentials or real tier session if applicable

real artifacts

limited URL count

limited language count

limited recipe count

Dry run is not a mock mode.

A dry run should produce enough evidence for an operator to decide whether to launch a larger run.

15. Suggested Acceptance Tests
15.1 Baseline Contract Test

Given a seed URL, one language, one viewport, one user tier:

the system produces exactly one baseline screenshot

page artifact validates

elements artifact validates

15.2 Multi-State Recipe Test

Given a recipe with three capture points:

the system produces exactly three additional capture contexts

each has exactly one screenshot

states are named exactly as declared

15.3 Determinism Test

Running the same baseline capture twice under the same conditions should produce:

identical item ordering

identical item_id values

stable storage paths

15.4 Overlay Review Test

A reviewed screenshot marked blocked_by_overlay must:

be excluded from annotation eligibility

be visible in review UI

be rerunnable by exact capture context

15.5 Universal Sections Test

Repeated EN baseline sections should collapse into deterministic groups with stable representatives.

15.6 Cross-Language Recipe Reproduction Test

A recipe defined on the reference language should run for a target language and produce the same expected states.

16. Operational Guidance for a Small Team

Because the system is operated by a very small team, implementation should prioritize:

explicit status visibility

minimal hidden automation

reproducible reruns

clear failure reasons

precise scoping of work

The operator must always be able to answer:

which URLs were captured

which states were expected

which states succeeded

which failed

which were blocked by overlays

which were rerun

which are ready for annotation

This is more valuable than adding broad but opaque automation.

17. Final Implementation Mindset

The system should be designed around one core idea:

A large amount of careful one-time manual recipe authoring is acceptable and desirable if it allows highly repeatable automated execution across many languages over time.

This is not a failure of automation.
It is the correct architecture for a multilingual, interaction-heavy website where full content coverage matters.