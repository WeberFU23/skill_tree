#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/sweep_locomo_skilltree_negmem_topk.sh" "$@"
