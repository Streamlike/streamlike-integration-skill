#!/usr/bin/env bash
# Downloads the public Streamlike OpenAPI descriptions next to this script.
#
#   ./fetch-openapi.sh            # both files into ./openapi/
#
# They are public, versioned with the platform, and authoritative: what they describe is what the
# production servers answer to. Re-run after a platform release.
set -euo pipefail

target="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/openapi"
mkdir -p "$target"

curl -fsSL "https://api.streamlike.com/openapi.json" -o "$target/api.json"
curl -fsSL "https://cdn.streamlike.com/openapi.json" -o "$target/ws.json"

for file in api ws; do
  version=$(python3 -c "import json;print(json.load(open('$target/$file.json'))['info']['version'])")
  paths=$(python3 -c "import json;print(len(json.load(open('$target/$file.json'))['paths']))")
  printf '%s: version %s, %s paths -> %s\n' "$file" "$version" "$paths" "$target/$file.json"
done
