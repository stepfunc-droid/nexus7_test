# Coordinator and remote Mac execution workflow

Established by user instruction on 2026-10-30. This is an operational host map, not new boot authorization. `AGENTS.md`, `DISKLESS_V2_EXECUTION.md` and `PROGRESS.md` retain their authority.

## Roles and paths

| Role | Location |
| --- | --- |
| Coordinator/editor | Current Codex machine |
| Mac build, host-gate and device execution | `ssh zhangjw@192.168.1.63` |
| Remote repository | `/Users/zhangjw/nexus7_test` |
| Coordinator view of repository | `/Volumes/zhangjw/nexus7_test` (SMB mount) |
| Accepted system candidate | `/Users/zhangjw/system.raw.img` |
| Original vendor candidate | `/Users/zhangjw/vendor.raw.img` |
| Partitioned disk candidate | `/Users/zhangjw/nexus7-diskless-v2/diskless-v2-android.raw.img` |
| Disk manifest candidate | Same disk path plus `.manifest.json` |

`HOST_FACT`: the coordinator's volume is an SMB mount of the Mac mini user share; the remote repository is on the Mac's local APFS data volume. Both views reported branch `diskless-v2`, HEAD `2c9333add5453be9101952de116d5a7d86c8fc24`, identical relevant script/image hashes and the same untracked output set. Treat these as a shared working tree. Do not run competing builds from both views.

After the remote documentation commit, coordinator-side `git status` first showed stale/inconsistent staged changes and then failed reading the index; remote Git still reported only the original untracked outputs. Evidence class: `HOST_FACT` for the differing observations; the filesystem/cache failure mechanism remains `UNKNOWN` (F6-019). Run Git inspection, staging and commits through SSH on the Mac. Do not rewrite/reset the shared index to repair a coordinator-only observation.

User instruction: perform Mac builds and full host validation remotely. Use SCP for changes/snapshots that need independent transfer, verify destination hashes, and retain exact source/commit identities in reports. A coordinator-side path is not the path to pass to a remote process. Use the remote `$HOME` paths above, then validate accepted byte identities; presence alone is insufficient.

No Debian host is designated. If a task requires Debian compilation, report that need to the user before relying on such an environment. This inspection did not compile anything and did not establish a complete cross-compilation toolchain.

## Observed host environment

`HOST_FACT`, read through SSH:

```text
OS=macOS 13.7.8 (22H730)
architecture=x86_64
user=zhangjw
git=/usr/local/bin/git
python3=/usr/local/bin/python3
fastboot=/usr/local/bin/fastboot
sha256sum=/usr/local/bin/sha256sum
scp=/usr/bin/scp
```

The tools were resolved through a remote login shell. Non-login SSH command environments may have a different PATH.

## Device observation and limits

Read-only queries on the remote Mac returned:

```text
fastboot devices -l: 07a117ae fastboot usb:336789504X
fastboot -s 07a117ae getvar product: flo
fastboot -s 07a117ae getvar version-bootloader: FLO-04.08
```

Evidence class: `REAL_DEVICE_FACT` for the bootloader response at inspection time. This says nothing about diagnostic boot execution or Android progress. No boot, flash, reboot, erase, NBD service start or device-state transition was requested during this batch. Repeat enumeration before a later separately authorized device action; a USB location is not a permanent identity.

## Artifact inspection scope

Remote continuation image SHA256 matched `0df5d3197661b032743b3804d4a2372dd12c152a2872fc860c35d7788f03e780`; panic-hold image matched `09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491`. The existing panic-hold host report matched `2d8104f8f8381a648a317343a2cc019e304330bab388fadeba64181b220795b6`.

System/vendor/disk candidates and the disk manifest exist at their expected remote default paths. Their full identities were not reread in this host-mapping batch. Full frozen-fact validation, F6-018 repair and complete current-input preflight remain pending. Hardware experiments remain paused.
