# Development contract

Identify likely duplicate or versioned filenames such as final, final-2, and copy variants.

Version 1.1 adds exact-content evidence for candidate pairs and opt-in cross-directory comparison; it never deletes, renames, or merges files.

Preserve deterministic, source-safe behavior and the interpretation boundary documented in the README. Every feature release must update tests, version metadata, changelog, README claims, repository metadata, release assets, and the Forge catalog together.


## Version 1.2.0

JSON input accepts optional `max_hash_bytes_per_file` and `max_hash_bytes_total` non-negative integer byte limits. Omitted or null limits preserve unlimited hashing. For example:

```json
{"root":"./documents","max_hash_bytes_per_file":10485760,"max_hash_bytes_total":52428800}
```

Candidate files are streamed in chunks of at most 1 MiB, hashed once per scan, and charged against the total by bytes actually read. A file whose observed size exceeds a remaining limit is skipped; later smaller candidates may still fit. Candidate pairs are visited in combinations of sorted paths; files consume budgets when first encountered in a qualifying pair. A later path in an early pair can therefore consume budget before an earlier path in a later pair. Reports expose `hash_bytes_read`, per-file `hash_status` (`hashed`, `per_file_budget`, `total_budget`, `unreadable`, or `changed`) and pair `content_status` (`identical`, `different`, or `unverified`). Unverified pairs have `exact_content: null` and never contribute to the exact-content count. Hashing checks file identity, size and timestamps before/after reading and at final classification; it is a point-in-time local audit, not a filesystem snapshot or proof against deliberate timestamp manipulation.


A digest is verified only after the stream returns EOF and the bytes read agree with stable metadata. Virtual files whose content disagrees with st_size remain unverified. A zero-byte budget cannot verify even an empty file. If a limit is exhausted exactly at the observed size, the file remains unverified because checking EOF could consume another byte. Leave at least one byte of available allowance for that EOF check; an EOF read consumes zero bytes. Actual content bytes, including bytes from an unverified attempt, are charged to the budget.

The 1.2.1 audit corrects Unicode empty-name matches, typed controls, discovery
failures and report creation. Keep every existing hash-budget, EOF, stat/fstat and
changing-file regression and the 90% branch-coverage gate.
