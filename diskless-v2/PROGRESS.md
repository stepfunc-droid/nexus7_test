# Diskless v2 implementation progress

This file records implementation state and issues encountered while executing `DISKLESS_V2_EXECUTION.md`.

## Phase 1 — deterministic diskless kernel

Status: **in progress; first build acceptance test pending**.

Implemented:

- pinned LineageOS flo kernel repository/ref/commit in `diskless-v2/kernel.env`;
- deterministic config generation in `scripts/v2/configure_kernel.sh`;
- kernel build wrapper in `scripts/v2/build_kernel.sh`;
- independent invariant verifier and build manifest in `scripts/v2/verify_kernel.sh`;
- required diskless invariants include NBD built-in, g_ether built-in, Android composite gadget disabled, persistent RAM console enabled, and SDCC1/eMMC registration disabled;
- kernel source is rejected unless HEAD matches the pinned upstream commit;
- `board-flo-storage.c` must equal the pinned upstream file plus exactly the repository-managed SDCC1 disable patch;
- ARM architecture is passed explicitly to Kconfig/build operations.

### Encountered issue P1-001 — historical defconfig modification blocked the first build

Observed output:

```text
==> Preparing deterministic diskless-v2 config
ERROR: unexpected tracked kernel source modification: arch/arm/configs/lineageos_flo_defconfig
```

Cause:

The existing kernel working tree contains a tracked modification to `arch/arm/configs/lineageos_flo_defconfig` from earlier experiments. The first v2 baseline guard treated every tracked change except the SDCC1 patch as build-affecting and therefore rejected the tree.

Design correction:

The v2 build must not trust or consume the working-tree defconfig at all. `configure_kernel.sh` now reads the pristine `lineageos_flo_defconfig` directly from the pinned kernel commit with `git show`, writes that snapshot to the output `.config`, applies only the documented v2 symbol changes, and runs `ARCH=arm olddefconfig`.

The historical working-tree defconfig modification is therefore permitted but explicitly ignored and recorded in the manifest. Other unknown tracked source changes remain fatal. The SDCC1 source file is checked against the exact expected transformation rather than being trusted merely because its pathname is allowed.

Acceptance test to run next:

```bash
cd ~/nexus7_test
git pull
KERNEL_DIR=/home/debian/diskless_test/android_kernel_google_msm \
  bash scripts/v2/build_kernel.sh
```

Do not proceed to Phase 2 until this command completes with `DISKLESS_V2_KERNEL_VERIFIED=1`.
