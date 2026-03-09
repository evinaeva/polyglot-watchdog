# Glossary

- **Seed URLs**: Manually managed canonical URL list stored as `seed_urls.json`.
- **Capture context**: Runtime capture dimensions for a page (identity excludes language).
- **page_id**: Stable page identifier derived from capture-context identity dimensions.
- **item_id**: Stable element identifier derived from domain, URL, selector, bbox, and element type.
- **Template rules**: Phase 2 annotation decisions persisted as `template_rules.json`.
- **Eligible dataset**: English reference dataset after applying review/rules filtering in Phase 3.
- **Capture review status**: Review record keyed by capture context and language.
- **Exact context rerun**: Replay of a capture using the same context dimensions.
