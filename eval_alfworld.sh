#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/eval_alfworld_flat_designer.sh" "$@"
