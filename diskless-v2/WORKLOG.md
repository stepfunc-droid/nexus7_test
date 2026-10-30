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

## Batch 2026-10-29-B — Enforce per-batch checkpointing

**Goal**

Turn the user's requirement "record every completed batch before continuing" into an enforced repository workflow rather than a conversational promise.

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=2a990b6fedfb269657c93e6d709a436ef3180450
checkpoint=governance reset active; hardware PAUSED
```

**Work completed**

1. Added an explicit `Batch checkpoint discipline` section to `AGENTS.md`.
2. Defined what constitutes a batch and what must be recorded before the next batch begins.
3. Required every batch closeout to record start/end identity, evidence class, conclusions, remaining unknowns, mistakes, changed files, next handoff, and hardware authorization.
4. Created this append-only `WORKLOG.md` as the durable chronological handoff ledger.
5. Updated `PROGRESS.md` startup order to require reading the latest worklog entries and made batch checkpointing part of governance state.
6. Explicitly prohibited starting another unrelated diagnostic or hardware experiment before the previous batch has been recorded and committed.

**Evidence produced / class**

```text
AGENTS batch policy        REPOSITORY FACT
WORKLOG ledger             REPOSITORY FACT
PROGRESS linkage           REPOSITORY FACT
runtime behavior           NOT CHANGED
hardware evidence          NONE
```

**Accepted conclusions**

- Diskless-v2 work now proceeds as explicit, closed batches.
- Documentation closeout is part of engineering work, not cleanup after the fact.
- `WORKLOG.md` is chronological only; it cannot override the total design or current checkpoint.
- A batch that changes runtime facts or project direction must also update the authoritative design/checkpoint/failure documents in that same batch.
- This mechanism exists specifically to prevent v2 from repeating v1's accumulation of undocumented assumptions and ad-hoc bypasses.

**Remaining unknowns / hypotheses**

No Phase6 root-cause unknown was resolved in this governance batch. Run1 reset/failure classification remains unchanged.

**Mistakes/revocations**

None newly introduced in this batch. The batch exists to prevent recurrence of the already-recorded governance drift.

**Files/docs/commits changed**

```text
3bba8fc9e0277438af2139a07521d6cbd889ad12  AGENTS.md: mandatory batch checkpoint discipline
7ece51502f2e63b250f6c12bd9f8c21c401caee2  create append-only WORKLOG.md
454518de7a6af1b75ea010d6a254edc1494ea17a  PROGRESS.md: require worklog in startup/checkpoint flow
```

**Next exact question / handoff**

The next batch must not begin with implementation. It begins with a full Phase6 evidence reconciliation under `AGENTS.md` and asks:

```text
What is the single highest-information binary experiment that can classify
Run1's failure/reset path without modifying frozen Phase1–5 mechanisms?
```

No answer is accepted until the evidence/history has been re-read and the experiment's delta, outcomes, INCONCLUSIVE cases, capture plan, and stop rules are documented.

**Hardware authorization state**

```text
PAUSED
```

---

## Batch 2026-10-29-C — Select Phase6 reset-classification experiment

**Goal**

Re-read the complete active Phase6 evidence/failure history under the rebuilt governance rules and select exactly one highest-information binary experiment without modifying frozen Phase1–5 mechanisms.

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=8b123faa06413c0beb1e49ac4080ee220748f7e3
Phase1–5=ACCEPTED/FROZEN
6V2-D=REAL-DEVICE PASS for transport attach
6V2-E=NOT REACHED
Run1 reset/failure cause=UNKNOWN
hardware=PAUSED
```

**Work completed**

1. Re-read `AGENTS.md`, total design, `PROGRESS.md`, latest `WORKLOG.md`, all active Phase6 evidence documents, and all failure records through F6-016.
2. Re-audited the exact pinned Linux 3.4 source for ARM oops/panic behavior, panic timeout behavior, MSM watchdog initialization/notifier behavior, APQ8064 watchdog timing, and Qualcomm restart-reason handling.
3. Verified the diskless kernel configuration is derived from pinned `lineageos_flo_defconfig`, retaining `CONFIG_MSM_WATCHDOG=y` and `CONFIG_MSM_DLOAD_MODE=y` while not enabling `/dev/mem` (`CONFIG_DEVMEM` disabled).
4. Compared three candidate directions: unchanged rerun + recovery `last_kmsg`, Qualcomm IMEM restart-reason readout, and wrapper-only panic-timeout A/B.
5. Selected the panic-timeout A/B because it answers one narrow causal question without changing frozen kernel/transport/Android mechanisms.
6. Wrote `PHASE6_V2_RESET_CLASSIFICATION.md` with the exact question, source proof, frozen inputs, outcomes, INCONCLUSIVE conditions, capture plan, and stop rules.
7. Found that the existing panic-hold helper only proved a sysctl write command was present, not that the runtime kernel value was actually changed; recorded this as F6-017.
8. Updated the total design and current checkpoint to select the experiment while keeping hardware paused.

**Source evidence / class**

```text
ARM die() + panic_on_oops -> panic()                 SOURCE_PROVEN
panic_timeout != 0 -> emergency_restart()            SOURCE_PROVEN
panic_timeout == 0 -> terminal panic loop            SOURCE_PROVEN
MSM panic notifier + timeout==0 -> watchdog disabled SOURCE_PROVEN
APQ8064 watchdog bark_time=45000ms                    SOURCE_PROVEN
Run1 runtime panic sysctl values                      NOT READ BACK / UNKNOWN
```

**Candidate comparison**

```text
unchanged rerun + last_kmsg:
  zero runtime delta, but reboot may allow an intervening kernel before recovery;
  not selected as primary classifier.

Qualcomm IMEM restart reason:
  source offers useful magic values, but accepted userspace has no read path and
  CONFIG_DEVMEM is disabled; exposing it would require a frozen-kernel delta.

panic-timeout A/B:
  wrapper-only diagnostic; no Phase1–5 source change; selected.
```

**Selected binary question**

```text
Did the Run1-like observed reboot depend on Linux panic() panic_timeout auto-restart?
```

Single intended causal variable:

```text
panic_timeout: 5 -> 0
panic_on_oops: remains 1
```

The revised implementation must fail closed before NBD attach unless same-run read-back proves:

```text
/proc/sys/kernel/panic == 0
/proc/sys/kernel/panic_on_oops == 1
```

**Outcome discipline**

```text
comparable boundary + >=90s persistent hold
    -> panic_timeout dependency SUPPORTED

comparable boundary + reboot still occurs
    -> panic_timeout auto-restart INSUFFICIENT to explain reset
       (does NOT prove userspace reboot)

precondition failure / no NBD / non-comparable boundary / incomplete evidence
    -> INCONCLUSIVE
```

**Evidence produced / class**

```text
experiment selection/design       HOST/SOURCE-BASED DESIGN DECISION
pinned panic/watchdog semantics   SOURCE_PROVEN
new runtime behavior              NONE
hardware evidence                 NONE
```

**Mistake/revocation recorded**

`F6-017`: proving that an artifact contains a runtime sysctl write is not proof that the running kernel accepted that value. A causal runtime knob requires same-run read-back or an independent equivalent observation.

**Files/docs/commits changed**

```text
76b69f3fdf8acc44e5af8f58d7ecc2d34d5d8ee6  add reset-classification experiment design
2b35be4ae6249e38d45d6d70bce7b32227daa970  record F6-017 runtime-readback gap
4c81e67a455bcab9316ecd38971e85aaf5727236  select experiment in total design
5b4b0bdeaa7c3cad697f841a8b7847d8eeee25c3  checkpoint selected experiment in PROGRESS
```

**Accepted conclusions**

- The next useful question is about dependence on Linux panic auto-restart, not yet the broader “kernel vs userspace” classification.
- Panic-hold remains a diagnostic proposal, not accepted architecture.
- Existing panic-hold code is insufficient under the new governance rules until runtime read-back is fail-closed.
- No Phase1–5 mechanism needs modification for the selected experiment.
- Hardware remains paused until a separate implementation batch revises and passes the host gates.

**Remaining unknowns**

```text
Run1 entered Linux panic() path          UNKNOWN
Run1 kernel hang/deadlock                UNKNOWN
Run1 watchdog/secure-side reset          UNKNOWN
Run1 userspace/init reboot               UNKNOWN
Run1 other reset path                    UNKNOWN
6V2-E p3/p6 second-stage evidence        NOT REACHED
```

**Next exact question / handoff**

Start a new implementation batch from this batch's closing HEAD and ask:

```text
Can we build a deterministic diagnostic image that changes only panic_timeout 5->0,
proves panic=0 and panic_on_oops=1 by fail-closed same-run read-back before NBD attach,
and otherwise preserves the accepted continuation/Phase1-5 runtime contract?
```

Only after that host implementation/audit passes may the total design consider authorizing one real-device run.

**Hardware authorization state**

```text
PAUSED
```

---

## Batch 2026-10-29-D — Prepare fail-closed panic-timeout host implementation

**Goal**

Implement the selected panic-timeout diagnostic entirely host-side, without authorizing hardware, while preserving Phase1–5 and the accepted continuation outside the explicitly approved precondition block.

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=fff80df12c5071f68043b912e4c1cd69a17dcf41
experiment=panic-timeout reset classification
hardware=PAUSED
```

**Work completed**

1. Added an independent panic-hold wrapper auditor pinned to the accepted continuation wrapper SHA.
2. Revised the diagnostic wrapper construction so `panic_on_oops=1` and `panic=0` are written and read back fail-closed before usb0 wait and before any NBD attach.
3. Required the independent wrapper auditor to prove exact accepted prefix/suffix bytes and only one approved diagnostic block replacement.
4. Kept the accepted Phase5 builder and independent continuation image auditor unchanged and reused them for deterministic A/B builds.
5. Re-audited pinned kernel source for later `panic_timeout` assignments; no target ARM/flo autonomous restore path was identified.
6. Audited Lineage 18.1 root `init.rc` and pinned flox `init.flox.rc`: root init reasserts `panic_on_oops=1`; neither audited file writes panic timeout.
7. Added a read-only accepted-image writer auditor that binds system/vendor SHA identities to the frozen-fact report and conservatively rejects canonical direct panic-timeout writer literals.
8. Fixed the image writer scanner to use read-only `mmap`, eliminating chunk-boundary false classification risk.
9. Tightened `phase6_v2_panic_hold_real_preflight.sh` so it first refreshes the accepted Audit-V2 frozen facts, then requires the new runtime-readback and accepted-image-writer audit report fields.
10. Synced the experiment document, total design, and `PROGRESS.md` to state that implementation is prepared but actual host execution is still pending.

**Evidence produced / class**

```text
wrapper auditor source/identity                 REPOSITORY FACT
fail-closed pre-NBD readback implementation     IMPLEMENTED_UNPROVEN
accepted-image writer scanner implementation    IMPLEMENTED_UNPROVEN
kernel panic/watchdog semantics                 SOURCE_PROVEN
root init.rc panic_on_oops write                SOURCE_PROVEN
pinned flox init.flox.rc no panic timeout write SOURCE_PROVEN
actual accepted-image writer scan result        NOT YET RUN
actual deterministic host gate result           NOT YET RUN
hardware evidence                               NONE
```

**Important claim limit**

The accepted-image scanner can prove that canonical direct writer literals are absent from the accepted system/vendor raw bytes when it passes. It cannot mathematically prove absence of a nonliteral/programmatic sysctl writer. This limitation is encoded in the report and remains part of any future negative-result interpretation.

**Files/docs/commits changed**

```text
bec1266918178f6e7811aa733be8a25579ca9947  add independent panic-hold wrapper auditor
87c89c8aa4cd79d5d89e25b6bfdf328d8aa04a6d  first fail-closed host-gate revision
75568598b6a15e79b96689a3799d09757ab9d62f  first tightened real preflight
868f69e97bcba3e2bf51f7fa6b17309de874e4a4  add accepted-image panic writer auditor
57b295d25977cfbf13bab021d4aee53a4c96773f  make writer scan mmap/boundary-safe
2e3a78a8fbed035d58055dbf02770793be334f59  integrate writer audit into host gate
2061a0c3d469699c129164801f688a745879bc7f  require writer audit in real preflight
2bb2241578bb2945b58001ec0072c0c2eab9b756  record prepared implementation in experiment design
9f54bc9e06c2e5d1f25584a51955628c5250d826  sync total design to prepared-host state
f13691bd796807ace1ba0ad8f50988c738b33dbb  sync current checkpoint
```

**Accepted conclusions**

- The selected diagnostic can be implemented without changing frozen kernel/transport/Android filesystem bytes.
- A later NBD connection in the diagnostic run can only occur after the wrapper's fail-closed `panic=0` / `panic_on_oops=1` read-back passed.
- The implementation itself is not a HOST PASS until executed against the user's actual accepted artifacts.
- No real-device command is authorized at this batch close.

**Remaining unknowns**

```text
host gate on actual accepted artifacts        PENDING
accepted-image direct writer result           PENDING
Run1 panic-timeout dependency                  UNKNOWN
Run1 panic/oops path                           UNKNOWN
Run1 hang/watchdog/userspace/other reset       UNKNOWN
6V2-E p3/p6 second-stage evidence              NOT REACHED
```

**Next exact question / handoff**

Host-only execution on the user's Mac:

```text
Does phase6_v2_panic_hold_real_preflight.sh pass against the exact accepted
artifacts, including frozen-fact identities, accepted-image writer scan,
exact wrapper delta, reproducible build, and independent final-image audit?
```

The output must be persisted and reviewed before changing hardware authorization.

**Hardware authorization state**

```text
PAUSED
real-device run=NOT AUTHORIZED
```

---

## Batch 2026-10-30-A — Takeover audit and authoritative-document reconciliation

**Goal / exact question**

Establish a reviewable handoff: do the active documents, preflight implementation and locally available artifacts agree on the current checkpoint and the next authorized action? This batch is host-only review/documentation reconciliation, not a runtime implementation batch.

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=cc649ef92886ff2854128c936c58fddfa98f92ee
authority=AGENTS.md + DISKLESS_V2_EXECUTION.md + PROGRESS.md
Phase1-5=ACCEPTED/FROZEN
6V2-D=REAL_DEVICE_FACT / transport attach PASS
6V2-E=NOT REACHED
Run1 reset/failure cause=UNKNOWN
hardware=PAUSED / new real-device run NOT AUTHORIZED
```

**Work completed**

1. Completed mandatory startup reads, all active evidence/failure records through F6-017, and recent commit reconciliation. The only commit after the latest meaningful PROGRESS update closes the previous implementation batch; the instruction to close that batch was stale.
2. Inspected the actual real-preflight call chain and recorded F6-018: it does not execute the frozen-fact gate despite the prior documentation claim. Stopped short of full-preflight execution or host/runtime script edits; synchronized the next handoff to repair/revalidation.
3. Found an existing untracked panic-hold PASS report and diagnostic image with original-host paths. Recorded their identities without accepting unverified execution provenance or inferring a hardware run.
4. Extracted `/init` from the local diagnostic image into a temporary directory and ran the existing independent wrapper auditor, then audited both local images against accepted boot/kernel/BusyBox/fstab/init inputs. All three checks returned exit 0; no full rebuild or writer scan was rerun.
5. Reconciled stale phase text: revoked p5-to-late-fs inference, initial still-open Run1 observation, initial missing-summary limitation, and unsupported automatic-reboot wording. Clarified the optional last_kmsg copy/app availability checks retained in the exact accepted wrapper; preserved all runtime bytes.
6. Added a historical-scope banner to README so its mainline prototype commands do not appear to be the active LineageOS v2 handoff.
7. Located system/disk path candidates on `/Volumes/zhangjw/`; did not equate path presence with accepted byte identity. Existing reports name `/Users/zhangjw/`, while current default paths differ.

**Evidence produced / class**

```text
local baseline-image audit                         HOST_FACT / PASS
local diagnostic-image audit                       HOST_FACT / PASS
exact diagnostic wrapper delta/order audit         HOST_FACT / PASS
missing frozen-fact-gate invocation                HOST_FACT / static local call-chain audit
old report's full execution provenance             UNKNOWN
current-input writer scan / deterministic rebuild  NOT RERUN
new real-device evidence                           NONE
diagnostic device execution since old checkpoint   UNKNOWN
```

**End artifact identity**

```text
evidence=diskless-v2/audits/2026-10-30-takeover.txt
evidence_sha256=a796a39f0a4ece103723c2ad3eaf4c082924e22b67dae8270a6b4124222689dc
baseline_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
diagnostic_image_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
diagnostic_wrapper_sha256=839ec782f5db944e3941ca7555b64528085cb1890109bd0fe4caae4a6257181a
closing_commit=the documentation commit containing this batch entry
```

**Accepted conclusions / remaining unknowns**

The local images satisfy the independently rerun artifact audits. This neither accepts the complete imported PASS report nor establishes device panic/read-back behavior. Phase1–5 remain accepted/frozen; Run1 cause remains UNKNOWN. The selected panic-timeout experiment remains a PROPOSED_DIAGNOSTIC. No runtime redesign is justified by this audit.

**Mistakes/revocations**

F6-018 revokes the claim that the current preflight refreshes frozen facts. Earlier stale phase wording is reconciled with existing accepted F6-013 through F6-016 rules; the append-only previous worklog entries remain historical.

**Files/docs changed**

```text
README.md
DISKLESS_V2_EXECUTION.md
diskless-v2/PROGRESS.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_V2_REAL_DEVICE.md
diskless-v2/PHASE6_V2_RUN1_POSTMORTEM.md
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/audits/2026-10-30-takeover.txt
diskless-v2/WORKLOG.md
```

**Validation**

The three existing host audit invocations and exact identities are persisted in the evidence file. Documentation diff reviewed; `git diff --check` passed. No host/runtime scripts or image bytes changed. Pre-existing untracked images, output directories and Python cache were retained.

**Next exact question / handoff**

Can the host-only preflight chain be repaired and verified to actually re-execute frozen-fact validation against explicitly resolved current input paths before consuming its report, while preserving frozen Phase1–5 runtime bytes? Then rerun complete host validation, preserve both output streams and exit status, and review results before any hardware authorization decision.

**Hardware authorization state**

```text
hardware=PAUSED
new real-device run=NOT AUTHORIZED
hardware commands issued in this batch=NONE
```

---

## Batch 2026-10-30-B — Establish remote Mac execution and SCP workflow

**Goal / exact question**

Can the coordinator reach the user-designated Mac, identify the repository/input paths and Nexus bootloader without changing device state, and verify the requested SCP handoff workflow?

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=2c9333add5453be9101952de116d5a7d86c8fc24
authority=AGENTS.md + DISKLESS_V2_EXECUTION.md + PROGRESS.md
F6-018=host-only repair/revalidation pending
Phase1-5=ACCEPTED/FROZEN
Run1 cause=UNKNOWN
hardware experiments=PAUSED
user authorization=SSH inspection, read-only bootloader queries, SCP changes,
                   Mac builds/host operations on zhangjw@192.168.1.63;
                   notify user when Debian compilation is needed
```

**Work completed**

1. Reconfirmed the local branch/HEAD and authoritative checkpoint. Connected via noninteractive SSH to `zhangjw@192.168.1.63` and inspected its login-shell tool paths, repository and inputs.
2. Remote Mac is x86_64 macOS 13.7.8; repository `/Users/zhangjw/nexus7_test` reported the same branch/HEAD as the coordinator and no tracked modifications before this batch's edits. System, original vendor, partitioned disk and manifest exist at the remote default paths. Presence checks do not constitute full input identity validation.
3. Verified the coordinator volume is an SMB mount of the Mac mini user directory; the two repository paths are a shared working tree. This explains matching commits/files and resolves the prior uncertainty about relocated inputs. Full Mac builds and host validation must execute remotely, not through coordinator paths.
4. On the remote Mac, ran read-only `fastboot devices -l` and serial-scoped product/bootloader queries with subprocess timeouts. Device `07a117ae` responded as `flo`, bootloader `FLO-04.08`. Issued no boot, flash, reboot, erase or NBD-service command.
5. Added the user-directed execution/transfer convention to AGENTS.md, total design and checkpoint; recorded the detailed host map in REMOTE_WORKFLOW.md. No runtime/host-gate code changed.
6. Used SCP to send REMOTE_WORKFLOW.md and the inspection transcript to an independent remote temporary directory. Both destination SHA256 values and byte comparisons against the remote working tree matched. No shared source or image was overwritten by SCP.

**Evidence / end artifact identities**

```text
SSH, remote environment/repository/path inspection     HOST_FACT
same relevant remote/local scripts/images hashes       HOST_FACT
SCP transfer + destination SHA256 + cmp                HOST_FACT
bootloader enumeration/product/version response        REAL_DEVICE_FACT at query time
full current-input hash/preflight validation            NOT RUN
diagnostic Android execution or reset cause             UNKNOWN

host_map=diskless-v2/REMOTE_WORKFLOW.md
host_map_sha256=6bce619a7dbe847b92c9111d0aed11775e632df9f8496715e69b160891853e5f
transcript=diskless-v2/audits/2026-10-30-remote-inspection.jsonl
transcript_sha256=a8cac953bfd3dab2174714c40da90b92d81400b0297fe454bc927379903bdae0
scp_destination=/tmp/nexus7-v2-handoff.5ONFnf/
closing_commit=the documentation commit containing this batch entry
```

**Accepted conclusions / remaining unknowns**

SSH and SCP are operational. The Mac is the designated build/validation/device host; current coordinator source edits are visible through SMB. Existing accepted continuation/diagnostic image hashes match remotely. No compilation occurred, and a full cross-compilation toolchain was not audited. No Debian host is designated. Phase1–5 acceptance, F6-018 and Run1's UNKNOWN cause are unchanged.

**Mistakes/revocations**

No new runtime mistake or causal inference. The earlier path-relocation concern is resolved operationally: use `/Users/zhangjw/` when running on the remote Mac. Full input verification is still required.

**Files/docs changed**

```text
AGENTS.md
DISKLESS_V2_EXECUTION.md
diskless-v2/PROGRESS.md
diskless-v2/REMOTE_WORKFLOW.md
diskless-v2/audits/2026-10-30-remote-inspection.jsonl
diskless-v2/WORKLOG.md
```

**Validation / next exact question**

SSH calls, SCP and remote hash/byte comparisons exited 0. Documentation diff reviewed; `git diff --check` passed. Remote commit `29d78b4150a6382ec7d5a7a435e588b390294f2a` recorded the initial handoff. The subsequent coordinator-side Git check through SMB showed inconsistent index state and then an index-read error; direct remote Git remained healthy with only original untracked outputs. Recorded this access-path discrepancy as F6-019 and moved all Git operations to SSH without resetting or rewriting the index. Underlying filesystem/cache mechanism is UNKNOWN. The SCP hashes above identify the initial transferred host-map snapshot; the committed host map additionally records F6-019.

Additional files changed for that correction: `diskless-v2/PHASE6_FAILURE_LOG.md` plus the host-routing documents already listed. Closing identity is the final documentation commit containing this correction.

Next batch: repair/verify the F6-018 host chain and run complete current-input validation through SSH on the Mac, preserving output and exact identities, before considering a controlled diagnostic boot.

**Hardware authorization state**

```text
read-only remote bootloader inspection=USER AUTHORIZED / COMPLETED
new boot/flash/reboot/erase commands issued=NONE
hardware experiments=PAUSED / new diagnostic boot NOT AUTHORIZED
```

---

## Batch 2026-10-30-C — Repair F6-018 and execute complete Mac host validation

**Goal / exact question**

Does the panic-hold preflight actually re-execute current-input frozen-fact validation before consuming reports, stop on failure despite stale PASS artifacts, and pass complete host validation against accepted inputs on the designated Mac?

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=cf46bb5802d35838b15c7063b5168dcb02fd5a16
execution_host=zhangjw@192.168.1.63
authority=AGENTS.md + DISKLESS_V2_EXECUTION.md + PROGRESS.md
Phase1-5=ACCEPTED/FROZEN
F6-018=REPAIR / CURRENT-INPUT VALIDATION PENDING
Run1 cause=UNKNOWN
hardware=PAUSED
```

**Work completed**

1. Completed startup review and inspected the complete relevant preflight/gate chain. No runtime change was justified or made.
2. Repaired the panic-hold real preflight to execute the existing frozen-fact gate first and require its fresh PASS marker. Bound disk/manifest arguments across gates, scoped fact/diagnostic reports separately, and kept continuation/diagnostic image overrides distinct.
3. Added an isolated orchestration self-test covering a stale PASS report with failing frozen validation, missing fresh PASS marker, base-preflight failure, and successful execution in frozen/base/host order with custom input/output paths.
4. Ran syntax/self-tests on the remote Mac. Ran a real-validator negative case with a missing stock boot and a pre-existing fact PASS report; it exited 1 without producing a diagnostic image or final PASS.
5. Sent both changed host scripts by SCP to `/tmp/nexus7-v2-f6018.d13cyJ/` and verified SHA256 and byte identity before complete real-input execution.
6. Executed current-input frozen facts, continuation A/B builds/audit, tracer protocol differential/semantic gates and the repaired complete panic-hold preflight on the Mac. Used separate output/report paths under `out/phase6-v2-host-20261030-C`, preserving existing images/reports. Every real gate exited 0. The complete preflight itself reran frozen facts before rebuilding/auditing the diagnostic.
7. Reviewed actual output, confirmed both rebuilt image hashes match prior accepted/diagnostic identities, and committed raw combined stdout/stderr, report identities and exit statuses under `audits/2026-10-30-f6018-host/`.
8. Updated design/checkpoint/phase evidence/failure resolution. Final read-only enumeration still showed Nexus `07a117ae` in fastboot. No boot, reboot, flash, erase or device-facing NBD service was started. No Debian build was needed.

**Evidence / accepted conclusions**

```text
isolated host orchestration self-test                 HOST_FACT / PASS (4 cases)
real frozen-gate stale-report rejection               HOST_FACT / PASS (expected exit 1)
current accepted-input frozen fact gate               HOST_FACT / PASS
continuation reproducible A/B builds + image audit    HOST_FACT / PASS
tracer protocol differential + semantic self-tests    HOST_FACT / PASS
accepted-image direct writer scan                    HOST_FACT / PASS
diagnostic reproducible A/B builds + audits           HOST_FACT / PASS
complete repaired panic-hold preflight                HOST_FACT / PASS
F6-018 implementation/host-verification gap            CLOSED
new diagnostic runtime / reset-cause evidence         NONE
```

The image-writer scan found one allowed panic_on_oops literal and zero canonical direct panic-timeout literals; it still does not prove absence of a nonliteral/programmatic sysctl writer. Host PASS does not demonstrate real-device read-back or authorize hardware.

**End artifact identity**

```text
summary=diskless-v2/audits/2026-10-30-f6018-host/SUMMARY.txt
summary_sha256=b2c01313a588694730fec5e3ec5d28508e0da544cc0e02f9220e52cb43d5b8c3
preflight_source_sha256=6fdecf83d686b091f03bce35d9fa68e0f76550d0800959ad314b9bb4c594e11c
selftest_source_sha256=dd2300b3ac7b445e2648f4204e8675d2b8aeb1226ffa83bcaa51cbddc1bc27fc
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
diagnostic_image_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
closing_commit=the code/documentation commit containing this batch entry
```

**Remaining unknowns / mistakes / revocations**

Run1 panic, hang, watchdog, userspace and other reset paths remain UNKNOWN; 6V2-E remains NOT REACHED. F6-018's old claim remains revoked in history; the current implementation is now independently exercised. F6-019 remote-Git routing was followed. No frozen runtime mechanism changed and no new runtime conclusion was accepted.

**Files/docs changed**

```text
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
scripts/v2/selftest_phase6_v2_panic_preflight.py
DISKLESS_V2_EXECUTION.md
diskless-v2/PROGRESS.md
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/REMOTE_WORKFLOW.md
diskless-v2/audits/2026-10-30-f6018-host/ (raw host evidence and SUMMARY)
diskless-v2/WORKLOG.md
```

**Next exact question / handoff**

Prepare and review the selected panic-timeout experiment's run-specific boot/capture/stop procedure: can it preserve the exact NBD failure boundary and distinguish an observed reboot from a >=90s persistent hold with the proven diagnostic image and frozen inputs? Missing observation must yield INCONCLUSIVE. Record any authorization in the authoritative documents before one controlled boot; rerun repaired preflight immediately before authorized use.

**Hardware authorization state**

```text
full host validation=PASS
real-device diagnostic run=NOT AUTHORIZED
hardware experiments=PAUSED
device-state-changing commands issued=NONE
```

---

## Batch 2026-10-30-D — Prepare observations and conditional Run P1 authorization

**Goal / exact question**

Can a concrete host-only capture procedure preserve the NBD failure boundary and distinguish reboot/reenumeration from a >=90s hold, while reusing the frozen diagnostic and unchanged accepted NBD protocol?

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=f585b41dc01eb8624cf4311476d21bd31a8c36c0
authority=AGENTS.md + total design + PROGRESS.md
complete host preflight=PASS / HOST_FACT (C)
Run1 cause=UNKNOWN
hardware=PAUSED
user instruction=continue controlled diagnostic preparation/execution
physical observer=user confirmed available
```

**Work completed**

1. Completed startup review and examined the original server's request/reply and failure-summary paths. Original logs alone do not periodically preserve ordinary p1 progress on an indefinitely idle connection.
2. Added a separate observed-server entrypoint that verifies the original V2 server's exact Git blob and delegates its protocol unchanged. It records completed reply identity/bytes and accepts SIGUSR1 snapshots without disconnecting or adding timeouts. The frozen original server and all Nexus runtime files remain unchanged.
3. Added a read-only macOS USB observer preserving target-port registry identity, VID/PID, UTC/monotonic timestamps and observation errors. Fixed the initial dict/list-root assumption before any hardware action; recorded F6-020.
4. Added/executed protocol/final-disk differential tests against the accepted server in RW and RO modes, an idle snapshot/continued-request test, and USB schema traversal tests. A real 2s USB dry run succeeded. All are HOST_FACT, not diagnostic hardware results.
5. Confirmed existing stock fastboot target and bound the existing lk2nd image SHA. This records the existing artifact, not a new bootstrap source build.
6. Identified DHCP-only saved USB services. The dedicated RNDIS/Ethernet Gadget service was successfully configured without sudo to the accepted `172.16.42.2/24` endpoint, router `0.0.0.0`, and read back. Management interfaces were not changed. Noninteractive sudo and BPF access are unavailable, so packet capture is not a run dependency.
7. Sent the three new host scripts via SCP to the independent source-snapshot directory and verified destination bytes. Hashed the complete accepted disk before any export.
8. Prepared/reviewed the run-specific P1 plan: exact question/delta/inputs, explicit 16MiB p1 comparability threshold, physical/USB hold criteria, command capture, bootstrap and attach limits, INCONCLUSIVE/stop rules and preserved evidence. Synchronized conditional single-run authorization in total design/checkpoint/phase evidence. No diagnostic boot occurred in this batch.

**Evidence / end artifact identity**

```text
observer source/protocol/idle self-tests             HOST_FACT / PASS
USB read-only dry run                              HOST_FACT / PASS
saved dedicated host endpoint read-back             HOST_FACT
full frozen disk SHA256                             HOST_FACT
physical observation availability                   user-provided precondition
new diagnostic runtime evidence                     NONE
evidence=diskless-v2/audits/2026-10-30-observation-host/
plan=diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P1.md
observed_server_sha256=07109f683e954075aead0d0f253a30d77b81cad6e06bc95c176a2278df91729c
USB_observer_sha256=1aca1eb7c160c3cc3e7ce3ec13af35f52fa13a5e2a53e19bab0becfc48bf1bf3
observer_selftest_sha256=9e5dab0a6f865bd8806208fb637d2c347ed9f05b01de02ab923454ee85594d17
full_disk_sha256=c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9
bootstrap_sha256=a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a
closing_commit=the preparation/authorization commit containing this entry
```

**Accepted conclusions / remaining unknowns / mistakes**

Host observations can be collected without privileged packet capture or Nexus-side instrumentation. Explicit completed replies remove dependence on an exception-time summary for p1 progress. Generic sampled phase/counters can be interrupted during an update and are not independently treated as completed I/O. USB absence alone remains insufficient to classify a reset or positive hold. The causal experiment remains PROPOSED_DIAGNOSTIC and Run1 cause remains UNKNOWN. F6-020 records the pre-boot observer schema error. No Phase1–5 runtime mechanism changed.

**Files/docs changed**

```text
scripts/v2/phase6_v2_nbd_observed_server.py
scripts/v2/phase6_v2_observe_usb.py
scripts/v2/selftest_phase6_v2_observation.py
diskless-v2/PHASE6_V2_PANIC_HOLD_RUN_P1.md
DISKLESS_V2_EXECUTION.md
diskless-v2/PROGRESS.md
diskless-v2/PHASE6_V2_RESET_CLASSIFICATION.md
diskless-v2/PHASE6_AUDIT_V2.md
diskless-v2/PHASE6_FAILURE_LOG.md
diskless-v2/REMOTE_WORKFLOW.md
diskless-v2/audits/2026-10-30-observation-host/
diskless-v2/WORKLOG.md
```

**Next exact question / hardware authorization**

After this preparation is committed, execute batch E / P1 only if fresh repaired preflight, source/artifact/full-disk identity checks, endpoint and observer readiness all pass. Then ask the selected binary reset-dependency question with one diagnostic RAM boot via the existing RAM-only lk2nd bootstrap. No flash, erase, automatic retry or recovery boot is authorized. Consume the exception after one attempt and restore hardware pause until its result is documented/committed.

---

## Batch 2026-10-30-E — P1 pre-boot decision record (batch still active)

Starting HEAD: `275c40d81eafaa74b28b90dc9626e912003ac2e0`; question and inputs are the committed P1 plan. Fresh repaired preflight passed, diagnostic identity matched, and full disk SHA matched preparation D (`HOST_FACT`). Before any device boot or export, automatic review rejected the wildcard RW listener-start action due to broader reachable-client exposure. The tool action did not execute.

F6-021 records the issue and safer revision: USB observation starts first, then a deferred launcher binds NBD only to `172.16.42.2` after that dedicated endpoint appears, retaining accepted client retries. No kernel, init, server-protocol or observer code changed. The user was informed of the automatic rejection and destination restriction. The source/plan revision is committed before attempting the narrower action. No device transition or diagnostic attempt has yet occurred; P1's single-use authorization remains conditional and unconsumed. Final experiment evidence, outcome, process state and batch close will be appended before another experiment.

---

### Batch E close — P1 did not execute the reset diagnostic

Fresh preflight/full disk check passed. The narrower host launcher and USB observer were armed; no NBD listener was started. One bootstrap RAM boot completed successfully. The initial helper's lk2nd guard timed out because it expected a nonempty version string; the actual read-back is `product: lk2nd-msm8960`, empty version, same `07a117ae` serial/physical port and new PID `0xd00d` (REAL_DEVICE_FACT). Diagnostic boot count stayed zero. F6-022 records the host predicate error; this is not evidence of a Nexus kernel failure.

Result: `NOT_EXECUTED / INCONCLUSIVE` for the reset-dependency question. User-visible bootstrap transition occurred, but no diagnostic kernel, NBD connection or export ran. The deferred launcher timed out without exporting; only this run's USB observer was stopped. Device remains in verified lk2nd. P1 authorization is consumed and hardware pause restored.

Evidence/end artifact: `diskless-v2/audits/2026-10-30-P1-preboot/`, including raw fresh preflight, full disk SHA, bootstrap transcript, all identity probes, final direct identity read-back, USB timeline, command journal, result and the exact deferred-launcher source. Frozen image/input identities remain unchanged. Starting HEAD `275c40d81eafaa74b28b90dc9626e912003ac2e0`; intermediate safer-plan commit `2d3333fe1b07e5da82ae6337158fdb866f2dd402`; closing identity is the documentation/evidence commit containing this close.

Documents changed: total design, PROGRESS, reset-classification and P1 phase documents, Audit-V2 status, append-only failure record, WORKLOG and P1 evidence directory. No frozen runtime, server-protocol or observer code changed. `git diff --check` is required before this close is committed.

Next exact question: can the same diagnostic be booted exactly once from the already-loaded, reverified lk2nd, using actual product/serial/physical USB identity and the same frozen inputs/observation criteria? Prepare and commit a separate run authorization before doing so; do not repeat the bootstrap merely to satisfy the mistaken predicate. No reset-cause inference is accepted.

---

## Batch 2026-10-30-F — P2 from verified lk2nd (active run authorization)

Starting HEAD `a8da61a3bc3b764c410ba3cdecb9cee178b5f455`; prior E is closed/committed. Goal: execute the unchanged panic-timeout diagnostic once from current verified lk2nd and classify the same binary reset-dependency question. No bootstrap repeat or artifact/runtime delta is proposed. The actual product/serial/USB identity replaces the mistaken version-field predicate; version remains observational.

P2 plan/conditional authorization is recorded in `PHASE6_V2_PANIC_HOLD_RUN_P2.md` and synchronized in total design/PROGRESS/reset/Audit-V2 documents. Fresh preflight/full disk checks are being recorded under `out/phase6-v2-panic-hold-P2/`. Only after committed authorization, passing exact gates and observer readiness may one diagnostic RAM boot run. Export remains restricted to `172.16.42.2`; no flash/erase/retry/recovery boot is allowed. Complete result/evidence/process-state close will be appended before another experiment.

---

### Batch F close — P2 prespecified hold outcome met; root cause remains UNKNOWN

Starting HEAD `a8da61a3bc3b764c410ba3cdecb9cee178b5f455`; authorization committed as `0868ba5fc1c1a1baad088ade886cda7758f728dc`. Fresh complete preflight, full disk SHA and actual lk2nd product/serial/USB checks passed. One exact diagnostic RAM boot completed successfully at 03:54:43.602615 UTC; no second bootstrap, flash, erase or retry. Deferred export started only on `172.16.42.2:10810` once the same physical Linux gadget and en7 endpoint appeared.

REAL_DEVICE_FACT: exactly one NBD connection, 1688 completed READ replies, 71,657,472 total reply bytes, 53,687,296 p1 bytes, zero writes; final completed READ offset 164990976 length 49152. Earlier idle periods ended in further requests and were excluded as terminal boundaries. The final reply then remained unchanged for 495.464s of snapshots, overlapping >=455.260s of continuous same USB registry identity with no observation errors or reenumeration. HOST_FACT: arithmetic/trace classifier meets the predeclared hold threshold. Result `panic_timeout_dependency=SUPPORTED`, with kernel panic, stack/call-site and exclusive root cause still UNKNOWN. Late nonliteral sysctl writers remain unproven absent.

The user reported Lineage boot animation and confirmed an earlier genuine self-reboot; historical run-specific sysctl/provenance limits remain. The user requested no ongoing manual screen observation; automated USB/NBD recording was used. The p3/p6 filesystem gate is NOT_REACHED as evidence, not proof that Android never executed second stage. Full Android boot remains NOT_PROVEN. Host TCP/5555 and ICMP probes timed out; cached ARP entry existed. These are preserved observations without causal attribution.

Evidence/end identity: `diskless-v2/audits/2026-10-30-P2/`, including raw combined command/server output, exact launcher source/commands, all USB/statistics/partition JSONL, user notes, endpoint/probe results, preflight/reports, `result.json` and `SHA256.json`. Diagnostic SHA remains `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`; full pre-run disk SHA remains `c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9`. Closing identity is the evidence/documentation commit containing this entry.

No frozen runtime/protocol code changed. Dedicated observer and statistics sampler ended or were stopped; live USB-only root-storage server PID 92856 remains running. No reset or recovery transition followed the diagnostic. P2 authorization is consumed and hardware pause restored. Next exact question: can a controlled first-successor recovery kernel expose P2's persistent console with no intervening Linux boot? Complete host preparation and explicit provenance/transition authorization before any physical reset or recovery RAM boot. If unavailable, keep UNKNOWN and audit actual init/fstab namespace before designing a validated observation channel. Documents changed: total design, PROGRESS, P2/reset/Audit-V2 phase documents, WORKLOG and P2 evidence directory. Diff checking excludes only raw `endpoint-live.txt`, whose two trailing spaces came directly from ifconfig and are preserved byte-for-byte; the evidence SHA manifest is independently verified. All documentation/code receives the normal diff check.

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
