#!/usr/bin/env bash
# Deploy ContractLens to a Hugging Face Docker Space. Needs HF_TOKEN and HF_USERNAME in ~/.config/swarm/secrets.env.
set -euo pipefail
set -a; source ~/.config/swarm/secrets.env; set +a
SPACE=${SPACE:-contractlens}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
curl -sf -X POST https://huggingface.co/api/repos/create -H "Authorization: Bearer $HF_TOKEN" -H 'content-type: application/json' \
  -d "{\"type\":\"space\",\"name\":\"$SPACE\",\"sdk\":\"docker\",\"private\":false}" >/dev/null || echo "space may already exist"
TMP=$(mktemp -d)
git clone -q "https://$HF_USERNAME:$HF_TOKEN@huggingface.co/spaces/$HF_USERNAME/$SPACE" "$TMP/space"
mkdir -p "$TMP/space/server"
cp "$ROOT/deploy/hf/Dockerfile" "$TMP/space/Dockerfile"
cp "$ROOT/deploy/hf/README.md" "$TMP/space/README.md"
cp "$ROOT/server/"{server.mjs,scanner.py,sample-report.json,package.json,package-lock.json} "$TMP/space/server/"
cd "$TMP/space" && git add -A && git -c user.email=megafi.app1+contractlens@gmail.com -c user.name=ContractLens commit -qm "deploy" && git push -q
echo "https://${HF_USERNAME//_/-}-${SPACE}.hf.space"
rm -rf "$TMP"
