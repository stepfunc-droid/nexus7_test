#!/usr/bin/env bash
set -u

IFACE="${IFACE:-en6}"
HOST="${HOST:-172.16.42.1}"
PORT_RE='10810|10811|10812|10813|10814|10999|11000'

echo "=== nexus7 diskless stall diagnostic ==="
date
printf '\n=== interface: %s ===\n' "$IFACE"
ifconfig "$IFACE" 2>&1 || true

printf '\n=== route to %s ===\n' "$HOST"
route -n get "$HOST" 2>&1 || true

printf '\n=== arp ===\n'
arp -an 2>&1 | grep -F "$HOST" || true

printf '\n=== relevant TCP sockets (lsof) ===\n'
lsof -nP -iTCP 2>/dev/null | grep -E "$PORT_RE" || true

printf '\n=== relevant TCP sockets (netstat) ===\n'
netstat -anv -p tcp 2>/dev/null | grep -E '\.(10810|10811|10812|10813|10814|10999|11000)[[:space:]]' || true

printf '\n=== reachability ===\n'
ping -c 3 -W 1000 "$HOST" 2>&1 || true

printf '\n=== interface counters sample 1 ===\n'
netstat -ibn 2>/dev/null | awk -v i="$IFACE" '$1==i {print}' || true
sleep 2
printf '\n=== interface counters sample 2 (2s later) ===\n'
netstat -ibn 2>/dev/null | awk -v i="$IFACE" '$1==i {print}' || true

printf '\n=== quick interpretation ===\n'
EST=$(lsof -nP -iTCP 2>/dev/null | grep -E '10810|10811|10812|10813|10814' | grep -c ESTABLISHED || true)
KMSG=$(lsof -nP -iTCP 2>/dev/null | grep '11000' | grep -c ESTABLISHED || true)
LINK=$(ifconfig "$IFACE" 2>/dev/null | grep -c 'status: active' || true)
IP=$(ifconfig "$IFACE" 2>/dev/null | grep -c 'inet 172\.16\.42\.2 ' || true)

echo "NBD established sockets: $EST / 5"
echo "kmsg established socket:  $KMSG / 1"
echo "interface active:          $LINK"
echo "172.16.42.2 present:       $IP"

if [ "$EST" -eq 5 ] && [ "$KMSG" -eq 0 ]; then
    echo "RESULT: NBD transport still appears alive; the kmsg streamer likely died independently."
elif [ "$EST" -lt 5 ]; then
    echo "RESULT: one or more NBD transports are gone/stale; investigate USB/TCP/NBD rather than Android init ordering."
elif [ "$LINK" -eq 0 ] || [ "$IP" -eq 0 ]; then
    echo "RESULT: Mac-side USB network state is broken or reconfigured."
else
    echo "RESULT: transport state is ambiguous; use the raw sections above."
fi
