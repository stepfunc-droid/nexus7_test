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

## Batch 2026-10-30-E — Review panic-hold host PASS and authorize one controlled run

**Goal**

Review the user's actual `phase6_v2_panic_hold_real_preflight.sh` output, classify the result correctly as host evidence, synchronize the authoritative project state, and decide whether exactly one real-device panic-hold run is authorized.

**Starting branch/HEAD/checkpoint**

```text
branch=diskless-v2
starting_HEAD=cc649ef92886ff2854128c936c58fddfa98f92ee
Phase1-5=ACCEPTED/FROZEN
6V2-D=PASS (REAL DEVICE transport attach)
Run1 reset/failure cause=UNKNOWN
panic-hold implementation=PREPARED
hardware=PAUSED
```

**Reviewed user-host result**

```text
DISKLESS_V2_PHASE6_V2_PANIC_HOLD_REAL_PREFLIGHT=PASS
diagnostic_image_sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
causal_variable=kernel.panic:5->0
panic_on_oops_target=1
runtime_precondition=fail-closed-readback-before-usb0-and-nbd
accepted_image_direct_panic_timeout_literals=0
accepted_continuation=unchanged
transport=accepted-6V2-path
```

Supporting audited identities/results:

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
replacement_wrapper_sha256=839ec782f5db944e3941ca7555b64528085cb1890109bd0fe4caae4a6257181a
system_sha256=a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
vendor_sha256=50224b71e7d534583804bb16f24a0c6a186a1cce6eff012ee2b42d9a5130aac6
kernel_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
android_init_sha256=cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
busybox_sha256=cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

**Evidence produced / class**

```text
actual real preflight                           HOST_FACT
exact diagnostic image identity                 HOST_FACT
exact wrapper delta                             HOST_FACT
reproducible A/B image build                    HOST_FACT
accepted-image canonical direct writer scan     HOST_FACT
runtime read-back mechanism before usb0/NBD     HOST_FACT + IMPLEMENTED PRECONDITION
real-device panic-timeout result                NONE YET
```

The writer-audit limitation remains explicit: nonliteral/programmatic sysctl access is not proven absent.

**Accepted conclusions**

- F6-017's host-side interpretation gap is closed for this experiment design: a later host-visible NBD connection can occur only after same-run fail-closed read-back has proved `panic=0` and `panic_on_oops=1`.
- The diagnostic image preserves the accepted continuation outside the approved panic precondition block.
- Phase1–5 remain unchanged and frozen.
- The host PASS does not itself establish whether Run1 used a Linux panic auto-restart path.
- The information gain now requires exactly one real-device A/B run.

**Files/docs/commits changed**

```text
12d29dd1f6e7c232260df01f7eba10eb64fb18ad  PROGRESS: record HOST PASS and authorize one controlled panic-hold run
cf8032317db8550734f0cbaf41604a9151fab78a  experiment doc: record actual preflight PASS and one-run authorization
8c6d444e397eb3087624608d86b9895e7ba05b07  total design: synchronize one-run hardware authorization
this WORKLOG commit                              close Batch E and record durable handoff
```

**Remaining unknowns**

```text
Run1 panic-timeout dependency                  UNKNOWN
Run1 entered Linux panic() path                UNKNOWN
Run1 kernel hang/deadlock                      UNKNOWN
Run1 watchdog/secure-side reset                UNKNOWN
Run1 userspace/init reboot                     UNKNOWN
Run1 other reset path                          UNKNOWN
6V2-E p3/p6 second-stage evidence              NOT REACHED
```

**Next exact question / handoff**

Run exactly one controlled RAM boot of:

```text
out/diskless-v2-android/phase6-v2-panic-hold.img
sha256=09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491
```

using the accepted 6V2 traced NBD path, preserving the trace/transcript and observing whether a Run1-comparable NBD stop is followed by a reboot or a >=90 second persistent hold.

No runtime patch or second run is allowed before that result is reviewed.

**Hardware authorization state**

```text
AUTHORIZED — ONE CONTROLLED PANIC-HOLD REAL-DEVICE RUN ONLY
boot method=fastboot boot only
flash=FORBIDDEN
second run=NOT AUTHORIZED
```

After that one run completes or aborts, hardware returns to `PAUSED` until evidence review and another checkpoint update.

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
