#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/eval_longmemeval_flat_designer.sh" "$@"
