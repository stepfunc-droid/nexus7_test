# F6-017 — diagnostic host gate proved a write command, not the runtime sysctl state

Status: **RECORDED BEFORE ANY PANIC-HOLD HARDWARE RUN**.

## Symptom

The first `phase6_v2_panic_hold_host_gate.sh` design proved that a temporary wrapper changed exactly one source line from:

```text
echo 5 > /proc/sys/kernel/panic
```

to:

```text
echo 0 > /proc/sys/kernel/panic
```

and proved the resulting boot image was reproducible with accepted kernel/Android/fstab/BusyBox identities.

## Mistake

The gate treated the presence of the write command as though it proved the running kernel's `panic_timeout` actually became `0` before Android handoff.

The wrapper used a conditional writable check and did not read the sysctl back. Therefore an image-level host PASS could not independently establish the real-device runtime precondition on which the A/B interpretation depends.

## Impact

Had the image been booted and later rebooted, a negative result could have been misinterpreted even if the `panic=0` runtime write had never taken effect.

No panic-hold real-device run occurred, so no hardware conclusion was contaminated.

## Correction

The reset-classification design now requires fail-closed runtime verification before NBD attach:

```text
/proc/sys/kernel/panic writable
write 0 succeeds
read-back panic == 0
read-back panic_on_oops == 1
```

If any condition fails, the supervisor must not proceed into the NBD/Android test path.

A later host-visible NBD connection can therefore serve as evidence that these preconditions were passed earlier in the wrapper.

## Permanent rule

When an experiment's causal interpretation depends on a runtime knob, a host artifact check that merely proves a write command exists is insufficient. The diagnostic must either:

1. fail closed on same-run runtime read-back before reaching the observed test boundary; or
2. provide an independent same-run observation channel that proves the runtime value.

Precondition read-back is measurement/validation; it must not be confused with the experiment's causal variable.
