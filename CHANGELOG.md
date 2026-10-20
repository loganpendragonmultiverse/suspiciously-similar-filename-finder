# Changelog

## 1.2.1 — 2026-10-20

- Preserve Unicode letters and canonical equivalents in filename comparison; unrelated non-Latin or symbol names no longer collapse to empty strings.
- Validate numeric thresholds and boolean cross-directory controls without coercion.
- Prune .git before directory discovery and fail unreadable discovery explicitly.
- Create reports exclusively with an explicit dangling-link guard; retain all existing hash-budget and changing-file checks.

## 1.2.0 - 2026-10-16

- Require observed EOF and consistent metadata before verified content claims; zero-size virtual sources and exact-budget exhaustion remain unverified. Clarify first-encounter budget allocation.

- Stream candidate hashes with optional byte budgets and explicit unverified classifications.

## 1.1.0 - 2026-07-27

- Added SHA-256 exact-content classification for candidate filename pairs.
- Added opt-in cross-directory comparison, reason labels, and threshold validation.

## 1.0.0 - 2026-07-26

- Released the first complete Suspiciously Similar Filename Finder command-line workflow.
- Added deterministic reporting, representative examples, cross-platform tests, and explicit limitations.
