# AGENTS.md — nexus7_test working protocol

Scope: the entire repository. These rules are mandatory for any agent or coding session working on `diskless-v2`.

## 1. Mandatory startup procedure

Before proposing a code change, experiment, hardware command, root-cause theory, or next step:

1. Confirm repository/branch/HEAD (`git status --short`, `git branch --show-current`, `git rev-parse HEAD`).
2. Read this `AGENTS.md` completely.
3. Read `DISKLESS_V2_EXECUTION.md` completely. It is the project-wide architecture and accepted-runtime source of truth.
4. Read `diskless-v2/PROGRESS.md` completely. It is the current checkpoint only.
5. Read every active-phase document named by `PROGRESS.md`.
6. For Phase 6, read `diskless-v2/PHASE6_FAILURE_LOG.md` and any separately referenced `PHASE6_FAILURE_F6_*.md` before proposing another experiment.
7. Inspect commits newer than the last meaningful `PROGRESS.md` update and reconcile them with the documents above.
8. If documentation and implementation disagree, stop. Treat the disagreement as a defect to reconcile; do not silently choose code, conversation memory, or the newest commit as truth.

Do not use chat/conversation memory as project state. Memory may help locate material, but repository documents and exact artifacts are the authority.

## 2. Document authority

The authority order is:

1. `AGENTS.md` — how work must be performed.
2. `DISKLESS_V2_EXECUTION.md` — system design, accepted runtime contract, phase acceptance, current project-wide constraints.
3. `diskless-v2/PROGRESS.md` — concise current checkpoint and active question.
4. Phase documents (`diskless-v2/PHASE*.md`) — detailed experiment design/evidence/history.
5. `diskless-v2/PHASE6_FAILURE_LOG.md` — append-only mistakes and regression-prevention rules.
6. Code/scripts/artifacts — implementation to verify against the documents, not a replacement for them.

A runtime fact is not considered accepted merely because it exists in code. Accepted runtime facts must be reflected in `DISKLESS_V2_EXECUTION.md` with an evidence class.

Phase documents may contain historical status text. If they conflict with the current checkpoint, `DISKLESS_V2_EXECUTION.md` + `PROGRESS.md` govern, and the stale phase document must be reconciled before its claims are reused.

## 3. Evidence vocabulary

Use these labels explicitly:

- `REAL_DEVICE_FACT` — directly demonstrated on the physical Nexus 7.
- `HOST_FACT` — demonstrated by deterministic host-side build/audit/self-test only.
- `SOURCE_PROVEN` — established from the exact pinned source used by the project.
- `IMPLEMENTED_UNPROVEN` — present in the artifact/code but not independently demonstrated at runtime.
- `PROPOSED_DIAGNOSTIC` — a designed experiment or artifact that is not accepted architecture.
- `REVOKED` — previously proposed/claimed and explicitly invalidated.
- `UNKNOWN` — evidence is insufficient; do not infer a cause.

Never turn a `HOST_FACT`, `SOURCE_PROVEN`, or `IMPLEMENTED_UNPROVEN` item into a `REAL_DEVICE_FACT` by wording.

## 4. Frozen boundary

Phase 1–5 are accepted/frozen unless new evidence directly invalidates a gate.

Do not modify proven Phase 1–5 runtime mechanisms merely because a later Phase 6 run fails. In particular, a later USB/NBD disappearance is not by itself evidence that USB/NBD caused the failure.

Known real-device-proven conventions that require explicit justification before modification include:

- `/bin/busybox` and `#!/bin/busybox sh`;
- `/etc/diskless-v2-layout`;
- one USB ECM root-transport interface;
- one NBD session to the partitioned disk;
- Phase5 NBD attach/retry/liveness/partition-validation behavior;
- original Lineage init preserved as `/init.android` for handoff;
- accepted Phase5 fstab and partition mapping.

## 5. Experiment discipline

One experiment must answer one binary question.

Before any hardware experiment, its phase document or `PROGRESS.md` must state:

- the exact binary question;
- the single intended variable/delta;
- frozen inputs and artifact hashes where applicable;
- host preflight/gates that must pass;
- observable outcomes;
- interpretation table;
- `INCONCLUSIVE` conditions;
- stop conditions;
- files/logs to preserve.

No hardware experiment is authorized merely because a script exists.

Host builders/auditors can authorize an artifact for consideration, but only the documented project state can authorize a real-device run.

## 6. Causality rules for Phase 6

- Do not patch the last visible log line merely because it is last.
- Do not infer a userspace caller or semantic file use from an NBD physical block read. Read-ahead/page cache make that invalid.
- Do not treat a host TCP timeout after Nexus-side disappearance as proof that transport caused the disappearance.
- Do not treat missing `/proc/last_kmsg` as proof of userspace reboot.
- Do not use a `last_kmsg` capture as evidence for a specific run unless its previous-boot provenance is controlled in that same experiment.
- Do not reintroduce the revoked `/diskless-busybox` / `rdinit=/diskless-init` reset architecture without new evidence requiring it.
- Do not add Android rc bypasses without a captured error proving the subsystem is the blocker.
- Do not revisit power/power-supply diagnosis without new evidence; the prior stable power observations are not an active Phase 6 variable.

## 7. Change discipline

Before editing runtime code:

1. State which accepted fact or current unknown requires the change.
2. Identify whether the change touches a frozen mechanism.
3. Prefer subtraction or a one-variable diagnostic over redesign.
4. Reuse accepted builders/auditors whenever possible.
5. Fail closed when artifact identity or expected source does not match.

After every meaningful accepted, revoked, or diagnostic runtime change:

1. Update `DISKLESS_V2_EXECUTION.md` if architecture, runtime contract, evidence class, or authorized direction changed.
2. Update `diskless-v2/PROGRESS.md` to the new concise checkpoint.
3. Update the active phase evidence document.
4. Append mistakes/regression rules to `PHASE6_FAILURE_LOG.md` when applicable.
5. Record exact hashes/commits for accepted artifacts.

Documentation sync is part of the change, not optional cleanup. Do not proceed to another hardware experiment while the authoritative documents disagree.

## 8. Communication discipline

When reporting status:

- separate observation, source proof, inference, and hypothesis;
- say `UNKNOWN` when unknown;
- do not claim a reboot was "automatic" or "caused by X" unless the evidence establishes that statement;
- do not call a host-only PASS a hardware PASS;
- give exact commands only after the relevant preflight and authorization state are clear.

## 9. Current governance reset

As of the creation of this file, hardware testing is paused while the authoritative documents are reconciled after Phase6 Audit-V2 Run 1.

The recently added `phase6_v2_panic_hold_*` scripts are `PROPOSED_DIAGNOSTIC` artifacts only. Their existence does not authorize a real-device boot. They must be re-reviewed under this protocol before use.
