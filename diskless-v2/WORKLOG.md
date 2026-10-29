# Diskless v2 — Batch work log

Status: **ACTIVE / APPEND-ONLY CHRONOLOGICAL LEDGER**.

Purpose: preserve handoff state after every coherent batch of work so later sessions do not reconstruct project history from chat, scattered scripts, or stale phase documents.

This file is **not** an architecture authority. Authority remains:

1. `AGENTS.md`
2. `DISKLESS_V2_EXECUTION.md`
3. `diskless-v2/PROGRESS.md`
4. active phase evidence documents / failure log

Each batch entry must record: starting point, completed work, evidence class, accepted conclusions, remaining unknowns, mistakes/revocations, changed files/commits, next question, and hardware authorization state.

---

## Batch 2026-10-29-A — Governance reset after Phase6 Run1

**Goal**

Stop Phase6 experiment drift and rebuild the project working protocol before any further real-device work.

**Starting state**

```text
Phase1–5       ACCEPTED / FROZEN
6V2-A/B/C      HOST PASS
6V2-D          REAL-DEVICE transport attach PASS
6V2-E          NOT REACHED
Run1 cause     UNKNOWN
hardware       had been moving toward ad-hoc follow-up diagnostics
```

The immediate trigger was repeated rediscovery of runtime facts from code, stale/competing current-state sections across documents, and an incorrect assumption about Run1 `/proc/last_kmsg` provenance.

**Completed work**

1. Added root `AGENTS.md` with mandatory startup, evidence, frozen-boundary, experiment, causality, change, and communication rules.
2. Reworked `DISKLESS_V2_EXECUTION.md` into the project-wide design/runtime source of truth instead of leaving it as an initial TODO plan.
3. Reduced `diskless-v2/PROGRESS.md` to a concise current checkpoint and explicitly paused hardware work.
4. Classified the recently added panic-hold and last-kmsg helpers as diagnostic proposals/utilities rather than hardware authorization.
5. Recorded governance/documentation failures in the Phase6 failure history.
6. Added mandatory batch checkpoint discipline to `AGENTS.md`.
7. Created this append-only `WORKLOG.md` so every future batch has a durable handoff record.

**Relevant commits**

```text
089efbf0c045250100a7a28af5e252ed2f075e29  add initial AGENTS.md governance
fc0278a2dbad39f2cb08b8c61f6e9b9f513a0908  promote execution document to source of truth
2a990b6fedfb269657c93e6d709a436ef3180450  reset PROGRESS to concise paused checkpoint
489681df255888307223c0283f1a5d50d1cce292  record governance/documentation failures
3bba8fc9e0277438af2139a07521d6cbd889ad12  require batch checkpoints/worklog handoff
```

**Evidence / classification**

```text
governance mechanism             HOST/REPOSITORY FACT
Phase1–5 accepted boundary       inherited REAL_DEVICE_FACT/HOST_FACT
Run1 reset/reboot cause          UNKNOWN
panic-hold idea                  PROPOSED_DIAGNOSTIC
old Run1 last_kmsg provenance    UNCONTROLLED / NOT ACCEPTED
```

**Accepted conclusions**

- `DISKLESS_V2_EXECUTION.md` is the sole project-wide architecture/runtime source of truth.
- `PROGRESS.md` is a checkpoint, not a competing design document.
- conversation memory and script existence are not authority.
- Phase1–5 remain frozen unless new evidence invalidates a gate.
- no further real-device Phase6 boot is authorized until the evidence/history is re-read under the rebuilt protocol and one experiment is explicitly approved.
- every future coherent batch must be closed in this worklog before a new batch begins.

**Remaining unknowns**

```text
Run1 kernel panic/oops path      UNKNOWN
Run1 kernel hang/deadlock        UNKNOWN
Run1 watchdog reset              UNKNOWN
Run1 userspace/init reboot       UNKNOWN
Run1 other reset path            UNKNOWN
6V2-E second-stage p3/p6         NOT REACHED
```

**Mistakes/revocations surfaced**

- project state had been allowed to live partly in code and chat rather than the total design document;
- no mandatory startup read/reconciliation procedure existed;
- multiple documents carried stale current-state sections;
- stale Run1 `last_kmsg` provenance was incorrectly assumed;
- diagnostic script creation was drifting too close to implicit hardware authorization.

**Next question / handoff**

Before proposing another real-device run:

```text
1. follow AGENTS.md startup procedure from the current HEAD;
2. re-read/reconcile all active Phase6 evidence and failure history;
3. identify the single highest-information unresolved binary question;
4. document one delta, outcomes, INCONCLUSIVE conditions, capture plan and stop rules;
5. only then change hardware authorization from PAUSED.
```

**Hardware authorization at batch close**

```text
PAUSED
```

---

## Template for future batches

```text
## Batch YYYY-MM-DD-X — <name>

Goal:
Starting branch/HEAD/checkpoint:
Work completed:
Evidence produced + class:
Accepted conclusions:
Remaining unknowns/hypotheses:
Mistakes/revocations:
Files/docs/commits changed:
Next exact question/handoff:
Hardware authorization state:
```
