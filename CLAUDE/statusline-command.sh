#!/bin/sh
# Claude Code status line — mirrors a clean PowerShell-style prompt
# Input: JSON via stdin from Claude Code

input=$(cat)

# --- identity ---
user=$(whoami)
host=$(hostname -s)

# --- directory (prefer cwd from Claude's reported workspace) ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
if [ -z "$cwd" ]; then
  cwd=$(pwd)
fi
dir=$(basename "$cwd")

# --- git branch (non-blocking, skip optional locks) ---
branch=$(GIT_OPTIONAL_LOCKS=0 git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null)

# --- model ---
model=$(echo "$input" | jq -r '.model.display_name // empty')

# --- context window ---
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# --- assemble ---
# Base: user@host dir
line=$(printf '\033[32m%s@%s\033[0m \033[34m%s\033[0m' "$user" "$host" "$dir")

# Append git branch if available
if [ -n "$branch" ]; then
  line="$line $(printf '\033[33m(%s)\033[0m' "$branch")"
fi

# Append model if available
if [ -n "$model" ]; then
  line="$line $(printf '\033[36m[%s]\033[0m' "$model")"
fi

# Append context usage if available
if [ -n "$used" ]; then
  used_int=$(printf '%.0f' "$used")
  line="$line $(printf '\033[35mctx:%s%%\033[0m' "$used_int")"
fi

printf '%s' "$line"
