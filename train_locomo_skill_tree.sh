#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/train_locomo_skilltree_negmem_autoevolve.sh" "$@"
