# Phase 6 failures F6-014 through F6-016

This file is an append-only continuation of `PHASE6_FAILURE_LOG.md`. It is separate only because F6-013 was already split into its own evidence file. These rules are mandatory under `AGENTS.md`.

## F6-014 — traced server failure summary was written to stderr but run capture used stdout-only `tee`

**Symptom**

The first Audit-V2 real-device run produced useful exception-time state on the server terminal (`phase`, request counts, bytes and last request), but the persisted `phase6-v2-server.txt` did not contain that summary.

**Mistake**

The traced NBD server printed the transport exception summary to stderr while the launcher/run guidance relied on stdout-only `| tee` capture.

**Impact**

Persisted files alone could not initially establish the final successful request/count/server syscall phase. The terminal scrollback had to be recovered manually.

**Fix**

The launcher was changed to merge stderr into stdout (`2>&1`) before `tee`. The NBD protocol/server implementation itself was not changed for this fix.

**Permanent rule**

Every real-device experiment must define all required evidence files before the run and must prove that stderr/stdout channels needed for interpretation are persisted. Observation plumbing must not be confused with protocol/runtime changes.

---

## F6-015 — stale `/proc/last_kmsg` provenance was assumed after Run1

**Symptom**

A later recovery plan initially proposed reading `/proc/last_kmsg` and treating the result as evidence for Run1.

**Mistake**

The plan implicitly assumed that no intervening kernel boot/reset had occurred after Run1. That fact was not known.

**Impact**

A successfully captured previous-boot console could have been incorrectly attributed to Run1.

**Permanent rules**

1. `last_kmsg` is evidence for a named run only when previous-boot provenance is controlled as part of that same experiment.
2. After-the-fact time gaps or unknown intervening boots make provenance `UNKNOWN`.
3. Missing `last_kmsg` never proves a userspace reboot.
4. A recovery helper is an evidence transport utility, not proof of which run produced the data.

---

## F6-016 — no mandatory startup protocol; total design and checkpoint drifted from implementation/history

**Symptom**

Runtime-critical facts such as the accepted BusyBox invocation contract and the continuation's panic settings had to be repeatedly rediscovered from code. `DISKLESS_V2_EXECUTION.md`, `PROGRESS.md`, and Phase6 evidence documents also contained different generations of “current state” text.

**Mistake**

The repository had a total design document but no root `AGENTS.md` requiring every new work session to read it, the current checkpoint, the active evidence documents, and failure history before acting. Accepted runtime changes were often recorded in scripts/phase notes without being promoted back into the total design source of truth.

**Impact**

Reasoning repeatedly restarted from incomplete conversational context, already-revoked ideas were reconsidered, implementation details were rediscovered as if new, and hardware experiments could be proposed before all authoritative state was reconciled.

**Fix**

A repository-root `AGENTS.md` now defines mandatory startup, document authority, evidence vocabulary, frozen boundaries, experiment discipline, causality rules, and documentation-sync requirements. `DISKLESS_V2_EXECUTION.md` has been rebuilt as the project-wide design/runtime source of truth, and `PROGRESS.md` has been reduced to a concise checkpoint.

**Permanent rules**

1. Conversation memory is never project authority.
2. Before any code change, experiment proposal, or hardware command, read `AGENTS.md`, the complete total design document, the complete current checkpoint, the active phase evidence, and Phase6 failure history.
3. If code and authoritative documents disagree, hardware work stops until reconciliation.
4. A runtime fact that exists only in code is not an accepted project fact.
5. Script existence does not authorize a hardware run.
6. Documentation synchronization is part of every meaningful runtime change, not later cleanup.
7. Phase documents may preserve historical status, but they do not override the total design + current checkpoint.

---

## Governance state after F6-016

```text
AGENTS.md                         ACTIVE / MANDATORY
DISKLESS_V2_EXECUTION.md         project-wide source of truth
PROGRESS.md                      concise current checkpoint
Phase1-5                         ACCEPTED / FROZEN
Phase6                           ACTIVE
hardware                         PAUSED
panic-hold scripts               PROPOSED_DIAGNOSTIC / NOT AUTHORIZED
Run1 last_kmsg provenance        UNKNOWN after the fact
```
