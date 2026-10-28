# Nexus 7 flo/flox Diskless Android v2 Execution Plan

## 1. Goal

Build a reproducible, RAM-boot-only LineageOS 18.1 environment for Nexus 7 2013 (flo/flox) that does not depend on the failed internal eMMC after the bootloader stage.

The final runtime must satisfy all of the following:

- Boot image is loaded with `fastboot boot`; nothing is flashed.
- Linux does not register the internal SDCC1/eMMC device in diskless mode.
- The USB device port is dedicated to the root-storage transport while Android is running.
- A single NBD connection carries a partitioned virtual disk instead of five independent NBD sessions.
- Android sees normal block partitions (`/dev/nbd0pN`) and mounts them through a deterministic fstab.
- Kernel crashes are captured in persistent RAM and are readable on the next boot without relying on USB networking being alive at the moment of failure.
- Every generated boot image is tied to a known kernel source/config and rejected if required invariants are not satisfied.
- Android services are kept as close to stock Lineage behavior as possible. Diagnostic bypasses must not silently become permanent architecture.

This document is the source of truth for implementation order. Do not skip a gate because a later stage appears to work.

---

## 2. Why v1 is frozen

The current prototype proved that the general idea is viable, but it evolved by patching the last visible failure rather than by enforcing a complete architecture.

The v1 path is therefore frozen for reference/debugging only. No new behavior should be added to it except fixes that help extract evidence needed by v2.

### What v1 proved

- A custom flo kernel can RAM-boot through lk2nd.
- Built-in USB Ethernet can establish a stable early `usb0` link to the Mac.
- The old Linux 3.4 NBD driver can attach remote block devices over that link.
- Lineage first-stage init can mount remote `system` and `vendor` block devices.
- Android second-stage init can progress through zygote/early-boot and enter the `boot` trigger.
- The internal eMMC can be absent from the running Linux block-device tree.

### What v1 did not prove

- That the USB/NBD transport remains valid after Android networking/power management is fully active.
- That the kernel configuration used for each boot is exactly the configuration we think it is.
- That late-boot stalls are userspace stalls rather than kernel oops/panic/deadlock.
- That five simultaneous NBD sessions are reliable on this 3.4 kernel and one USB NIC.
- That the growing set of binary-patched Android rc files still represents a valid Lineage runtime.

---

## 3. Important failures encountered in v1

### 3.1 SELinux transition failure

The boot originally stopped during SELinux transition. Running permissive allowed the system to proceed much farther.

Lesson: early diagnostic boots may use permissive mode, but v2 must record this explicitly as a diagnostic policy and later restore enforcing.

### 3.2 Qualcomm `devwait` / ADSP wait

`init.flox.rc` synchronously executed `/vendor/bin/init.qcom.devwait.sh`, which waited for `sys.qcom.devup=1`. In the prototype this blocked progress, so `devwait` and later `devstart_sh` were bypassed.

Lesson: bypassing these services is useful to isolate transport problems, but permanently removing ADSP startup is not an acceptable final solution.

### 3.3 `installd.rc` sdcardfs/configfs early-boot block

The visible boot stopped while processing the large early-boot configfs setup from `installd.rc`. Disabling that block moved the system into the `boot` trigger.

Lesson: removing a block and progressing farther does **not** prove that block was the root cause. It also changes I/O pressure, concurrency and timing. In v2, such changes must be treated as diagnostic experiments, not architectural fixes.

### 3.4 USB/NBD becomes non-responsive during later boot

At the observed stall:

- macOS still showed the USB Ethernet interface as active.
- NBD TCP sessions could remain shown as `ESTABLISHED`.
- the kmsg TCP session could remain shown as `ESTABLISHED`.
- ping to `172.16.42.1` failed.
- ARP could disappear.
- interface packet counters stopped advancing.

Lesson: an `ESTABLISHED` TCP state on the Mac does not prove that the Nexus kernel is processing packets. USB/network transport and kernel liveness must not be inferred from socket state alone.

### 3.5 One NBD connection later timed out

In one run the `system` NBD session disappeared and the Mac-side server eventually reported a send timeout. Later runs showed all five sessions still established while the Nexus stopped processing traffic.

Lesson: a dropped NBD connection can be a consequence of a deeper kernel/USB stall. The system must not be debugged by assuming the first visible TCP failure is the root cause.

### 3.6 Diagnostic blind spot: `panic=0` + network kmsg

The prototype boot cmdline used `panic=0`, while Android init enables `panic_on_oops=1`.

If a kernel oops occurs:

1. it is promoted to panic;
2. `panic=0` leaves the machine stopped forever;
3. the userspace `cat /proc/kmsg | nc ...` logger cannot run after the panic;
4. the Mac only sees the last normal line before the crash.

Lesson: the prototype was structurally incapable of capturing the most important late-boot crash evidence.

### 3.7 The flo kernel already has persistent RAM console support

The Lineage flo kernel enables Android RAM console/persistent RAM support and ASUS board code reserves persistent RAM for it. The old kernel exposes the previous console through `/proc/last_kmsg`.

Lesson: v2 must use this native crash-capture path before relying on live USB logging.

### 3.8 Competing USB gadget architectures

The stock flo kernel configuration contains the Android composite gadget (`CONFIG_USB_G_ANDROID=y`). The prototype additionally enabled `CONFIG_USB_ETH=y` and then disabled several Android USB rc imports in the system image.

Lesson: a diskless kernel must have one explicit gadget architecture. v2 will use the USB Ethernet gadget for storage transport and disable `USB_G_ANDROID` in diskless builds.

### 3.9 Build reproducibility was not enforced

The prototype build script accepted an existing `zImage` without proving its exact source/config or proving that the eMMC-disable patch was present.

Lesson: v2 builds must fail closed when kernel invariants do not match the diskless design.

---

## 4. v2 design principles

### 4.1 One transport purpose per USB port

While Android is running in diskless mode, the USB device port is the root-storage transport. MTP, ADB-over-USB, RNDIS reconfiguration and normal Android USB gadget ownership are secondary and must not be allowed to reconfigure the controller.

ADB, if needed later, should initially use TCP over the already-existing diskless network rather than competing for USB gadget ownership.

### 4.2 One NBD session, one virtual disk

Do not export five independent NBD devices.

Export one virtual disk from the Mac and use the kernel's NBD partition support:

```text
/dev/nbd0
  p1  system    RO
  p2  vendor    RO
  p3  cache     RW
  p4  userdata  RW
  p5  persist   RW
  p6  metadata  RW/reserved
```

Exact partition numbers/sizes are defined once in a manifest and reused by image creation, fstab generation and validation.

Benefits:

- one TCP socket instead of five;
- one NBD `NBD_DO_IT` session;
- fewer old-3.4 NBD queues/threads;
- one place to instrument transport failures;
- simpler reconnect/failure semantics;
- easier host-side packet/block tracing.

### 4.3 Deterministic kernel

The v2 kernel is a product, not an incidental artifact from a previous build directory.

Required invariants include at minimum:

- flo machine support enabled;
- `CONFIG_BLK_DEV_NBD=y`;
- NBD partition scanning configured (`max_part` supplied at boot or compiled policy);
- `CONFIG_USB_ETH=y`;
- `CONFIG_USB_G_ANDROID=n` for the diskless kernel;
- persistent RAM / Android RAM console enabled;
- SDCC1/eMMC registration disabled for diskless builds;
- required ext4/TCP/IPv4 functionality built in;
- no required root-transport component as a module stored on the remote root filesystem.

The build script must print and save:

- kernel git commit;
- kernel config hash;
- resulting zImage hash;
- resulting boot image hash.

### 4.4 Persistent crash evidence before live logging

Diagnostic priority:

1. previous-boot persistent RAM console (`/proc/last_kmsg`);
2. current kernel console/live kmsg;
3. Android/logcat diagnostics;
4. host-side NBD request trace.

A kernel crash must auto-reboot after a short delay (initially 5 seconds) so the next minimal boot can recover the crash log.

### 4.5 Android should not own the root transport lifecycle

The root-storage link must be established before Android first-stage init and must not depend on Android properties, netd, vold or USB gadget rc files.

Long-term, the diskless transport should be protected from Android reconfiguration. Candidate approaches, in priority order:

1. dedicated diskless kernel USB policy that prevents Android gadget ownership and prevents USB PHY low-power transitions that break the active root transport;
2. make the diskless interface explicitly unmanaged by Android userspace;
3. if supported and necessary, isolate transport in a separate network namespace before Android starts.

Do not adopt option 3 unless kernel support and process/socket lifetime are verified on this 3.4 tree.

### 4.6 Keep Android close to stock

The final v2 should not permanently depend on binary edits that disable unrelated subsystems.

Initial transport bring-up may run with a minimal diagnostic Android configuration, but every bypass must be tracked and later removed or justified.

---

## 5. Target boot flow

```text
stock fastboot
    |
    v
lk2nd (RAM boot)
    |
    v
diskless-v2 boot.img
    |
    +-- deterministic diskless flo kernel
    |
    `-- v2 initramfs
          |
          +-- mount proc/sys/dev
          +-- read and upload /proc/last_kmsg if present
          +-- wait for usb0
          +-- set 172.16.42.1/24
          +-- connect exactly one NBD session to Mac
          +-- wait for /dev/nbd0 and partition nodes
          +-- validate expected partition sizes/filesystems
          +-- start optional live diagnostics
          `-- exec original Android /init
                    |
                    +-- first-stage mount nbd0p1/nbd0p2
                    +-- second-stage init
                    +-- data/cache/persist from nbd0 partitions
                    `-- launcher
```

---

## 6. Execution gates and TODO list

Each phase has a hard acceptance gate. Do not continue until the gate passes repeatedly.

### Phase 0 — Freeze and document v1

- [x] Preserve current v1 scripts as reference.
- [x] Document known failures and architectural problems.
- [ ] Stop adding new Android rc bypasses to v1.

**Gate:** this document is committed and becomes the implementation checklist.

### Phase 1 — Deterministic diskless kernel

Create scripts that build/verify the kernel from a known tree/config.

Tasks:

- [ ] Add `scripts/v2/verify_kernel.sh`.
- [ ] Add a repeatable diskless config transformation starting from `lineageos_flo_defconfig`.
- [ ] Enforce `CONFIG_BLK_DEV_NBD=y`.
- [ ] Enforce `CONFIG_USB_ETH=y`.
- [ ] Enforce `CONFIG_USB_G_ANDROID=n`.
- [ ] Enforce persistent RAM/ram_console support.
- [ ] Enforce/verify SDCC1/eMMC registration is disabled.
- [ ] Verify all required root-transport pieces are built-in.
- [ ] Record git/config/image hashes in a build manifest.
- [ ] Remove `panic=0`; use a short nonzero panic timeout for diagnostic builds.

**Gate:** a clean kernel tree can be transformed, built and independently verified with no manual config editing.

### Phase 2 — Single partitioned NBD disk

Tasks:

- [ ] Define `diskless-v2/layout.json` (or equivalent) as the single partition-layout manifest.
- [ ] Create one sparse raw disk image.
- [ ] Create a DOS/MBR partition table compatible with the old kernel.
- [ ] Place/copy system and vendor filesystems into their partitions without changing their filesystem contents.
- [ ] Create compatible ext4 cache/data/persist/metadata partitions.
- [ ] Add host-side layout validation.
- [ ] Export only this one disk from one NBD server port.

**Gate:** on a minimal RAM boot, `/dev/nbd0p1...` appear and all expected partitions can be read; RW partitions survive a reconnect/reboot test.

### Phase 3 — v2 initramfs transport supervisor

Tasks:

- [ ] New `initramfs/diskless-v2-init` rather than extending the v1 wrapper.
- [ ] Upload previous `/proc/last_kmsg` before starting Android.
- [ ] Configure `usb0` deterministically.
- [ ] Attach one NBD device.
- [ ] Wait for and validate partition nodes.
- [ ] Fail visibly to a local emergency shell if transport validation fails.
- [ ] Keep diagnostic logging independent from Android init ordering.
- [ ] Do not start five `nbd-client` instances.

**Gate:** the transport-only image runs for at least 10 minutes under repeated read/write load with zero dropped NBD sessions and no packet-processing stall.

### Phase 4 — Protect USB root transport

Tasks:

- [ ] Audit flo `msm_otg` / CI13xxx suspend and charger-detection paths used by the actual diskless kernel config.
- [ ] Add an explicit `androidboot.diskless=1` policy.
- [ ] In diskless mode, prevent USB controller/PHY power transitions that would sever an active root-storage transport.
- [ ] Confirm charger/power-source detection cannot silently switch the USB data path into an incompatible state.
- [ ] Confirm Android USB init cannot bind/reconfigure the UDC because `USB_G_ANDROID` is absent.

**Gate:** transport remains alive through CPU idle/low-power enable, screen state changes and normal Lineage `boot` actions.

### Phase 5 — Deterministic v2 Android fstab/image preparation

Tasks:

- [ ] Generate/patch fstab from the partition manifest, mapping to `/dev/nbd0pN`.
- [ ] Remove eMMC-only entries for the diskless boot environment.
- [ ] Handle userdata metadata/encryption policy explicitly rather than with untracked byte edits.
- [ ] Validate resulting system/vendor images before server start.
- [ ] Do not disable ADSP, installd or unrelated Android services in the baseline v2 image.

**Gate:** original Lineage Android first-stage init mounts all required v2 partitions without any eMMC lookup.

### Phase 6 — Android boot integration

Tasks:

- [ ] Boot stock-as-possible Lineage userspace on the stable v2 transport.
- [ ] Use permissive SELinux only as an explicitly labelled diagnostic mode.
- [ ] Recover crash evidence from persistent RAM after every kernel failure.
- [ ] Fix real subsystem failures one at a time only after a captured error proves them.
- [ ] Restore/repair ADSP startup rather than permanently bypassing it.
- [ ] Restore correct installd/sdcardfs behavior or implement the required modern equivalent for this device tree.

**Gate:** reach launcher repeatedly (target: 10 consecutive cold RAM boots) with no transport loss.

### Phase 7 — Restore normal runtime features

Tasks:

- [ ] SELinux enforcing.
- [ ] audio/ADSP.
- [ ] Wi-Fi/Bluetooth as desired.
- [ ] persistent userdata integrity tests.
- [ ] ADB over TCP if needed.
- [ ] reboot/shutdown behavior that never touches failed eMMC.

**Gate:** stable daily-use runtime without hidden v1 bypasses.

---

## 7. Rules for future debugging

1. Do not patch the last visible log line merely because it is last.
2. First classify the failure as one of:
   - kernel panic/oops;
   - kernel live-lock/deadlock;
   - USB transport loss;
   - NBD protocol/session failure;
   - Android userspace synchronous wait;
   - Android service crash/restart loop.
3. Use persistent kernel evidence before network-based evidence when the network itself is suspect.
4. One experiment must answer one binary question.
5. Every temporary bypass must be listed in this document or a linked issue before it is merged into the v2 path.
6. Every build must be reproducible from repository scripts. No undocumented manual `.config` edits.
7. Do not advance to Android integration until the raw transport passes its standalone gate.

---

## 8. Immediate next action

Start Phase 1 only.

The first code change after this document is:

> Add a v2 kernel verifier that fails closed unless the built kernel configuration matches the diskless architecture.

Do not build the single-NBD disk or modify Android userspace until this verifier exists and passes on a known kernel tree.
