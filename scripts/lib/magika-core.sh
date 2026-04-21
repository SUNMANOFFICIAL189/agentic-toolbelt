#!/usr/bin/env bash
# Layer 1 — Magika file-type integrity scan
# Detects extension-spoofed payloads and hidden binaries in external code.
# Catches ~20% of threat surface; paired with other layers for defence-in-depth.
#
# Usage: magika_scan <directory>
# Returns: 0 = pass, 1 = hard fail (type mismatch), 2 = warnings only
# Writes: structured JSON report to $TRUST_GATE_TMP/magika.json

set -euo pipefail

: "${TRUST_GATE_TMP:=/tmp/trust-gate-$$}"
mkdir -p "$TRUST_GATE_TMP"

magika_scan() {
  local target="$1"

  if [[ ! -d "$target" && ! -f "$target" ]]; then
    echo "magika_scan: target not found: $target" >&2
    return 1
  fi

  if ! command -v magika >/dev/null 2>&1; then
    echo "magika_scan: magika CLI not installed — cannot proceed" >&2
    return 1
  fi

  local report="$TRUST_GATE_TMP/magika.json"
  local summary="$TRUST_GATE_TMP/magika-summary.txt"

  # Run recursive scan, JSON output
  magika -r --json "$target" > "$report" 2>/dev/null || {
    echo "magika_scan: scan failed on $target" >&2
    return 1
  }

  # Extension vs detected-type mismatch heuristic
  # High-risk mismatches: extension says text/md/yaml/json but detected as executable/binary/script
  local mismatches
  mismatches=$(python3 - "$report" <<'PY'
import json, sys, os
report_path = sys.argv[1]
with open(report_path) as f:
    data = json.load(f)

# Magika 1.x returns a list of results, each with path and result.label
suspicious_exts = {'.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.html', '.pdf',
                   '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.wav', '.mp3'}
dangerous_labels = {'shell', 'bash', 'python', 'javascript', 'elf', 'macho', 'pebin',
                    'wasm', 'javabytecode', 'perl', 'ruby', 'lua', 'batch', 'powershell'}

mismatches = []
results = data if isinstance(data, list) else [data]
for entry in results:
    path = entry.get('path') or ''
    res = entry.get('result') or {}
    value = res.get('value') or {}
    out = value.get('output') or {}
    label = (out.get('label') or '').lower()
    score = out.get('score') or 0.0
    ext = os.path.splitext(path)[1].lower()
    if ext in suspicious_exts and label in dangerous_labels and score >= 0.5:
        mismatches.append({'path': path, 'ext': ext, 'detected': label, 'score': score})

print(json.dumps(mismatches))
PY
)

  local mismatch_count
  mismatch_count=$(echo "$mismatches" | python3 -c 'import json,sys; print(len(json.loads(sys.stdin.read())))')

  {
    echo "=== Magika scan: $target ==="
    echo "Mismatches (ext ≠ detected type): $mismatch_count"
    if [[ "$mismatch_count" -gt 0 ]]; then
      echo "$mismatches" | python3 -m json.tool
    fi
  } > "$summary"

  if [[ "$mismatch_count" -gt 0 ]]; then
    echo "magika_scan: HARD FAIL — $mismatch_count extension-spoofing mismatches in $target" >&2
    cat "$summary" >&2
    return 1
  fi

  echo "magika_scan: PASS — no extension-spoofing detected in $target" >&2
  return 0
}
