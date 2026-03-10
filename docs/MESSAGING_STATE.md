# MESSAGING_STATE.md

## Purpose

This file defines the deterministic messaging states used by Stage D release gating.

## Decision rule

`GATE_PASSED = all(v1_0_required_criteria == pass)`

Source of criteria: `RELEASE_CRITERIA.md` required scope items 1-8.

Exactly one messaging state is valid at a time:

- `pre_production`
- `production_ready_v1_scope`

## State: `pre_production`

Use this wording block when any required criterion is `fail` or `unknown`:

- Stage: **late prototype / pre-production / operator-console-in-progress**
- Release claim: **not production-ready**
- Scope note: v1.0 scope is documented, but one or more release blockers remain.

## State: `production_ready_v1_scope`

Use this wording block only when all required criteria are `pass`:

- Stage: **production-ready for the documented v1.0 scope**
- Optional companion claim: **contract-aligned for the documented v1.0 flow**
- Scope note: this does not imply all future phases/polish are complete.

## Forbidden phrases (when gate is not passed)

- "production-ready"
- "mostly production-ready"
- "basically production-ready"
- "production-ready except"

## Always-forbidden drift phrases

- "entirely mock-backed"
- "zero implemented phases"
- "only a UI scaffold"

## Deferred scope reminder

The following are explicitly deferred and non-blocking for v1.0:

- OCR / Phase 4
- crawler improvements beyond accepted manual seed URL workflow
- extra UX polish beyond core v1.0 flow
