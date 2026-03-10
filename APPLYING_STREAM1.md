# APPLYING_STREAM1.md

## What to do

Apply these files into the repository:

- replace root `README.md`
- add root `RELEASE_CRITERIA.md`
- add `docs/PRODUCT_TRUTHSET.md`
- use `docs/ABOUT_PAGE_COPY.md` as the new source text for the `/about` page

## Why this package exists

The repository and public-facing copy drifted:

- some docs still describe the project as almost entirely mock/scaffold;
- the current codebase and public UI already expose real artifact-backed behavior;
- the product is still not production-ready.

This package aligns messaging without overstating readiness.

## Recommended commit message

`docs: align README/about/release criteria with current pre-production status`

## After applying

After merging these files, do a quick pass to ensure the actual About page route or template uses the same wording as `docs/ABOUT_PAGE_COPY.md`.
