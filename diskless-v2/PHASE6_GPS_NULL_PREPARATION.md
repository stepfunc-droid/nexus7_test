# Phase6 four-byte GPS HAL diagnostic preparation

Batch R starts at4ee8a911016e06a7c0841ac719906e23290057f1 after Q closed. Binary host question: can the proposed GPS-interface deferral change exactly4 bytes and preserve all other Q1 inputs? YES/HOST_FACT. Runtime IMPLEMENTED_UNPROVEN; no hardware permission from this gate.

Original GPS SHA dfe33c9f397ae51ad5085411a85f333fb41c3f587e89d1ec27e20820d98f20be. Producer finds the unique contiguous original ELF in vendor and patches file offset0x1484 from70b502f0 to00207047. Independent consumer resolves /lib/hw/gps.msm8960.so inode/extents, validates unchanged exported Thumb get_gps_interface address0x2484, checks whole payload/metadata unchanged except4 bytes, then streams all vendor bytes. Native LLVM independently decodes new entry as movs r0,#0;bx lr. No stack/prologue is entered; NULL reports only GPS unavailable. This is a temporary captured-blocker diagnostic, not a firmware fix.

Fresh original-disk APFS clone plus prior root-fstab data reconstructs exact pristine Q1 SHA060ba738...4498d5a. A separate clone changes only corresponding p2 bytes; full6.2GB comparison proves exactly4 changed bytes, all tables/other partitions/metadata unchanged, and p2 hash matches modified vendor. Q1 boot50377dc8...f99c799 is unchanged; no kernel/rc/firmware/SELinux/network change or compile. Runtime-written Q1 disk retained. Source/component/offset/manifest/disk audits and trace-map validation all pass on the Mac.

```text
artifact_dir=out/phase6-v2-gps-null-R/
GPS_sha256=8cbc55bef118d680651e3a07a15d4d4bae44f7a34608dbcf0c7c4954454b81d9
vendor_sha256=7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996
disk_sha256=3cf28c2392d9daa945ae9e7b4edb52883330947a3ae4d9c74bb71e80d45ee811
manifest_sha256=9a040b59379961ce3039575fd459d86052b9760576c7d2523352d1f3d23f20e8
trace_map_sha256=23ba156c7c9859bc83ee03342f07d305e82fd96403613323d72041a954c1c5d9
vendor_patch_offset=37246084
boot_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
```

Evidence: audits/2026-10-30-gps-null-preparation. Independent streams reject any extra byte delta; pinned source/entry checks fail closed. No device command ran in R. Next: separately committed Q2 plan/current gates, one RAM test with Q1 route/root-fstab preserved, bounded active-progress handling and prepared successor capture. No kernel compilation needed; GPS restoration remains later work.
