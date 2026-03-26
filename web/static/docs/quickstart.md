# Quickstart workflow

A typical operator flow is:

1. Manage seed URLs on `/urls`.
2. Discover or inspect URLs (`/crawler` for inventory inspection).
3. Capture English pages (pipeline endpoint flow).
4. Review pulled elements and apply annotation rules (`/pulling`).
5. Build the English eligible dataset (Phase 3).
6. Capture target-language pages and run comparison (Phase 6).
7. Search issues from `/` by applying a query.

Note: several phase triggers exist as backend APIs even when a page remains pre-production or internal-operator-oriented.
