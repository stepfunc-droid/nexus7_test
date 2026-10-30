# Phase6 second-stage root-fstab namespace audit

Status: **HOST_FACT / MISMATCH PROVEN / MINIMAL DERIVATIVE IMPLEMENTATION NEXT / HARDWARE PAUSED**.

Batch H starts at `69b35b4c4f3a28cf1af4e17db81a0a5f3d51eae4`. Binary host question: does the exact accepted system expose an unpatched root `/fstab.flox`, distinct from the patched boot/vendor copies consumed before/after handoff?

## Exact host findings

The existing read-only ext4 resolver was used on the Mac after verifying system SHA256 `a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880`.

```text
system /fstab.flox: regular file, inode 26, 4295 bytes
root_fstab_sha256=ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764
root_fstab=byte-identical to pinned stock eMMC fstab
root_fstab_is_vendor_symlink=false
system /init.flox.rc: inode 30
init_flox_rc_sha256=4b0d083ed82710b6a2925d2a24a9d6f7f4e1a679ffaed11835be98480add1487
calls=mount_all ./fstab.flox --early; mount_all ./fstab.flox --late
patched vendor /etc/fstab.flox: inode 265, NBD mapping present, eMMC paths absent
accepted_generated_fstab_sha256=834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf
```

Evidence class: HOST_FACT from exact artifact identity and filesystem resolution. The captured prior NBD console independently records these second-stage eMMC cache/persist/userdata paths being skipped; exact named-P2 console attribution retains the separate provenance limits. No current eMMC-system errors were used to derive this host finding.

The namespace gap is proven: changing boot `/fstab.flox` and vendor `/etc/fstab.flox` did not change system's independent root file after SwitchRoot. Phase5's real-device first-stage p1/p2 gate stays accepted/frozen; it did not validate later file lookup. No kernel, BusyBox, handoff or transport redesign is justified.

Evidence: `audits/2026-10-30-fstab-namespace/`. Source images were opened read-only, and no device command or runtime modification occurred in H.

## Next implementation batch — one-file diagnostic derivative

Create separate system and partitioned-disk derivatives while preserving the golden accepted sources. Replace only the system-root fstab file data with the exact accepted generated mapping, padded to the original file size using the accepted comment-padding convention. Preserve inode/extents/xattrs/filesystem geometry and all bytes outside that file. Do not edit any Android rc or bypass services/self-tests.

The diagnostic boot image remains the exact P2 panic-hold image; the only new intended runtime variable will be the root-fstab data in p1. A host audit must independently resolve the actual file and prove exact allowed bytes, unchanged file metadata/geometry, unchanged disk bytes outside the corresponding p1 file-data ranges, and p1 identity matching the derived system. Require deterministic builds and current source/image hashes. Do not relabel the derivative as the accepted clean source or alter old phase gates to accept it silently.

Before a hardware run, prepare automatic full-session observation and first-successor log capture through the now user-enabled rooted-debugging eMMC fallback; reject unidentifiable logs and observe beyond finite idle windows. Review/commit exact artifact hashes, binary runtime question, outcomes, stops and authorization separately. No next boot is authorized at this checkpoint. Later NBD timeout cause remains UNKNOWN and must not be conflated with the proven earlier fstab mismatch.
