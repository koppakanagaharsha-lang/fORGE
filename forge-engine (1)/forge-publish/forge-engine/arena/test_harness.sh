#!/usr/bin/env bash
# FORGE Arena — Test Harness
# Usage: test_harness.sh [original_dir] [fork_dir] [timestamp]

set -euo pipefail

ORIGINAL="${1:-$HOME/.forge/engine}"
FORK="${2:-}"
TIMESTAMP="${3:-$(date +%s)}"
FORGE_DIR="$HOME/.forge"
RESULTS_DIR="$FORGE_DIR/arena/results"
TASKS_FILE="$FORGE_DIR/engine/arena/task_suite.json"

mkdir -p "$RESULTS_DIR"

[ -z "$FORK" ] && { echo "Usage: test_harness.sh original fork timestamp"; exit 1; }

source "$FORGE_DIR/.env" 2>/dev/null || true

run_suite() {
  local engine_dir="$1"
  local label="$2"
  local result_file="$RESULTS_DIR/${label}_${TIMESTAMP}.json"

  local total=0 errors=0 total_time=0 quality_sum=0

  local arena_req="${ARENA_REQUEST:-}"
  if [ -n "$arena_req" ]; then
    python3 "$FORGE_DIR/engine/arena/builder.py" "$arena_req"
  fi

  if [ ! -f "$TASKS_FILE" ]; then
    # Create minimal test suite if missing
    cat > "$TASKS_FILE" << 'EOF'
[
  {"id": "t1", "type": "python_function",
   "prompt": "Write a Python function that returns the nth Fibonacci number",
   "expect_contains": ["def ", "return"]},
  {"id": "t2", "type": "shell_script",
   "prompt": "Write a bash script that counts files in a directory",
   "expect_contains": ["#!/", "find", "wc"]},
  {"id": "t3", "type": "javascript",
   "prompt": "Write a JavaScript function that debounces another function",
   "expect_contains": ["function", "setTimeout", "clearTimeout"]},
  {"id": "t4", "type": "python_class",
   "prompt": "Write a Python class for a simple key-value cache with TTL",
   "expect_contains": ["class", "def get", "def set"]},
  {"id": "t5", "type": "readme",
   "prompt": "Write a README for a CLI tool that converts JSON to YAML",
   "expect_contains": ["#", "install", "usage"]}
]
EOF
  fi

  # Run each task
  while IFS= read -r task; do
    local task_id=$(echo "$task" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    local prompt=$(echo "$task" | python3 -c "import sys,json; print(json.load(sys.stdin)['prompt'])")
    local expects=$(echo "$task" | python3 -c "import sys,json; print(' '.join(json.load(sys.stdin).get('expect_contains',[])))")

    local start_time=$(date +%s%N)
    local output=""
    local task_errors=0

    # Invoke cortex from this engine
    output=$(timeout 60 \
      FORGE_DIR="$FORGE_DIR" \
      bash "$engine_dir/cortex/invoke.sh" \
      --task "$prompt" 2>/dev/null || echo "")

    local end_time=$(date +%s%N)
    local elapsed=$(( (end_time - start_time) / 1000000 ))  # ms

    # Score quality: check expected strings present
    local task_quality=0
    local expect_count=0
    for expect in $expects; do
      expect_count=$((expect_count + 1))
      echo "$output" | grep -qi "$expect" && \
        task_quality=$((task_quality + 1)) || \
        task_errors=$((task_errors + 1))
    done

    local quality_score=5
    [ $expect_count -gt 0 ] && \
      quality_score=$(python3 -c "print(round(($task_quality/$expect_count)*10, 1))")

    total=$((total + 1))
    errors=$((errors + task_errors))
    total_time=$((total_time + elapsed))
    quality_sum=$(python3 -c "print($quality_sum + $quality_score)")

  done < <(python3 -c "import json,sys; [print(json.dumps(t)) for t in json.load(open('$TASKS_FILE'))]")

  local avg_time=$(python3 -c "print(round($total_time / max($total,1) / 1000, 2))")  # seconds
  local avg_quality=$(python3 -c "print(round($quality_sum / max($total,1), 2))")
  local error_rate=$(python3 -c "print(round($errors / max($total*5,1), 3))")

  python3 -c "
import json
result = {
  'label': '$label',
  'timestamp': '$TIMESTAMP',
  'total_tasks': $total,
  'total_errors': $errors,
  'avg_task_seconds': $avg_time,
  'quality_score': $avg_quality,
  'error_rate': $error_rate
}
with open('$result_file', 'w') as f:
    json.dump(result, f, indent=2)
print(f'Results: {result_file}')
print(json.dumps(result, indent=2))
"
}

echo "Running original suite..."
run_suite "$ORIGINAL" "original"

echo "Running fork suite..."
run_suite "$FORK" "fork"

# Deploy if successful
if jq -e '.error_rate == 0' "$RESULTS_DIR/fork_${TIMESTAMP}.json" >/dev/null 2>&1; then
  echo "Arena tests passed flawlessly. Deploying fork to production!"
  rsync -av --delete "$FORK/" "$ORIGINAL/"
  echo "Deployment complete."
else
  echo "Arena tests did not pass perfectly. Skipping deployment."
fi

echo "Test harness complete."
