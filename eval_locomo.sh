#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/eval_locomo_flat_memskill.sh" "$@"
