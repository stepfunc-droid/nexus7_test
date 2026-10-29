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
- ARM architecture is passed explicitly to Kconfig/build operations;
- the pristine flo defconfig is read directly from the pinned commit, so historical working-tree edits cannot affect v2;
- legacy Linux 3.4 Kconfig resolution uses `oldnoconfig`, not the newer unsupported `olddefconfig` target.

### Encountered issue P1-001 — historical defconfig modification blocked the first build

Observed output:

```text
==> Preparing deterministic diskless-v2 config
ERROR: unexpected tracked kernel source modification: arch/arm/configs/lineageos_flo_defconfig
```

Cause:

The existing kernel working tree contains a tracked modification to `arch/arm/configs/lineageos_flo_defconfig` from earlier experiments. The first v2 baseline guard treated every tracked change except the SDCC1 patch as build-affecting and therefore rejected the tree.

Design correction:

The v2 build does not trust or consume the working-tree defconfig. `configure_kernel.sh` reads the pristine `lineageos_flo_defconfig` directly from the pinned kernel commit with `git show`, writes that snapshot to the output `.config`, and applies only the documented v2 symbol changes.

The historical working-tree defconfig modification is permitted but explicitly ignored. Other unknown tracked source changes remain fatal. The SDCC1 source file is checked against the exact expected transformation rather than being trusted merely because its pathname is allowed.

### Encountered issue P1-002 — `olddefconfig` does not exist in this Linux 3.4 tree

Observed output:

```text
==> Running ARM olddefconfig
make[2]: *** No rule to make target 'olddefconfig'. Stop.
```

Cause:

The pinned LineageOS flo kernel uses the older Linux 3.4 Kconfig makefile. It provides `oldconfig`, `silentoldconfig`, and `oldnoconfig`, but not the newer `olddefconfig` target.

Design correction:

`configure_kernel.sh` now uses:

```text
make ... ARCH=arm oldnoconfig
```

`oldnoconfig` is non-interactive, keeps the supplied `.config` as the base, and assigns `n` to otherwise-unrepresented symbols. Immediately afterwards the v2 script verifies every required diskless invariant and fails closed if Kconfig changed one of them.

Acceptance test to run next:

```bash
cd ~/nexus7_test
git pull
KERNEL_DIR=/home/debian/diskless_test/android_kernel_google_msm \
  bash scripts/v2/build_kernel.sh
```

Do not proceed to Phase 2 until this command completes with `DISKLESS_V2_KERNEL_VERIFIED=1`.
