#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
TRANSPORT_INIT="$ROOT/initramfs/diskless-v2-transport-init"
FACT_REPORT="${FACT_REPORT:-$OUT/phase6-v2-frozen-facts.txt}"

EXPECTED_TRANSPORT_SHA256="6d99a16ab431cc3b980bf7244f4b85d2127b5d8ec1d57eeb4d106e3137a6fc87"
EXPECTED_TRANSPORT_INIT_GIT_BLOB="1e7e601fe1bd69b646cb49d68afc97a9b9fa0dd5"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in sha256sum grep git awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$TRANSPORT_BOOT" "$TRANSPORT_INIT" "$FACT_REPORT"; do
    [[ -f "$f" ]] || fail "required crash-capture input missing: $f"
done

grep -q '^DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS$' "$FACT_REPORT" || \
    fail "frozen-fact report is not PASS"

REPORT_TRANSPORT_SHA="$(awk -F= '/^transport_boot_sha256=/{print $2; exit}' "$FACT_REPORT")"
[[ "$REPORT_TRANSPORT_SHA" == "$EXPECTED_TRANSPORT_SHA256" ]] || \
    fail "frozen-fact transport sha mismatch: report=$REPORT_TRANSPORT_SHA expected=$EXPECTED_TRANSPORT_SHA256"

ACTUAL_TRANSPORT_SHA="$(sha256sum "$TRANSPORT_BOOT" | awk '{print $1}')"
[[ "$ACTUAL_TRANSPORT_SHA" == "$EXPECTED_TRANSPORT_SHA256" ]] || \
    fail "accepted transport image changed: actual=$ACTUAL_TRANSPORT_SHA expected=$EXPECTED_TRANSPORT_SHA256"

ACTUAL_INIT_BLOB="$(git hash-object "$TRANSPORT_INIT")"
[[ "$ACTUAL_INIT_BLOB" == "$EXPECTED_TRANSPORT_INIT_GIT_BLOB" ]] || \
    fail "accepted transport init changed: git-blob=$ACTUAL_INIT_BLOB expected=$EXPECTED_TRANSPORT_INIT_GIT_BLOB"

# Crash-capture contract: copy the previous persistent console before Android,
# then expose /www over the already-proven USB Ethernet path.
grep -Fq 'if [ -r /proc/last_kmsg ]; then' "$TRANSPORT_INIT" || \
    fail "transport init no longer checks /proc/last_kmsg"
grep -Fq '$BB cat /proc/last_kmsg > /www/last_kmsg.txt' "$TRANSPORT_INIT" || \
    fail "transport init no longer snapshots /proc/last_kmsg"
grep -Fq '$BB httpd -p 2325 -h /www' "$TRANSPORT_INIT" || \
    fail "transport init no longer exposes recovery files on HTTP 2325"

# Important ordering: the last_kmsg snapshot must precede usb0 wait/httpd and NBD attach.
LAST_KMSG_LINE="$(grep -n -F '$BB cat /proc/last_kmsg > /www/last_kmsg.txt' "$TRANSPORT_INIT" | head -n1 | cut -d: -f1)"
HTTP_LINE="$(grep -n -F '$BB httpd -p 2325 -h /www' "$TRANSPORT_INIT" | head -n1 | cut -d: -f1)"
NBD_LINE="$(grep -n -F 'start_nbd' "$TRANSPORT_INIT" | tail -n1 | cut -d: -f1)"
[[ "$LAST_KMSG_LINE" -lt "$HTTP_LINE" && "$LAST_KMSG_LINE" -lt "$NBD_LINE" ]] || \
    fail "last_kmsg snapshot ordering changed"

echo "DISKLESS_V2_PHASE6_V2_CRASH_CAPTURE_PREFLIGHT=PASS"
echo "transport_boot_sha256=$ACTUAL_TRANSPORT_SHA"
echo "transport_init_git_blob=$ACTUAL_INIT_BLOB"
echo "last_kmsg_snapshot=before-network-observation-and-nbd"
echo "recovery_http=http://172.16.42.1:2325"
echo "continuation_boot=forbidden-during-capture"
echo "nbd_server_required=no"
