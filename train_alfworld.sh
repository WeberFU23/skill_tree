#!/bin/bash
set -euo pipefail
exec bash "$(dirname "$0")/scripts/train_alfworld_flat_designer.sh" "$@"
