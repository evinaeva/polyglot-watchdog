# Quickstart workflow

A typical operator flow is:

1. Manage seed URLs on `/urls`.
2. Start and monitor capture jobs from `/workflow`.
3. Review capture contexts and save review decisions from `/contexts`.
4. Apply annotation/template-rule decisions from `/pulls`.
5. Build the English eligible dataset (Phase 3) and generate issues (Phase 6) from `/workflow`.
6. Run target-language checks from `/check-languages`.
7. Search issues from `/` and use the `?` tooltip in each issue row for evidence drilldown.

Note: several phase triggers exist as backend APIs even when a page remains pre-production or internal-operator-oriented.
