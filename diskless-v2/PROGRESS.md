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
- legacy Linux 3.4 Kconfig resolution uses `oldnoconfig`, not the newer unsupported `olddefconfig` target;
- the ARM cross-compiler is pinned to LineageOS 18.1 GCC 4.9 at commit `da10d2bd65e2c57d338fb6bb712ff522ad4e34e7`;
- `scripts/v2/setup_toolchain.sh` creates the repository-managed toolchain checkout under `.toolchains/`;
- `build_kernel.sh` no longer auto-selects the host distro compiler and rejects any compiler other than the pinned GCC 4.9 checkout.

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

### Encountered issue P1-003 — host GCC 12 cannot build the legacy Linux 3.4 kernel

Observed output:

```text
include/linux/compiler-gcc.h:106:1: fatal error: linux/compiler-gcc12.h: No such file or directory
```

Cause:

The initial v2 wrapper auto-selected Debian's `arm-linux-gnueabihf-gcc`. On the current Debian host that compiler is GCC 12. This Linux 3.4 tree predates modern GCC compatibility headers; `compiler-gcc.h` dispatches by GCC major version and there is no `compiler-gcc12.h`.

This is a build-environment design error, not a reason to patch the kernel with an ad-hoc GCC 12 compatibility header.

Design correction:

The v2 build now pins LineageOS's own `lineage-18.1` ARM GCC 4.9 prebuilt toolchain:

```text
repository: LineageOS/android_prebuilts_gcc_linux-x86_arm_arm-linux-androideabi-4.9
commit:     da10d2bd65e2c57d338fb6bb712ff522ad4e34e7
prefix:     arm-linux-androideabi-
```

`build_kernel.sh` uses only this repository-managed toolchain by default. If it is absent, the wrapper runs `scripts/v2/setup_toolchain.sh`; the compiler version and toolchain commit are verified and recorded in the build manifest. Host GCC versions therefore no longer affect v2 kernel output.

Acceptance test to run next:

```bash
cd ~/nexus7_test
git pull
KERNEL_DIR=/home/debian/diskless_test/android_kernel_google_msm \
  bash scripts/v2/build_kernel.sh
```

On the first run after P1-003 this may clone the pinned LineageOS GCC 4.9 toolchain under `.toolchains/` before compiling the kernel.

Do not proceed to Phase 2 until this command completes with `DISKLESS_V2_KERNEL_VERIFIED=1`.
