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

## Batch 2026-10-30-G — Late-transition correction and previous NBD console capture

Starting HEAD `9369be99ef49df85eb5f7c8b783e5a62c94a1e5c`. Initial question was preparing attributable P2 console recovery. Existing recovery host preflight passed, but no recovery/reset command was executed. During preparation the user reported normal startup/ADB, then clarified the actual sequence: failed RAM image, long delay, automatic return to eMMC; subsequent eMMC instability/repeated starts were also reported.

ADB immediately proved the new runtime uses eMMC and has no nbd0 pid. The initial finite-window panic-timeout support was withdrawn, with F6-023 recording the premature causal acceptance. Old P2 raw observations are retained; corrected status is automatic transition with specific reset cause UNKNOWN and panic timeout alone insufficient subject to unknown late writers. Current eMMC logcat/boot-animation/ADB must not be treated as diskless success or P2 failure logs.

Direct last_kmsg was initially permission denied; adbd root was disabled by system setting. No setting bypass was attempted. Supported bugreport export succeeded, but cached recovery files were October 27 and lacked diskless/NBD markers; none was attributed to P2. Full bugreport/current logcat remain in remote out with committed hashes rather than being promoted as P2 evidence. The user subsequently enabled rooted debugging; `adb root` restarted adbd only. Boot ID remained b124ede8-c0bb-490a-8697-211f41b4bb73 across recorded checks, uptime increased, and sys.boot_completed became 1 on eMMC. This does not establish the kernel-vs-framework count of all reported starts outside those checks.

Root capture saved 225,756 bytes from current /proc/last_kmsg, SHA256 c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497. REAL_DEVICE_FACT: it describes a prior NBD-backed boot with second-stage mount_all ./fstab.flox skipping eMMC cache/persist/userdata paths, read-only data errors, NBD receive -110/socket shutdown at 1177s, and explicit init boringssl-self-check-failed reboot at 1180s. Do not patch that final self-test failure as though it were the first cause. Exact P2 attribution is corroborated but not independently unique: ring head/cmdline lost and intervening starts uncontrolled. No stale/unknown-provenance console is silently accepted as a named-run fact.

Evidence: `audits/2026-10-30-P2-late-transition/` and `audits/2026-10-30-previous-NBD-console/` with raw console/identity, provenance report and SHA manifests. Recovery-image preflight is HOST_FACT only; no recovery boot occurred. Inactive USB-only P2 server PID 92856 was stopped after confirming current eMMC/no active root session. No kernel/Android/fstab/runtime file changed; no extra bootstrap/reset/flash was issued. User-enabled root debugging was used as authorized, not changed by the agent.

Architecture/checkpoint/evidence/failure documents are synchronized: early hold support REVOKED; first-stage fstab acceptance remains frozen and does not establish post-SwitchRoot namespace (F6-024). Current direction is one host-only binary audit: does exact accepted system expose an unpatched root fstab.flox while boot/vendor copies are patched? Establish actual path/content/caller and image SHA before designing a minimal Phase6 correction. This is the next batch; no hardware authorization exists. Closing identity is the documentation/evidence commit containing this entry. Raw captured outputs retain original whitespace/bytes; normal diff checks apply to docs/code, evidence hashes validate raw files.

---

## Batch 2026-10-30-H — Exact system-root fstab namespace audit

Starting HEAD `69b35b4c4f3a28cf1af4e17db81a0a5f3d51eae4`; prior G closed/committed. Binary question: is the exact accepted system root fstab still stock eMMC despite patched boot/vendor copies? Answer YES, HOST_FACT. On the Mac, verified system SHA a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880 and resolved actual ext4 entries with the accepted read-only helper. Root /fstab.flox is regular inode 26, 4295 bytes, exact stock SHA ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764, not a symlink. Exact /init.flox.rc invokes mount_all ./fstab.flox --early/--late. Vendor /etc/fstab.flox independently contains the generated NBD mapping.

Accepted conclusion: a concrete second-stage namespace mismatch exists. It is consistent with the captured prior-NBD console's eMMC mount skips; that console's named-run provenance limits stay unchanged. Phase5 first-stage gate is still accepted and does not prove the later file lookup. No artifact was modified, no device command was executed in H, and no transport/kernel/rc redesign is justified. Later NBD timeout cause remains UNKNOWN.

Evidence/end artifacts: `audits/2026-10-30-fstab-namespace/` with report/source SHA and exact extracted root fstab/init rc/vendor fstab. New phase document `PHASE6_SECOND_STAGE_FSTAB.md`, total design, PROGRESS and this ledger record the finding and next host-only direction. Source image/golden disk identities are unchanged; closing identity is this documentation/evidence commit.

Next exact question: can a deterministic separate system/disk derivative change only root-fstab file data to the exact accepted NBD mapping, with independent outside-byte/metadata/geometry/source audits and unchanged P2 boot/runtime mechanisms? This is a PROPOSED_DIAGNOSTIC implementation batch, not hardware authorization. Prepare automatic whole-session/first-successor log capture before any later controlled run. Hardware PAUSED. Doc/code diff checks exclude raw extracted evidence only; hashes retain exact source bytes.

---

## Batch 2026-10-30-I — Root-fstab derivative implementation and independent audit

Starting branch/HEAD: diskless-v2 / `3be1c91e760222bf4a75cc6a845ce677d73dea5c`; checkpoint H namespace mismatch, hardware PAUSED. Binary host question: can a deterministic separate derivative contain precisely the root-fstab data replacement and no other image changes? Answer YES, HOST_FACT.

Added pinned-source builder reusing the unchanged accepted vendor byte-replacement tool twice on the independently resolved system file. Historical vendor marker is not reused as a system gate. Two system outputs match SHA d004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795; repeat deleted after matching. Copied golden disk, replaced only corresponding p1 file-data span. Derived disk SHA 060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a; manifest SHA e307d3285e61fc0a4419bdb6a89d672a45792ab65da39bfdddfaa61bed33b3a3.

Independent read-only auditor resolves regular inode26, exact ranges/content/padding, checks calculated layout against pinned manifest, streams all source/candidate bytes and hashes both p1 regions. Only 2566 bytes change within the4295-byte file data, system offset2125824/disk3174400. All other bytes unchanged implies metadata/xattrs/geometry/rc/other partitions unchanged; p1 hashes match source/derived systems. Golden source system/disk hashes still match original pins. Negative tests reject corruption inside/outside replacements and across chunks, wrong length, alias, overlap and out-of-range changes. Complete actual Mac build/audit exit0. Local edits were independently SCP-snapshotted to /tmp and compared at destination before execution.

Evidence/end artifacts: out/phase6-v2-root-fstab-I and committed audits/2026-10-30-root-fstab-derivative (raw build output, independent audit, determinism, manifest, script hashes). Runtime class remains IMPLEMENTED_UNPROVEN / PROPOSED_DIAGNOSTIC. No accepted first-stage/kernel/transport/handoff mechanism changed and no device command ran. No new mistake/revocation was found; F6-024's namespace lesson already covers this correction.

Files: two new host scripts plus negative self-test, total design, PROGRESS, active second-stage-fstab phase document, this ledger, evidence directory. Closing identity is the commit containing this close. Next exact question: can automatic whole-session/first-successor capture reliably preserve identity-qualified evidence without manual screen observation, before separately considering one controlled run of this derivative? Preserve old frozen-source gates, add explicit derivative validation; do not silently accept the derivative as golden. Hardware PAUSED, existing P1/P2 permissions consumed. Mount_all success, full diskless boot and the later NBD-timeout cause remain UNKNOWN.

---

## Batch 2026-10-30-J — Automatic console-first ADB observation preparation

Starting branch/HEAD/checkpoint: diskless-v2 / e814fc55122ba8712ba4390e705eb2350e4d28d4, derivative I HOST_PASS but runtime unproven/hardware paused. Question: can automatic host capture save the previous console before slower diagnostics while checking boot identity and retaining first-successor attribution limits? Host implementation/test answer YES; real-reset capture remains IMPLEMENTED_UNPROVEN.

Added phase6_v2_watch_adb_console.py and selftest_phase6_v2_adb_console.py. Collector requires already-root valid baseline, saves last_kmsg first, checks same serial/boot ID/root before/after, preserves binary stdout/stderr/status/hashes, deduplicates stable captures per boot, bounds retries and heartbeats, supports explicitly enabled adb root on a new return. It neither reboots nor changes device files/settings. First-visible ADB is always UNKNOWN as first-successor identity pending independent full-sequence review. No idle-window or restored-ADB success inference exists.

HOST_FACT: three actual Mac tests pass, including real CLI with fake ADB baseline/offline/new nonroot boot/root restart/stable capture, exact binary saving, identity-change flag and invalid probes. REAL_DEVICE_FACT: baseline-only read on current eMMC boot b124ede8-c0bb-490a-8697-211f41b4bb73, UID0, uptime13303.68->13304.62, stable throughout; last_kmsg225756 bytes SHA c494dc5eee957d1c85f5327ec44222e270e5875e253a71ca40a0ad03ab760497 exactly matches existing archived previous NBD console. No new attribution, reset or root restart occurred on hardware.

Evidence/end artifact: out/phase6-v2-console-J-current, committed audits/2026-10-30-console-capture-host metadata/current identity/timeline/source hashes/self-test summary and reference to identical previous-console archive. Current eMMC dmesg remains in out with hash and is not used as diskless cause. Files/docs: new collector/test and active capture phase document, total design, PROGRESS, this ledger/evidence. SCP independent snapshots compared on Mac before execution. No new mistake/revocation; existing F6-023 provenance rule applies. Closing identity is this commit.

Next exact question: can a composed preflight freshly validate original frozen/P2 inputs plus the explicitly distinct root-fstab derivative/trace map, before separately documenting a single hardware question and conditions? Hardware PAUSED; no boot/recovery/reset authorization is created by J. Later NBD timeout and derivative real-device mount/boot remain UNKNOWN.

---

## Batch 2026-10-30-K — Composed root-fstab preflight and proposed R1 plan

Starting branch/HEAD: diskless-v2 /71945d787aeb963d05981cfa306e5510afac2485, J closed; I derivative host-pass/current baseline available, hardware paused. Question: can unchanged original clean-source/P2 gates and explicit derivative gates be composed without weakening source identity? Answer YES, HOST_FACT.

Added phase6_v2_root_fstab_preflight.py: fresh output required, explicitly pinned original input paths, current repaired full original preflight, exact rebuilt P2 boot SHA check; then independent full-byte derivative audit, disk-structure validation and two matching derivative trace maps. All five stages and final composed gate pass with exit0 on the Mac. Trace-map SHA4a70e1c1ceb1933ba840c73b77b67bfcbd1429a2fa2aa360f3381be2856fd90b; original/derived hashes unchanged. Raw historical original-gate panic binary question is scoped as an artifact check, not reused as current runtime inference. Source snapshot SCP transferred and compared before execution.

Prepared PHASE6_ROOT_FSTAB_RUN_R1.md with the sole root-fstab variable, frozen hashes, host gates, observer readiness, conditional one-shot RAM-boot sequence from current eMMC, USB-only export, binary AND-based p3/p6 evidence question, positive/negative/INCONCLUSIVE outcomes, provenance limits, full2100s session observation/cap behavior and stops/preservation. Its status remains NOT AUTHORIZED. No device command, boot, root restart or export occurred in K; host PASS cannot activate itself.

Evidence/end artifacts: out/phase6-v2-root-fstab-K-preflight; audits/2026-10-30-root-fstab-preflight with every child stdout/stderr/status, current reports/map/result and source SHA. No new mistake/revocation was found. Files/docs: new composed preflight, proposed R1 document, total design, PROGRESS, this ledger/evidence. Closing identity is this commit. Next question: are the committed R1 conditions/readiness satisfied so a separately documented one-run hardware exception can be activated? Hardware PAUSED at K close; actual root-fstab runtime effect/full boot/NBD late-timeout cause remain UNKNOWN.

---

## Batch 2026-10-30-L — R1 conditional activation / execution batch open

Starting branch/HEAD: diskless-v2 / a23e2ad1c9cfb73f8fb3cc855e01c9f9ca942916; K closed/committed. Goal/binary question: run the root-fstab-only derivative once and determine whether both cache/p3 and persist/p6 filesystem-read evidence appears on one NBD session. Fresh readiness verifies original current rooted eMMC boot/serial/physical USB, clean tracked state, no10810 listener, full derivative disk and boot/bootstrap/manifest/map pins. Raw readiness/launcher are preserved before execution. R1 exact plan/conditional single-use activation is synchronized with total design/PROGRESS; observers must be healthy/armed before any device transition.

Before activation, noticed stale Selected next experiment wording in historical total-design P1/P2 sections; reconciled history/current headings and appended F6-025 before issuing any transition. No experiment ran against inconsistent authority. Runtime source/protocol unchanged. Launcher SHA da8cdfc6cec277e67b4d9812d4a6c672708587ae829d2560228226614bbc3815 differs from old P2 only in run/disk/map/name paths and sampling duration. The next entry will close this same controlled execution with counts/evidence/outcome/process state; no unrelated batch/experiment may begin first.

---

### L interim milestone — R1 binary YES, observation not closed

Execution/authorization HEADb8722970d64cbd626aa37efdab38e458fe9b0c47. One guarded ADB-to-bootloader, one pinned lk2nd and one exact P2 diagnostic RAM boot all succeeded; diagnostic completed08:10:49.526796UTC. USB/ADB observers were armed first. USB-only server PID862 bound172.16.42.2:10810 and accepted exactly one session; first request within120s. REAL_DEVICE_FACT: cache/p3 SB+GDT complete at request721, persist/p6 at838, userdata/p5 at943. R1 AND-question YES; existing Phase6-E classifier also PASS. Snapshot1902 completed replies,1875 reads/70,493,184 bytes (p1:51,897,344),27 writes/1,421,312 bytes. No mount/full-boot/caller/late-fs claim follows. Later request inactivity and TCP5555 timeout are observations, cause UNKNOWN.

Immutable positive trace prefix/classifier/result, command transcripts, state and snapshot evidence archived in audits/2026-10-30-root-fstab-R1-positive; full logs continue in out/phase6-root-fstab-R1. R1 permission consumed/hardware paused. USB/ADB watchers and NBD snapshots continue; live root server preserved. Runtime-written disk no longer pristine. This is an interim evidence commit within L, not a batch close or permission for another investigation/experiment. Final terminal/cap/provenance/process-state capture and documentation close remain required.

---

### Batch L close — NBD mounts/late-fs proved; panic console captured after user transition

Starting HEADa23e2ad1c9cfb73f8fb3cc855e01c9f9ca942916; activationb8722970d64cbd626aa37efdab38e458fe9b0c47; positive evidence8c77b84fdd7fb92096b9f152b3f10f092a854657. Sole R1 hardware counts remained1 ADB-to-bootloader,1 lk2nd RAM boot,1 diagnostic RAM boot, no flash/erase/retry/recovery boot. Binary p3-AND-p6 answer YES,1902 replies including27 writes, original sources preserved. At08:32:13UTC continued passive waiting ended by user steering, not a reset-cause conclusion. F6-026 records the mistake of relying on automatic fallback as the only active console route despite a bounded cap.

The user explicitly chose manual hard reboot into eMMC and requested continuous ADB capture, then reported reboot done. Existing collector saved117459 bytes of last_kmsg at08:33:49.513661UTC, successor UID0/boot IDf1ff23e5-d651-48fc-a764-e75f79e95330 stable, uptime15.57->16.43. SHA86741d43b64d590bde65d1238a752b327519e8b2eca1e4d81d2ea215b1379c4b. Full diskless ring head, only controlled R1 NBD boot, distinguishing new NBD mounts vs pinned baseline and continuous USB/user sequence establish R1 attribution; collector's first-visible/first-successor distinction remains explicit. Later eMMC ADB loss did not erase host evidence.

REAL_DEVICE_FACT: NBD p1/p2 mounts successful, cache/persist mounts at15.499/15.649s, data at17.031s; early mount_all498ms, late622ms, explicit post-fs-data; netd/zygote start around20s. Phase6-E/F PASS. SELinux fsck denial is recorded but mount succeeds afterward; it is not established as stall cause. NBD receive -110 at1077.926s precedes journal/I/O failures and explicit p5 ext4 panic/stack at1078.293s. Terminal panic is proved; initial I/O loss near20s and full Android boot remain UNKNOWN/NOT_PROVEN. No automatic reboot conclusion and no last-visible-line bypass is accepted.

The user next reported stock fastboot. Same serial/physical USB/productflo were verified08:37:42UTC; only then were R1 server862/sampler99861/USB observer99849/ADB watcher99850 stopped. A preceding live-ADB cleanup guard found ADB unavailable and stopped nothing. No agent state-changing command followed R1. Current device fastboot; all R1 processes closed; no active export. Full final evidence/result/console/provenance/SHA manifest is in audits/2026-10-30-root-fstab-R1; raw runtime-written disk retained in out and not pristine. This close supersedes earlier open-observation/handoff snapshots without deleting them.

Docs changed in L: total design, PROGRESS, R1 phase, append-only F6-025/026, WORKLOG and three evidence directories (activation/positive/final). No kernel/protocol/rc runtime source changed. Closing identity is this commit. Next exact question: do the exact pinned transport-protection mechanisms cover the networking changes possible at the observed initial I/O-loss boundary, or does source establish an uncovered path requiring a narrowly observed diagnostic? This is a read-only source/contract audit, not authorization to patch/boot. Hardware PAUSED. Raw evidence retains byte-for-byte whitespace; normal diff checks apply to docs/code and SHA verification to raw captures.

---

## Batch 2026-10-30-M — Accepted transport-guard coverage audit

Starting branch/HEAD: diskless-v2 /daa09349715333b47e50cdf7b2392f27292fe391; L closed, device stock fastboot, hardware paused. Question: do repository-added accepted transport guards protect IPv4 addressing/rules/routes/netfilter against Android startup changes? Answer NO within the added-code scope, SOURCE_PROVEN. Reviewed exact managed patch/configure/independent-verifier/continuation code: only storage registration and msm_otg power/suspend hooks plus g_ether selection; no route/filter protection or surviving supervisor. This does not invalidate Phase4's real-device power/stress gate or prove an upstream networking behavior/cause.

HOST_FACT: Mac rechecked golden system SHA and independently resolved exact startup rc/build.prop/netd identities. netd inode822,size479760,SHAefb13b1f3b33289d85d2091b5c1c2a07d82fce2ee0e0fd02e879dd7bd833dbaf; extracted netd.rc/init.rc/init.flox.rc/USB rc show netd start/fwmark setup, not its compiled internal route operations. Kernel source tree was not present in Mac home; no Debian build/source modification was needed. No device command or runtime image change occurred.

Evidence/end artifact: out/phase6-v2-transport-coverage-M, committed audits/2026-10-30-transport-coverage with exact extracts/report/source hashes/SHA manifest. Files/docs: new active audit phase, total design, PROGRESS, this ledger/evidence. No new mistake/revocation; R1 timing is not netd causal proof. Closing identity is this commit. Next exact question: does the exact compiled netd startup remove/bypass ordinary main-table routing used by the pre-Android unmarked NBD socket? Establish artifact/source linkage or retain UNKNOWN, before selecting any single-variable runtime diagnostic. Hardware PAUSED/no boot or patch authorization; device stays fastboot.

---

## Batch 2026-10-30-N — Exact netd compiled-policy audit and R1 timing clarification

Starting HEAD23382dafcf2b0cab13ed01e049de4200ad58e9b6, M closed/device stock fastboot/hardware paused. Binary artifact question: does exact netd startup delete nonzero-priority rules and install unreachable fallback? Answer YES/HOST_FACT, conditional compiled behavior, not runtime causal proof. Exact ELF SHAefb13b1f3b33289d85d2091b5c1c2a07d82fce2ee0e0fd02e879dd7bd833dbaf embeds compressed symbols; mini-debug SHA945c3431bd60515959d7f9e619661e519364cd3a2b3e80886d07a011a12b5906. Mac bundled LLVM, explicit Thumb ranges, original-byte BL/vtable decoding verify main->Controllers->RouteController->rtNetlinkFlush, GETRULE34/DELRULE33/filter priority!=0 and priority32000/action7 fallback. Exact pinned kernel ABI headers retrieved read-only. AOSP11 is explanatory reference only; exact ROM source commit UNKNOWN. Initial wrong ARM-mode/nearest-symbol dump rejected (F6-028).

User challenged whether1078s panic coincided with manual reboot. Saved audit wall/uptime anchors extrapolate08:28:50.8UTC, announcement recorded08:33:22/USB drop08:33:27. Physical keypress timestamp is not controlled; independence stays UNKNOWN. Asking user to recall exact minutes was inappropriate (F6-027). Long request-flow stall was already failed startup validation; no renewed passive waiting or causal overclaim follows.

Evidence/end artifacts: out/phase6-v2-netd-policy-N; committed audits/2026-10-30-netd-policy with extracted symbol/range/ABI/report/timing evidence and SHA manifest. No device command, kernel compile or runtime image change occurred. Total design/PROGRESS/new netd phase/R1 clarification/failure ledger/WORKLOG synchronized. Closing identity is this commit. Next exact host question: can a deterministic separate P2-derived image add exactly one host/32 priority0 main-lookup rule plus fail-closed readback, and use a fresh R1-identical disk, without changing accepted kernel/NBD/rc/handoff behavior? This is PROPOSED_DIAGNOSTIC preparation only; no hardware boot is authorized. A later run needs bounded stall/controlled successor capture, not automatic-reboot waiting.

---

## Batch 2026-10-30-O — Root-route diagnostic artifacts and offline capture preparation

Starting HEADb56c2c3e4d42cf20c8279be6041b6dbf71c1ff50; N closed, device fastboot, hardware paused. Binary host question: can the single reviewed rule delta preserve all other image/disk contents? YES/HOST_FACT. Added pinned fragment, builder, independent delta auditor and three fail-closed tests; deterministic image SHA50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799. Accepted image audit and every-other-entry/header/kernel/init comparison pass. Runtime proof remains absent; rule add/readback precedes NBD fail-closed.

APFS clone of original disk plus root-fstab bytes independently matches R1 pre-run SHA060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a, full-byte source/p1/system/metadata/other-partition audit passes; original and runtime-written R1 disk preserved. Added explicit offline ADB arming path; four collector tests and actual2s fastboot/offline dry run pass. No device transition/boot/flash occurred. SCP independent snapshots compared before Mac execution. No new mistake/revocation.

Evidence/artifacts: out/phase6-v2-root-route-O and audits/2026-10-30-root-route-preparation. Changed code/docs: fragment, builder/auditor/test, host collector/test, preparation phase, total design/PROGRESS/WORKLOG/evidence. Closing identity is this commit. User explicitly requested immediate testing; next batch is Q1, fresh original fact gate and separately committed single-use plan/activation, max180s observation/60s no-progress handling with prepared manual successor capture. Hardware authorization remains NONE at O close; runtime effect UNKNOWN. No Debian compile required.

---

## Batch 2026-10-30-P — Q1 single root-route diagnostic (active)

Starting HEADb807d1f771883ae0352d08a214119991d18c9b38, O closed. User explicitly requested immediate testing. Goal: whether the sole peer/32 priority0 main rule lets successful NBD I/O continue beyond R1's prior cutoff. Fresh original fact gate, route image/current pristine disk/identity checks and bounded Q1 plan prepared. This committed plan/total design conditionally permit one lk2nd and one diagnostic RAM boot only after observer arming; no flash/retry/other boot. Active observation max180s,60s reply inactivity leads to controlled successor capture. Full result/evidence/process-state close remains required before any new batch.

---

### Batch P close — Q1 binary YES; GSS powerup panic captured

Starting HEADb807d1f771883ae0352d08a214119991d18c9b38,activation/execution6c7945bc272396f90ea7c9ee5e46b901275090eb. Fresh original fact producer/route audit/current full hashes/identities passed. One lk2nd/one diagnostic RAM boot,no flash/retry/extra ADB reboot. REAL_DEVICE_FACT: target peer-rule readback marker6.153594s;one NBD session18345 replies(17156 READ719774720B,1189 WRITE29736960B),97.950304s success span,cache/persist/userdata gates and system_server. Binary YES; route-protected baseline progress accepted, exclusive cause/post-netd RPDB not claimed.

At bounded180s/user-reported stopped animation,prompted controlled hard reboot; user confirmed. Collector saved130302-byte last_kmsg SHA43d12aa2ed4bff986198335fa213e81c1c6101303c9d9f7faa6a1d2c35867cae at09:23:16.986462UTC,UID0/boot389cb03f-aa51-4516-a245-4a8f08f29a3d stable,uptime15.92->16.78. Unique rule marker/full diskless head/sole Q1 load/USB-user sequence establish attribution, not first-visible alone. Primary GSS fatal/restart_level3/recovery leads subsystem_restart_wq_func panic107.166s; internal reason UNKNOWN. F6-029 separates secondary stopping NBD/qtaguid stacks. Later host TCP timeout is not cause proof; full Android boot NOT_PROVEN.

ADB later unavailable,cleanup guard stopped nothing. Subsequent verified stock fastboot/same serial/port/product allowed stopping all Q1-owned export/sampler/USB/ADB processes; no transition actor inferred. Written disk preserved. Evidence/result/provenance/SHA in audits/2026-10-30-root-route-Q1. Total design/PROGRESS/phase/failure/WORKLOG synchronized;closing identity is this commit. Next exact source question: does pinned GSS/SSR code map captured powerup panic to repeated startup/recovery failure independently of NBD, and what firmware inputs were used? Read-only audit only,hardware PAUSED/no new compile or boot. Retain root-fstab and peer-rule behavior in later isolated experiments.

---

## Batch 2026-10-30-Q — Exact GSS/SSR and GPS activation source audit

Starting HEADb129012155a67692b7a1191006bae26bee14813b,P closed/device fastboot/hardware paused. Binary source question whether pinned GSS/SSR explains primary powerup panic independently of NBD: YES/SOURCE_PROVEN. Fetched three exact kernel files/Git blobs; gss_open->pil_get,SMSM_RESET->restart,overlapping SSR powerup lock panic matches Q1. Firmware gss.mdt/b00..b11 and ueventd paths identified; operation/internal GSS cause UNKNOWN.

HOST_FACT: exact GPS HAL SHA dfe33c9f397ae51ad5085411a85f333fb41c3f587e89d1ec27e20820d98f20be,embedded symbols/Thumb/PLT show C entry2484 opens /dev/gss; separate gps.disable-aware function does not guard this entry. Actual caller process UNKNOWN. Minimal next proposed diagnostic: replace entry4 bytes70b502f0 with00207047(return NULL/GPS unavailable),retaining Q1 kernel/route/system/fresh disk inputs and every other byte. No kernel compile/rc bypass selected; runtime unproven. No device command/source modification occurred in Q.

Evidence out/phase6-v2-gss-source-Q and audits/2026-10-30-gss-source; new phase,total design,PROGRESS,WORKLOG synchronized. No new mistake/revocation; property-only candidate rejected before implementation. Closing identity is this commit. Next binary host question: can independent ELF/filesystem/full-byte gates prove exactly4 HAL bytes change and nothing else? Hardware PAUSED,no new boot authorized. GPS deferral is a captured-blocker diagnostic,not permanent feature acceptance.

---

## Batch 2026-10-30-R — Four-byte GPS HAL isolation host gate

Starting HEAD4ee8a911016e06a7c0841ac719906e23290057f1,Q closed/device fastboot/hardware paused. Binary host question exact4-byte-only GPS deferral possible? YES/HOST_FACT. Added pinned-source producer plus independent ELF/filesystem/streaming consumers. GPS entry returns NULL using00207047 at file0x1484; inode/extents/metadata/every other vendor byte unchanged. Native LLVM verifies Thumb semantics. New vendor SHA7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996.

Fresh APFS clones reconstruct pristine Q1 SHA060ba738...4498d5a and candidate3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811. Full disk comparison exactly4 changed bytes/p2 hash equals modified vendor, all other bytes unchanged. Disk structure/map gates pass; Q1 boot50377dc8...f99c799 unchanged. Complete Mac gate exit0. No kernel/rc/firmware/SELinux/route change or device command. Runtime-written Q1 retained. SCP script snapshot compared before execution.

Evidence out/phase6-v2-gps-null-R and audits/2026-10-30-gps-null-preparation. New host gate/preparation phase,total design,PROGRESS,WORKLOG synchronized; no new mistake/revocation. Closing identity is this commit. Next Q2 separately committed single-run plan/current gates, bounded active-progress observation and successor capture. Runtime IMPLEMENTED_UNPROVEN/hardware PAUSED. Temporary GPS deferral requires later restoration work; no Debian compile needed.

---

## Batch 2026-10-30-S — Q2 GPS-only diagnostic(active)

Starting HEADc09c5260c00d7b296cc4d43a5a05816821a01168,R closed/device fastboot. Goal whether four-byte GPS-interface deferral prevents captured GSS panic and progresses past107s. Conditional single-use Q2 plan/design synchronized; fresh original producer/current hashes/identities and armed offline capture required. One lk2nd/one Q1-image RAM boot only,new R disk only;no flash/retry/other boot. Observe180s,extend120 only with successful I/O,max300;60s no progress triggers controlled successor capture. Final evidence/result/process/document close required before another batch.

---

### Batch S close — core diskless setup and desktop success; preserve live runtime

Startc09c5260c00d7b296cc4d43a5a05816821a01168; authorization/execution9818dd26774fff4aee3da308a2011b583ec257e6. Fresh original producer/current pins/stock-lk2nd identities and armed observation passed. Exactly1 bootstrap and1 diagnostic RAM boot,no flash/erase/retry; command completed09:59:15.036924UTC. Only Q1-to-Q2 pristine delta remains4 GPS HAL bytes; Q1 boot50377dc8...f99c799 unchanged. HOST_FACT gates retained; no runtime code edited in S.

REAL_DEVICE_FACT: user first observed setup, accepted GPS unavailable, continued normal initialization, then confirmed desktop without observed crash. Snapshot10:12:18UTC: same gadget registry4295016541 since09:59:23UTC,one active NBD connection,25742 replies,818136064 READ bytes,89602048 WRITE bytes,successful requests beyond742s. Core diskless UI boot accepted for explicit GPS-null profile; no fallback USB transition observed. Behavioral progress is positive. Console-specific GSS criterion NOT_EVALUATED: preserve live successful OS instead of destructive successor capture. sys.boot_completed readback,GSS internal reason,other functions and long-term stability remain UNKNOWN. User accepts GPS omission; restoration optional future work. No new mistake/revocation discovered.

Live server12963 binds only172.16.42.2:10810; caffeinate14159 prevents Mac idle sleep while server exists. Keep USB/Mac/export running. USB/ADB/sampler12844/12845/12849 capped1200s; independent root server persists afterward. Disk out/phase6-v2-gps-null-R/disk.raw.img now includes user setup;3cf28c...e811 hash is pre-run only. Do not overwrite/commit private userdata or treat it as pristine. No cleanup stopping live storage performed.

Evidence/end identity: immutable complete-line log prefix and commands/gates/identities/process/user/result/SHA under audits/2026-10-30-gps-null-Q2/,cut10:12:18UTC; raw logs continue in out. Updated total design§5/7/9/16,PROGRESS,Q2 phase,this ledger; closing identity is this documentation commit. Previous S(active) entry is historical pre-run plan, superseded by this result. Next question: normal functions and reproducible working-profile packaging. User also asks how GApps Pico would be installed; advisory design discussion only, no live modification selected. Hardware permission consumed/PAUSED for new boots and experiments; live successful runtime preserved.

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
