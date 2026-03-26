                    ┌──────────────────────────────┐
                    │          OPERATORS            │
                    │  (single human maintainer)   │
                    └──────────────┬───────────────┘
                                   │
                                   │
                    ┌──────────────▼──────────────┐
                    │           UI Layer           │
                    │                              │
                    │  /urls                       │
                    │  /workflow                   │
                    │  /contexts                   │
                    │  /pulls                      │
                    │  /check-languages            │
                    │  / (issues)                  │
                    │                              │
                    └──────────────┬───────────────┘
                                   │
                                   │ writes
                                   ▼
                      ┌─────────────────────────┐
                      │     CONFIG ARTIFACTS    │
                      │  (GCS – domain scoped)  │
                      │                         │
                      │ seed_urls.v1.json       │
                      │ recipes/*.v1.json       │
                      │                         │
                      └─────────────┬───────────┘
                                    │
                                    │ pipeline trigger
                                    ▼

╔════════════════════════════════════════════════════════════════╗
║                         CAPTURE PIPELINE                       ║
╚════════════════════════════════════════════════════════════════╝

              ┌────────────────────────────────────┐
              │            Phase 1                 │
              │        BASELINE PULL               │
              │                                    │
              │ Input: seed_urls                   │
              │                                    │
              │ Playwright                         │
              │  - open URL                        │
              │  - wait stable                     │
              │  - extract DOM                     │
              │  - detect elements                 │
              │  - full-page screenshot            │
              │                                    │
              │ state = baseline                   │
              └──────────────┬─────────────────────┘
                             │
                             │
                             ▼

              ┌────────────────────────────────────┐
              │      UNIVERSAL SECTIONS ENGINE     │
              │                                    │
              │ Input: EN baseline pages           │
              │                                    │
              │ Detect repeating structures        │
              │ (header/footer/navigation)         │
              │                                    │
              │ Deterministic fingerprinting       │
              │                                    │
              │ Output: universal_sections         │
              └──────────────┬─────────────────────┘
                             │
                             │
                             ▼

              ┌────────────────────────────────────┐
              │        SCRIPTED CAPTURE ENGINE     │
              │                                    │
              │ Input: interaction_recipes         │
              │                                    │
              │ Playwright executes steps          │
              │                                    │
              │ capture_state("...")               │
              │ produces                           │
              │                                    │
              │ new capture contexts               │
              │                                    │
              │ state examples:                    │
              │  gallery_photos_open               │
              │  modal_signup_open                 │
              │  comments_panel_open               │
              │                                    │
              │ Each state → 1 screenshot          │
              └──────────────┬─────────────────────┘
                             │
                             │
                             ▼

              ┌────────────────────────────────────┐
              │       CAPTURE ARTIFACT STORAGE     │
              │                                    │
              │ GCS (deterministic structure)      │
              │                                    │
              │ /pages                             │
              │ /elements                          │
              │ /screenshots                       │
              │                                    │
              │ Key structure:                     │
              │ domain/url/state/tier/viewport     │
              └──────────────┬─────────────────────┘
                             │
                             │
                             ▼

              ┌────────────────────────────────────┐
              │        CAPTURE REVIEW UI           │
              │                                    │
              │ Human reviews screenshots          │
              │                                    │
              │ If overlay blocks content:         │
              │                                    │
              │ mark: blocked_by_overlay           │
              │                                    │
              │ system schedules rerun             │
              └──────────────┬─────────────────────┘
                             │
                             │
                             ▼

╔════════════════════════════════════════════════════════════════╗
║                       ANALYSIS PIPELINE                        ║
╚════════════════════════════════════════════════════════════════╝

              ┌────────────────────────────────────┐
              │           Phase 2                  │
              │          ANNOTATION                │
              │                                    │
              │ Annotators label elements          │
              │                                    │
              │ Context visible:                   │
              │  URL                               │
              │  state                             │
              │  language                          │
              │  user tier                         │
              │                                    │
              │ universal_sections collapsed       │
              └──────────────┬─────────────────────┘
                             │
                             ▼

              ┌────────────────────────────────────┐
              │           Phase 3                  │
              │      ELIGIBLE DATASET BUILD        │
              │                                    │
              │ Includes                           │
              │  baseline states                   │
              │  scripted states                   │
              │  universal sections                │
              └──────────────┬─────────────────────┘
                             │
                             ▼

              ┌────────────────────────────────────┐
              │         TARGET PULL                │
              │                                    │
              │ Run capture for                    │
              │  all languages                     │
              │  all states                        │
              │  all user tiers                    │
              └──────────────┬─────────────────────┘
                             │
                             ▼

              ┌────────────────────────────────────┐
              │           PAIRING                  │
              │                                    │
              │ Pair items using                   │
              │                                    │
              │ item_id = sha1(                    │
              │  domain + url + selector + bbox   │
              │  + element_type                    │
              │ )                                  │
              └──────────────┬─────────────────────┘
                             │
                             ▼

              ┌────────────────────────────────────┐
              │           Phase 6                  │
              │       ISSUE GENERATION             │
              │                                    │
              │ Detect issues:                     │
              │                                    │
              │ translation mismatch               │
              │ missing translation                │
              │ layout overflow                    │
              │ missing state                      │
              │ overlay-blocked capture            │
              └────────────────────────────────────┘
			  
			  
Capture Context Structure (Core System Concept)

Every captured page must belong to a capture context.

capture_context = (
    url,
    viewport_kind,
    state,
    user_tier
)

Example contexts:

/profile | desktop | baseline | guest
/profile | desktop | gallery_photos_open | guest
/profile | desktop | gallery_photos_open | premium
/pricing | mobile | modal_signup_open | guest

Each context produces:

1 full-page screenshot
1 page artifact
1 elements artifact
Artifact Storage Layout (GCS)

Example structure:

gs://watchdog-data/

domain/
   example.com/

      pages/
         url_hash/
            state/
               viewport/
                  user_tier/
                     page.json

      elements/
         url_hash/
            state/
               viewport/
                  user_tier/
                     elements.json

      screenshots/
         url_hash/
            state/
               viewport/
                  user_tier/
                     screenshot.png

Deterministic keys ensure reproducibility.

Recipe Execution Model

Recipe:

recipe_id: profile_interactions
url_pattern: /profile

Execution steps:

navigate /profile

capture_state("baseline")

click photos_tab
wait photos_grid
capture_state("gallery_photos_open")

click videos_tab
wait videos_grid
capture_state("gallery_videos_open")

click comments_tab
wait comments_loaded
capture_state("comments_panel_open")

Output:

4 capture contexts
4 screenshots
4 element datasets
Screenshot Review Flow

Human operator workflow:

Open Capture Review UI

Browse screenshots

Detect overlay problems

Example problem:

advert popup covering content
cookie wall
newsletter modal

Operator action:

mark capture = blocked_by_overlay

System reaction:

enqueue rerun for that exact capture context

Example rerun target:

url: /pricing
state: baseline
language: FR
tier: guest
viewport: desktop
Dry Run Execution

Dry run is a real pipeline run with restricted scope.

Example:

languages = [EN]
urls = 2
recipes = enabled
tiers = guest
viewport = desktop

Purpose:

verify selectors

verify states

verify DOM stability

verify screenshot correctness

detect overlay issues

Only after dry run passes should a full run across 38 languages be triggered.

