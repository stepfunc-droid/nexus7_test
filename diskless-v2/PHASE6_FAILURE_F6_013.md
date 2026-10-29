# F6-013 — userdata block evidence was overinterpreted as a hard late-fs proof

Status: **RECORDED BEFORE 6V2-D HARDWARE RUN**.

## Symptom / proposed interpretation

The first Audit-V2 partition-stage design labeled p5 userdata as:

```text
second-stage-late-fs
```

and the initial real-trace classifier was prepared to emit a hard late-fs PASS when userdata ext4 superblock + primary-GDT reads were observed.

## Mistake

The fstab `latemount` flag was treated as though every possible userdata block access must originate from `mount_all --late`.

That is stronger than the source supports.

## Source reason

Pinned root `init.rc` starts `vold` in `early-fs`, before the later `late-fs` trigger. Once second-stage is running, vold may therefore inspect userdata before `mount_all --late` executes.

Consequently:

```text
p5 filesystem I/O
!=
proof that late-fs has been reached
```

## Correction

Before the first Audit-V2 hardware run:

- the real-trace gate was changed not to emit a late-fs PASS from p5;
- userdata evidence is reported only as `OBSERVED` / `NOT_OBSERVED`;
- the classifier always emits `late_fs_claim=NOT_PROVEN` for p5-only evidence;
- 6V2-E acceptance remains based on cache/persist filesystem evidence, whose important causal property is that those partitions are excluded from first-stage and from the continuation supervisor's content I/O.

## Permanent rule

A partition's fstab mount class does not prove that every block access to that partition originates from the corresponding `mount_all` call. Service startup order and other users of the block device must be audited before turning block I/O into a stage-specific acceptance marker.
