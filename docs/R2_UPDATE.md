# R2 reproducibility update

This is an update of the working repository. It does not create a release tag,
an immutable archival record, or a DOI. The main branch remains maintained.

## Added

- Full-round and multi-pair logical functional verifiers and the Table 9 result
  record: six official vectors, 146 round-boundary states, and 12 joint-oracle
  cases including ideal phase and workspace cleanup.
- An eight-S-box Table 14 checker separating native gate counts, clean-wrapper
  resources, and 4T lowering estimates.
- Pinned source identities and native gate counts for the five selected DORCIS
  circuits, without rerunning the synthesis tool or vendoring its code.
- Historical seed-0 RECTANGLE and KLEIN records selected for Tables 1 and 14.
- A map from current manuscript table numbers to the modular evidence files.

## Updated

- GIFT's catalog minimum status now includes the existing conclusive
  300-second retry, within the adopted bounded AND-depth-2 model.
- The README and reproduction guide include the new commands and distinguish
  functional checks from resource-model calculations.
- File inventories and checksums are regenerated after validation.

Existing manuscript resource values and historical solver logs are retained.
PRINCE's unresolved lower instances are retained as UNKNOWN.

## Evidence coverage

RECTANGLE and KLEIN use the selected historical seed-0 records for their
Table 1 and Table 14 values. Their conversions are checked against those
records. Original selected netlists are not included, and no new SAT witness
is substituted. The six primary rows also have released gate-file evidence.

## Archival timing

A tagged release corresponding to the final accepted manuscript and its
version-specific DOI are planned upon acceptance and before publication.

The earlier `src/R2_repository_update_files.zip` is retained as an upload
record. Use the unpacked repository files and the commands in the
reproduction guide for verification.
