# Phase7 M1 — user-operated GApps startup

Status: READY FOR USER / NOT EXECUTED BY AGENT. User explicitly requested to perform the first GApps startup manually after host preparation. U must close/commit full host evidence first. No agent-issued Nexus transition/boot is authorized by this plan.

Current public entrypoints: ./stop-nbd.sh (after verified fastboot), ./start-nbd.sh (terminal one), ./start-nexus7.sh (terminal two). All require no arguments and call the documented existing guarded operations using absolute paths. The Python-command sequence below describes their internal behavior. Both release directories now provide the same three entrypoints.

Binary question: does the host-audited GApps Pico derivative reach Google setup/desktop and permit opening Play Store without observed crash on this diskless runtime? Sole runtime input change from clean Q2 is the GApps p1 installation profile; initial writable partitions, GPS-null vendor, exact boot/kernel/peer route/root-fstab, transport/handoff and enforcing policy remain fixed. Skipswypelibs omits optional gesture libraries; stock keyboard remains.

```text
Mac=/Users/zhangjw/nexus7/releases/20261030-gapps-pico
boot_sha256=50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799
lk2nd_sha256=a76f4e138e5eaf5fa902bbee97604e7f5a06830c0f2028a3829c5b2985860c3a
system_sha256=98e58fa4070666b4f1ff5ab7d8c15617bf1237fa4e0c0f3cee617031a4d62401
clean_disk_sha256=70e4caad543835d0f9f61de64de1f22265bedbc9365ccfdfc7f89b72340832f9
vendor_sha256=7218d1ba6808fe45398cc096356303ea3f59833866c1cababb8aa670f5f6d996
GApps_ZIP_sha256=4df52af6b0dcc0f21d6e1dd943ef3088121354179782b9d0d48593ff127b4cc0
serial=07a117ae;USB_location336789504;bind172.16.42.2:10810
working_disk=disks/daily.raw.img (fresh APFS clone of checked clean master)
```

Host prerequisites: original installer G exit0/UI completion, exact ZIP/base hashes, H target metadata restoration, independent34-file/20-directory/1-symlink metadata and target-resolution gates, protected files/root-fstab unchanged, e2fsck0, whole composed disk outside p1 byte-identical to Q2, immutable bundle hash verification. Mac endpoint parser demonstrated correct current physical gadget/dedicated172.16.42.2/24. Guard tests reject master export, boot without armed serve, and stopping live gadget root; original service preserved. New launcher behavior remains IMPLEMENTED_UNPROVEN on hardware.

User sequence: manually enter stock fastboot first. On the Mac run nexus7.py stop-nbd; it verifies same physical fastboot/product before stopping only the recognized old USB-only NBD process. Run nexus7.py serve disks/daily.raw.img and keep that terminal open. It requires no10810 listener, verifies assets, arms USB observer before accepting boot, then waits up to180s for correct gadget/dedicated endpoint and launches exact server with5s stats and idle-sleep guard. In another Mac terminal run nexus7.py boot: one pinned lk2nd RAM boot from stock flo/18d1:4ee0, verify lk2nd-msm8960/18d1:d00d/serial/location, then one exact boot.img RAM boot. No flash/erase/automatic retry. Exact commands are in packaged README; explicit fastboot commands are an alternative, not an additional boot sequence. Archive terminal output if choosing direct commands instead of journaled helper.

Observe first attach within120s; before any UI,60s without completed replies or no initial UI/progress by300s means pause failed-start validation and preserve evidence, not unbounded waiting or cause inference. Continuing interactive Google setup with new I/O is normal active use, not a failed-start wait. YES requires user's direct same-run setup/desktop/Play evidence corroborated by USB continuity/one active NBD session. Earlier unrelated failure, extra boot/session, missing continuity/provenance, inability to reach setup, or unresolved normal-idle distinction is INCONCLUSIVE; captured actual errors may establish a narrower NO. No GSS/internal cause inference from host timeout.

Any failed identity/precondition stops before next command. No repeated boot to manufacture evidence. Keep root export while Linux may depend on it; shutdown/verified fastboot required before stopping. USB observation900s cap does not stop NBD. Preserve runs/{usb.jsonl,boot-commands.jsonl,stats.jsonl,trace.jsonl,server.log,*.pid}, release manifest, user outcomes and written working disk. Do not commit private data. After the user's attempt, close a separate M1 evidence batch before any further experiment. Current agent U delivers artifacts/instructions only; Q2 remains live until user transitions it.
