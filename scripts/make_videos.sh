#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
  echo "Usage: make_videos.sh manifest.json [--force]" >&2
  exit 2
fi
manifest=$1
shift
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$script_dir/make_videos.py" --manifest "$manifest" "$@"
