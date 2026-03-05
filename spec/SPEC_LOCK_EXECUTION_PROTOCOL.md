# SPEC LOCK + EXECUTION PROTOCOL (STRICT MODE)

## 0. Authority
- This protocol governs AI implementation behavior.
- `contract/watchdog_contract_v1.0.md` defines normative system behavior guarantees.
- Implementations MUST conform to Contract v1.0 and MUST NOT alter architecture semantics without explicit contract revision.

## 1. AI Implementation Rules
AI agents MUST:
1. Implement and validate phases in numeric order (0 → 6).
2. Preserve artifact contracts and schema compatibility.
3. Keep URL-level screenshot model intact:
   - 1 URL = 1 screenshot
   - no per-element screenshot linkage
4. Respect the OPEN/DEFERRED status of Phase 4 in Contract v1.0.

AI agents MUST NOT:
- Redesign phase model.
- Introduce per-element screenshot schema fields.
- Define OCR engine/output internals under Contract v1.0.
- Replace storage architecture based on undocumented assumptions.

## 2. Allowed and Forbidden Change Types
### Allowed
- Fill missing implementation details that are already implied by Contract v1.0.
- Add validation and logging consistent with Contract v1.0.
- Add tests that verify contract conformance.

### Forbidden
- Reorder phases.
- Modify contract-defined artifact semantics without versioned contract update.
- Change schema meaning by implicit field repurposing.

## 3. Phase 4 Guardrail
For Contract v1.0, Phase 4 is OPEN/DEFERRED.
- AI MUST treat OCR behavior specification as out-of-scope.
- AI MAY only preserve interfaces/handoffs needed by neighboring phases.
- Any attempt to define OCR engine selection, consensus, or result schema requires explicit contract update.

## 4. STOP Conditions
AI MUST stop with exact output:
`STOP: requires architecture decision`

Trigger examples:
- Required behavior conflicts with Contract v1.0.
- A task requires defining deferred OCR internals.
- A task requires adding per-element screenshot ownership.
- Artifact format ambiguity blocks deterministic implementation.

## 5. Compliance Checklist (For AI Runs)
Before finalizing implementation, AI SHOULD verify:
- Contract precedence respected.
- Schemas unchanged in meaning.
- URL-level screenshot model preserved.
- Phase 4 OPEN/DEFERRED guardrail respected.
- Deterministic behavior maintained.
