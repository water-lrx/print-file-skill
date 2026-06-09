#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_src="$repo_dir/print-file"
skill_dst="$HOME/.codex/skills/print-file"

if [[ ! -f "$skill_src/SKILL.md" ]]; then
  echo "Missing $skill_src/SKILL.md" >&2
  exit 1
fi

mkdir -p "$HOME/.codex/skills"
config_backup=""
if [[ -d "$skill_dst/config" ]]; then
  config_backup="$(mktemp -d)"
  cp -R "$skill_dst/config" "$config_backup/config"
fi

rm -rf "$skill_dst"
cp -R "$skill_src" "$skill_dst"
rm -rf "$skill_dst/config"
if [[ -n "$config_backup" ]]; then
  cp -R "$config_backup/config" "$skill_dst/config"
  rm -rf "$config_backup"
fi
chmod +x "$skill_dst/scripts/print_file.py"

echo "Installed print-file skill to $skill_dst"
echo "Restart Codex to reload available skills."
