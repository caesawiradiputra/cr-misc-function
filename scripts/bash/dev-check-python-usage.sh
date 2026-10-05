#!/usr/bin/env bash
# List running python processes that are actually burning CPU, busiest first
# (top 5). Bash port of dev-check_python_usage.ps1 (PowerShell), which does
# the equivalent via Get-Process python | Where CPU -gt 0.
set -euo pipefail

{
    printf '%-8s %-6s %-10s %-10s %s\n' "PID" "CPU%" "RSS(KB)" "RUNTIME(s)" "COMMAND"
    ps -eo pid,pcpu,rss,etimes,comm --sort=-pcpu \
        | awk 'NR>1 && $5 ~ /python/ && $2+0 > 0' \
        | head -n 5 \
        | awk '{printf "%-8s %-6s %-10s %-10s %s\n", $1, $2, $3, $4, $5}'
}
