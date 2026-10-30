
# Phase6 diagnostic: preserve only the dedicated root-storage peer lookup.
require_applet ip
require_applet iprule
$BB ip rule add priority 0 to "$HOST/32" table main || fail "root-peer policy rule add failed"
ROOT_ROUTE_RULES="$($BB ip rule show 2>/dev/null)" || fail "root-peer policy rule readback failed"
echo "$ROOT_ROUTE_RULES" | $BB awk -v peer="$HOST" '
    $1 == "0:" {
        dst = 0; main = 0
        for (i = 2; i < NF; i++) {
            if ($i == "to" && ($(i + 1) == peer || $(i + 1) == peer "/32")) dst = 1
            if ($i == "lookup" && $(i + 1) == "main") main = 1
        }
        if (dst && main) found = 1
    }
    END { exit(found ? 0 : 1) }
' || fail "root-peer priority-0 main-table rule not confirmed"
echo "diskless-v2: root-peer rule ready pref=0 to=$HOST/32 lookup=main" > /dev/kmsg 2>/dev/null || true
