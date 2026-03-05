SPEC LOCK + EXECUTION PROTOCOL

This document governs AI implementation.

Contract v1.0 defines behavior guarantees.

1. AI Implementation Rules

AI MUST:

implement pipeline phases sequentially

respect schema contracts

avoid architecture changes

AI MUST NOT:

redesign pipeline phases

change schema definitions

introduce alternative storage systems

2. Allowed Changes

AI may:

implement missing phases

add code consistent with schema contracts

add logging

AI must NOT:

rewrite crawler architecture

replace storage backend

change artifact schemas

3. STOP Conditions

AI must STOP if:

schema changes required

pipeline phases reordered

artifact formats unclear

Output:

STOP: requires architecture decision
4. Implementation Order

AI must implement in order:

Phase 0 crawler

Phase 1 extractor

Phase 2 UI annotation

Phase 3 filtering

Phase 4 OCR

Phase 5 normalization

Phase 6 QA checks

Skipping phases is forbidden.

Что получится после этого шага

Будет три уровня документации:

Тип	Документ	Назначение
Overview	docs/overview.md	описание системы
Contract	contract/watchdog_contract_v1.0.md	строгие правила
Spec lock	spec/SPEC_LOCK_EXECUTION_PROTOCOL.md	правила для AI
