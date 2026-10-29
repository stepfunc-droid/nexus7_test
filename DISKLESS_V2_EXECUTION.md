# Nexus 7 flo/flox Diskless Android v2 — Design and Execution Source of Truth

This document is the project-wide source of truth for the diskless-v2 architecture, accepted runtime contract, phase acceptance boundary, and current debugging direction.

`AGENTS.md` defines how every work session must consume and maintain this document. `diskless-v2/PROGRESS.md` is only the concise current checkpoint. Phase documents contain detailed evidence/history and do not override this document.

If this document, `PROGRESS.md`, a phase document, and the implementation disagree, hardware work stops until the discrepancy is reconciled.

---

## 1. Goal

Build a reproducible, RAM-boot-only LineageOS 18.1 environment for Nexus 7 2013 (flo/flox) that does not depend on the failed internal eMMC after the bootloader stage.

Final-runtime requirements:

- boot with `fastboot boot`; do not flash the device;
- Linux must not register/use failed SDCC1/eMMC in diskless mode;
- use the Nexus USB device port for the root-storage network transport;
- use one USB Ethernet interface and one NBD connection carrying one partitioned virtual disk;
- Android mounts normal `/dev/nbd0pN` block partitions through deterministic fstab data;
- root transport is established before Android and does not depend on netd/vold/Android USB ownership;
- kernel and boot artifacts are tied to known source/config identities;
- Android remains as close to stock Lineage behavior as practical; diagnostic bypasses are never silently promoted to architecture;
- failures are classified from evidence before runtime mechanisms are changed.

---

## 2. Evidence vocabulary

All project claims must use the following distinction:

- **REAL_DEVICE_FACT** — directly demonstrated on the physical Nexus 7.
- **HOST_FACT** — demonstrated by deterministic host build/audit/self-test only.
- **SOURCE_PROVEN** — established from exact pinned source used by this project.
- **IMPLEMENTED_UNPROVEN** — present in code/artifact but not independently demonstrated as a runtime fact.
- **PROPOSED_DIAGNOSTIC** — experiment/artifact proposal; not accepted architecture.
- **REVOKED** — explicitly invalidated.
- **UNKNOWN** — insufficient evidence.

A host gate, source audit, or code inspection must never be described as a real-device fact.

---

## 3. Frozen accepted architecture — Phase 1 through Phase 5

Phase 1–5 are accepted/frozen. They may be changed only if new evidence directly invalidates an accepted gate.

### 3.1 Deterministic diskless kernel — REAL_DEVICE_FACT + HOST_FACT

Accepted identity:

```text
kernel_commit=0da5107137f93b8d8f697e949ab0784f5ace450c
config_sha256=ac1a000a3e2c539f3ba686cba3c3fa80f1381c4b51384024e00e37aee9a39180
zimage_sha256=eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05
```

Accepted invariants include:

- flo machine support;
- built-in NBD;
- `nbd.max_part=8` policy;
- built-in USB Ethernet gadget;
- `CONFIG_USB_G_ANDROID=n` in the diskless kernel;
- ext4/TCP/IPv4 required transport functionality built in;
- persistent RAM / Android ram_console support;
- SDCC1/eMMC registration disabled for diskless builds;
- diskless USB guard enabled;
- system-suspend guard at `PM_SUSPEND_PREPARE`.

The exact Phase4 accepted identity is also recorded in `diskless-v2/phase4-accepted.env`.

### 3.2 Single partitioned NBD disk — HOST_FACT + REAL_DEVICE_FACT

Logical layout source is `diskless-v2/layout.json`:

```text
p1 system    ext4  RO
p2 vendor    ext4  RO
p3 cache     ext4  RW
p4 extended
p5 userdata  ext4  RW
p6 persist   ext4  RW
p7 metadata  raw   RW/reserved
sector_size=512
nbd.max_part=8
```

One raw disk is exported over one TCP/NBD session on host port `10810`.

### 3.3 Transport supervisor — REAL_DEVICE_FACT

Accepted runtime conventions:

```text
/bin/busybox
#!/bin/busybox sh
BB=/bin/busybox
PATH=/bin:/sbin
/etc/diskless-v2-layout
usb0 on Nexus = 172.16.42.1/24
Mac transport endpoint = 172.16.42.2:10810
one /dev/nbd0 kernel session
```

Phase3 real-device acceptance included partition validation, RW persistence/reconnect behavior, and a 10-minute transport stress run:

```text
DISKLESS_V2_TRANSPORT_STATUS=PASS
detail=10-minute single-NBD transport acceptance passed cycles=212 checksum=2ae11a761b6f8386dbf3e378e58f0108
```

The BusyBox invocation contract above is frozen. Renaming the payload to `/diskless-busybox` is REVOKED.

### 3.4 USB/root-transport protection — REAL_DEVICE_FACT

Accepted safeguards:

```text
USB_DISKLESS_GUARD=enabled
USB_SYSTEM_SUSPEND_GUARD=pm_notifier
USB_SYSTEM_SUSPEND_STAGE=PM_SUSPEND_PREPARE
```

Phase4 preserved the NBD session through the suspend gate and repeated transport stress.

Do not infer that a later transport disappearance is the cause of a later boot failure merely because transport is the first host-visible component to disappear.

### 3.5 Deterministic Android fstab and first-stage handoff — REAL_DEVICE_FACT + HOST_FACT

Accepted fstab SHA:

```text
834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
```

Accepted mapping:

```text
/system    <- /dev/block/nbd0p1
/vendor    <- /dev/block/nbd0p2
/cache     <- /dev/block/nbd0p3
/data      <- /dev/block/nbd0p5
/persist   <- /dev/block/nbd0p6
metadata   <- /dev/block/nbd0p7
```

Accepted system image SHA:

```text
a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880
```

Accepted original Lineage boot `/init` SHA:

```text
cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44
```

Accepted BusyBox SHA:

```text
cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de
```

Phase5D real-device boot proved that the same accepted NBD session survived handoff and original Lineage first-stage mounted `/system` and `/vendor`.

Frozen packaging/handoff contract:

```text
/init                    diskless supervisor
/init.android            exact original Lineage boot init
/bin/busybox             exact accepted BusyBox payload
/etc/diskless-v2-layout  exact accepted layout contract
```

Before handoff, supervisor-owned `/dev/pts`, `/sys`, and `/proc` mounts are detached according to the accepted Phase5 behavior, then the wrapper executes `/init.android`.

---

## 4. Accepted Phase6 continuation baseline

Phase6 must continue from Phase5D by subtraction/minimal delta, not redesign.

The first Phase6 reset architecture that introduced `/diskless-busybox` and `rdinit=/diskless-init` is REVOKED. Host agreement did not make it valid; its first real-device boot failed before any NBD connection.

Audit-V2 continuation preserves Phase5D transport and handoff behavior and removes diagnostic observers/SIGSTOP so Android may continue naturally.

Accepted continuation host identity:

```text
continuation_image_sha256=0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780
continuation_wrapper_sha256=2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc
handoff=exec-/init.android
busybox=/bin/busybox
android_rc_modifications=none
selinux_policy=stock-enforcing-baseline
```

Host gates 6V2-A/B/C passed. These are HOST_FACTS, not hardware acceptance by themselves.

---

## 5. Current runtime contract and evidence class

These values must be known before reasoning about a Phase6 run.

### 5.1 Boot/runtime controls

| Item | Current value | Evidence class | Notes |
|---|---|---|---|
| `androidboot.diskless` | `1` | HOST_FACT / IMPLEMENTED_UNPROVEN as semantic Android input | exact cmdline token audited |
| `nbd.max_part` | `8` | REAL_DEVICE_FACT | partition nodes used successfully |
| `rdinit` | `/init` | HOST_FACT + observed continuation execution | no `/diskless-init` redesign |
| SELinux request | stock enforcing baseline | HOST_FACT | no permissive cmdline token in accepted continuation |
| `panic_on_oops` | wrapper requests `1` before Android handoff | IMPLEMENTED_UNPROVEN | code executes conditionally if sysctl is writable; value has not been independently read back in Run1 |
| `panic_timeout` | cmdline contains `panic=5`; wrapper requests runtime `5` | HOST_FACT / IMPLEMENTED_UNPROVEN as read-back runtime state | do not treat as Run1 root cause without experiment |
| MSM watchdog default | enabled by pinned source unless disabled | SOURCE_PROVEN | exact Run1 runtime watchdog state was not measured |

### 5.2 Root transport

| Item | Current value | Evidence class |
|---|---|---|
| Nexus interface | `usb0 172.16.42.1/24` | REAL_DEVICE_FACT |
| Mac endpoint | `172.16.42.2:10810` | REAL_DEVICE_FACT |
| NBD sessions | exactly one | REAL_DEVICE_FACT |
| backing disk | partitioned raw disk from accepted layout | REAL_DEVICE_FACT |
| Android USB composite gadget | disabled in diskless kernel | HOST_FACT + accepted kernel identity |

### 5.3 Diagnostic behavior

Accepted continuation deliberately does **not** carry the earlier HTTP/live-kmsg/SIGSTOP observer set.

The transport-only recovery image can snapshot previous `/proc/last_kmsg`, but a `last_kmsg` is useful for a specific run only when previous-boot provenance is controlled during that same experiment.

Absence of `last_kmsg` never proves a userspace reboot.

---

## 6. Boot flow

```text
stock fastboot
    |
    v
lk2nd (RAM only, forced fastboot)
    |
    v
diskless-v2 boot image
    |
    +-- accepted deterministic flo kernel
    |
    `-- diskless supervisor
          |
          +-- mount/setup minimal proc/sys/dev state
          +-- wait/configure usb0
          +-- attach exactly one NBD session
          +-- validate /dev/nbd0 + expected partitions
          +-- detach supervisor-owned handoff mounts
          `-- exec /init.android
                    |
                    +-- original Lineage first-stage init
                    +-- mount p1 system + p2 vendor
                    +-- SELinux setup/transition
                    +-- second-stage init
                    +-- fs: p3 cache + p6 persist
                    +-- late-fs: p5 userdata
                    `-- later services / launcher
```

Stage-isolation rule:

- p1/p2 activity can occur during first stage;
- filesystem-internal p3 or p6 activity is stronger evidence of second-stage `fs` processing because they are not first-stage mounts;
- p5 activity alone must not be overinterpreted as a semantic caller unless the mount-stage conditions are independently satisfied.

NBD observes block traffic, not userspace callers. Physical extent overlap with a file cannot prove that a specific process parsed or semantically used that file.

---

## 7. Phase status

```text
Phase 0   v1 frozen/documented                           COMPLETE
Phase 1   deterministic diskless kernel                  ACCEPTED / FROZEN
Phase 2   single partitioned NBD disk                    ACCEPTED / FROZEN
Phase 3   transport supervisor + stress                  ACCEPTED / FROZEN
Phase 4   USB/root-transport protection                  ACCEPTED / FROZEN
Phase 5   deterministic Android fstab + first stage      ACCEPTED / FROZEN
Phase 6   full Android integration                       ACTIVE
Phase 7   normal runtime feature restoration             NOT REACHED
```

### Phase6 Audit-V2 gate state

```text
6V2-A frozen facts                         PASS (HOST)
6V2-B continuation semantic/image audit    PASS (HOST)
6V2-C traced NBD differential/audit        PASS (HOST)
6V2-D transport attach on real device      PASS (REAL DEVICE)
6V2-E p3/p6 second-stage evidence          NOT REACHED
6V2-F late-fs evidence                     NOT REACHED
6V2-G first genuine later blocker          ACTIVE / UNKNOWN
```

---

## 8. Phase6 real-device Run1 — accepted observations only

The accepted continuation established USB ECM and exactly one NBD connection and performed substantial real block I/O.

Recovered host terminal summary:

```text
requests=1755
reads=1755
writes=0
read_bytes=75442176
phase=request-header-recv
last=[READ offset=0x1ce00000 (484442112) length=94208 fua=0]
connection_close=transport-error:TimeoutError(60, 'Operation timed out')
```

Accepted interpretation:

- 1755 READ requests / 75,442,176 bytes completed;
- `phase=request-header-recv` means the previous READ was already serviced and the server was waiting for a new NBD request header;
- macOS errno 60 is ETIMEDOUT, not evidence of an application-configured 60-second server timeout;
- the host timeout is not accepted as the cause of the Nexus-side failure;
- after Nexus-side NBD I/O stopped, the user observed the device reboot;
- the current evidence does **not** establish whether the device first panicked, hung, watchdog-reset, received a userspace/init reboot request, or followed another reset path;
- no accepted p3/cache or p6/persist filesystem evidence was observed, therefore 6V2-E remains NOT REACHED.

A reverse map associated the final successful p1 read with disk blocks belonging to `/system/lib/libkeystore_aidl.so`. This is forensic context only and carries no caller/root-cause meaning.

Current root-cause classification:

```text
transport_attach=PROVEN
transport_caused_failure=NOT_PROVEN
kernel_panic=UNKNOWN
kernel_hang=UNKNOWN
watchdog_reset=UNKNOWN
userspace_or_init_reboot=UNKNOWN
second_stage_or_later=NOT_PROVEN
```

---

## 9. Current blocker

The current blocker is not “which file was read last.” It is the unclassified failure/reset boundary after substantial p1/system I/O and before accepted p3/p6 second-stage evidence.

The next experiment must classify one failure dimension without changing accepted transport/Android architecture.

No result may be inferred from stale Run1 `/proc/last_kmsg` because its previous-boot provenance is no longer controlled.

---

## 10. Current hardware authorization state

**HARDWARE PAUSED FOR GOVERNANCE/DOCUMENT RECONCILIATION.**

No additional Phase6 real-device boot is currently authorized by this document.

The following recently created scripts exist in the repository:

```text
scripts/v2/phase6_v2_panic_hold_host_gate.sh
scripts/v2/phase6_v2_panic_hold_real_preflight.sh
```

Their status is:

```text
PROPOSED_DIAGNOSTIC
NOT_ACCEPTED_ARCHITECTURE
NOT_HARDWARE_AUTHORIZED
```

They were created before the project working protocol was rebuilt. They must be re-reviewed under `AGENTS.md` together with the exact pinned kernel/watchdog source and the current evidence before they can become an authorized experiment.

Likewise, the Run1 `last_kmsg` capture helpers are not evidence for Run1 unless provenance can be established; they remain utilities, not a causal conclusion.

---

## 11. Debugging rules

1. Classify before patching.
2. One experiment = one binary question.
3. Never patch the last visible log/file merely because it was last.
4. Prefer persistent evidence when the network itself may disappear, but control provenance.
5. Do not infer semantic callers from NBD block traffic.
6. Do not treat TCP state/timeout as kernel-liveness proof or failure cause by itself.
7. Do not advance an evidence class by wording.
8. Do not modify accepted Phase1–5 mechanisms without direct contradicting evidence.
9. Do not add Android rc bypasses without a captured subsystem error.
10. Do not allow builder/auditor self-consistency to substitute for real-device proof.
11. Every accepted/revoked runtime change must be reflected here before another hardware run.
12. `UNKNOWN` is a valid result and is preferred over an unsupported explanation.

---

## 12. v1 lessons that remain binding

The frozen v1 prototype established useful possibilities but also demonstrated failure modes that must not be repeated:

- permissive SELinux may move a diagnostic boot farther, but that does not prove SELinux is the root cause;
- bypassing Qualcomm devwait/ADSP or installd/configfs can alter timing and I/O pressure and must not become permanent fixes without evidence;
- a TCP socket shown as `ESTABLISHED` on the Mac does not prove the Nexus kernel is still processing packets;
- a dropped NBD connection can be a consequence of a deeper failure;
- network kmsg readers cannot be relied on after a kernel panic;
- the flo kernel already provides persistent RAM console support, but previous-boot provenance must be controlled;
- the diskless kernel must use one explicit USB gadget architecture;
- build reproducibility and artifact identity are mandatory.

---

## 13. Immediate next action

The immediate action is **not a hardware boot**.

1. Establish and follow `AGENTS.md`.
2. Reconcile `diskless-v2/PROGRESS.md` with this document.
3. Treat existing Phase6 phase documents as detailed evidence/history; do not reuse stale “current state” sections without reconciliation.
4. Re-review the proposed panic-hold experiment and any alternative reset-classification experiment against the current evidence and pinned source.
5. Only after one experiment is documented with one binary question, one controlled delta, interpretation/INCONCLUSIVE rules, preserved artifacts, and passing host gates may this document authorize the next real-device boot.
