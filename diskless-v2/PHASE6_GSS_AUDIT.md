# Phase6 GSS/SSR and exact GPS activation audit

Batch Q starts atb129012155a67692b7a1191006bae26bee14813b after P closed; hardware paused/current device stock fastboot. Binary source question: does pinned GSS/SSR explain the primary powerup panic independently of NBD? YES/SOURCE_PROVEN; internal GSS failure reason remains UNKNOWN.

Kernel commit0da5107137f93b8d8f697e949ab0784f5ace450c files fetched and Git-blob verified: gss-8064.c(d1f78113f7a0ece7a8cd3fe248bcd934c171326c),pil-gss.c(c7f8fb06bd8c4ca9dc2d0d33047dfcb00d96b00b),subsystem_restart.c(f24c706e83aeeb6f400a63722f0a37e575bf4ce9). No source change/build/device command occurred.

gss_open on /dev/gss calls pil_get("gss"). SMSM_RESET callback invokes restart_gss->subsystem_restart_dev. SSR releases shutdown_lock while retaining powerup_lock during recovery; another restart obtaining the former but not the latter panics with Q1's exact message. This matches primary GSS panic, not NBD origin. Missing SMEM reason does not establish a firmware/calibration cause; do not remove the panic safeguard instead of isolating activation.

HOST_FACT: vendor /firmware/gss.mdt,b00..b11 identities recorded; ueventd searches /vendor/firmware. Logged successful loading/reset release does not prove correct firmware operation. Original /dev/gss node rule is0660 system gps.

Exact /vendor/lib/hw/gps.msm8960.so SHA dfe33c9f397ae51ad5085411a85f333fb41c3f587e89d1ec27e20820d98f20be,size20272 contains /dev/gss. Embedded symbols/Thumb code/PLT identify get_gps_interface0x2484 and __open_2(/dev/gss) call0x24e2. HAL callback gps__get_gps_interface0x4d18 traverses thunk/PLT to this entry. A separate exported function supports gps.disable=1, but does not guard the C entry activation; property-only diagnostic not selected. Actual caller process UNKNOWN; no block-read-to-caller inference.

The C interface already has legitimate NULL-return paths. Proposed next host-only diagnostic replaces its first4 bytes(file offset0x1484,70b502f0) with00207047(Thumb movs r0,#0;bx lr),reporting only GPS unavailable before GSS activation. Explicit temporary GPS HAL deferral is justified by captured failure, not a blanket peripheral/rc/kernel bypass or permanent fix. Preserve exact Q1 boot/kernel/route/root-fstab/fresh data and every other vendor/disk byte. Require independent ELF/filesystem/full-byte gates. Runtime IMPLEMENTED_UNPROVEN/hardware paused; no kernel compile/Android rc edit selected.

Evidence: audits/2026-10-30-gss-source. Next binary host question: can the diagnostic change exactly those4 bytes with identical metadata/other partitions and unchanged Q1 image? No hardware run authorized by this audit.
