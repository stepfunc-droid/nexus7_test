# Phase6 exact netd startup policy audit

Batch N starts at23382dafcf2b0cab13ed01e049de4200ad58e9b6 after M closed. Hardware paused, device stock fastboot. Binary artifact question: does the exact netd contain a startup path that deletes nonzero-priority rules (including ordinary main lookup) and installs an unreachable fallback? **YES / HOST_FACT from exact executable**, not a real-device route snapshot or proof of R1's initiating cause.

## Exact executable audit

netd SHA efb13b1f3b33289d85d2091b5c1c2a07d82fce2ee0e0fd02e879dd7bd833dbaf contains .gnu_debugdata. Its embedded XZ-compressed ELF symbols decompress to SHA945c3431bd60515959d7f9e619661e519364cd3a2b3e80886d07a011a12b5906. Addresses/names therefore come from the exact artifact rather than assuming its source revision from the ROM date. Mac's bundled LLVM reads ELF and Thumb; no Debian compilation was needed.

Verified machine-code call chain: main(0x2c81c) -> Controllers::init(0x3b248) -> RouteController::Init(0x4b660). The latter calls rtNetlinkFlush(0x4c770) with GETRULE34/DELRULE33 and string rules. Its std::function vtable0x6d624 directly binds predicate0x4c3c8, which reads attribute6/FRA_PRIORITY and returns true iff nonzero. Original-byte Thumb branch decoding independently checks these edges. Thus priority0 is excluded from deletion; default main lookup32766 is eligible.

On the successful path after flushing, Init calls modifyIpRule(0x4c048) with NEWRULE32,priority32000,action7/FR_ACT_UNREACHABLE,table0 and no selectors. Pinned kernel headers at0da5107137f93b8d8f697e949ab0784f5ace450c establish these ABI constants. This is exact compiled behavior, conditional on runtime execution/success; the audit does not establish the actual RPDB at R1's20s boundary.

Reference only: [AOSP Android11 RouteController](https://android.googlesource.com/platform/system/netd/+/refs/tags/android-11.0.0_r48/server/RouteController.cpp) describes the corresponding flush/startup/fallback logic. The exact ROM netd source commit remains UNKNOWN; that reference is not silently labelled its build source. The accepted wrapper only configures usb0/NBD and adds no protected policy rule. M established that accepted power/gadget guards do not cover L3 policy. This is a concrete missing protection candidate consistent with the timing; it is not netd runtime causality proof.

Initial default LLVM disassembly used ARM decoding and misleading nearest dynamic-symbol headings. It was rejected before conclusions; only Thumb instruction ranges selected by embedded mini-debug symbols are evidence. The original executable bytes are unchanged. Evidence/report/symbols/selected disassembly/pinned ABI headers are in audits/2026-10-30-netd-policy/; full native tool outputs/executable stay in out/phase6-v2-netd-policy-N.

## Proposed next diagnostic, host work only

Create a separate P2-derived wrapper/image adding exactly one root-peer policy rule: priority0,to172.16.42.2/32,lookup main, before NBD attach. Require BusyBox command success and exact rule readback before attach; preserve accepted paths, kernel, USB/NBD attach/retry/handoff and all Android rc/services/SELinux. This deliberately adds the policy missing from the audited contract; it is an explicit diagnostic exception to the zero-new-lines wrapper, not a silent edit of the accepted wrapper or a redesign. Exact netd predicate explains why priority0 is the proposed survivor, while /32 limits scope to the dedicated root-storage host.

Use a fresh derivative disk byte-identical to R1's pre-run disk, not its runtime-written instance. Reuse accepted builders/image audits and prove the sole boot delta, deterministic output and current original/derived input identities. Kernel compilation is not selected. Runtime effect remains PROPOSED_DIAGNOSTIC/IMPLEMENTED_UNPROVEN; hardware PAUSED. Before any run, commit the exact binary question/inputs/outcomes and a bounded stall decision with a prepared actionable successor-capture route. No prolonged automatic-reboot waiting, disabling netd, Android bypass or undocumented boot is authorized.

## R1 timing clarification

User questioned whether the late panic could coincide with manual hard reboot. HOST_FACT: saved audit wall-time/uptime anchors extrapolate panic near08:28:50.8UTC, while the announcement was recorded08:33:22 and USB disappearance08:33:27. Extrapolation is an inference across clocks/timekeeping, not a timestamp of the physical keypress. The user cannot be expected to recall exact button times; no such recollection is a gate. Panic presence in the saved console is proven, but independence from manual action remains UNKNOWN. The long request-flow stall/failed startup validation was already established well before log retrieval and does not depend on that late panic. Do not use this clarification to restart passive waiting or treat the stalled startup as normal.
