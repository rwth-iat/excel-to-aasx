#!/usr/bin/env bash
# Rebuild the vendored frontend libraries (ADR 0007). Needs Node/npm once; the app does not.
# Usage: tools/vendor.sh   (writes src/excel_to_aasx/adapters/web/static/vendor/)
set -euo pipefail

CODEMIRROR=6.0.2
CM_STATE=6.7.6
# 3.x is compiled from Ruby Asciidoctor, like the PDF build; 4.x is a rewrite.
ASCIIDOCTOR=3.0.4
ESBUILD=0.28.2

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/src/excel_to_aasx/adapters/web/static/vendor"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cd "$WORK"
npm init -y >/dev/null
# --ignore-scripts: no install hooks from third-party packages run on this machine.
npm install --ignore-scripts --no-audit --no-fund --save-exact \
  "codemirror@$CODEMIRROR" "@codemirror/state@$CM_STATE" \
  "@asciidoctor/core@$ASCIIDOCTOR" "esbuild@$ESBUILD" >/dev/null

cat > entry.js <<'JS'
export { basicSetup, EditorView } from "codemirror";
export { EditorState } from "@codemirror/state";
JS
mkdir -p "$OUT"
npx --no-install esbuild entry.js --bundle --format=esm --minify --legal-comments=eof \
  --outfile="$OUT/codemirror.js"
# The 3.x browser build is an ES module (export default); minify it as one.
npx --no-install esbuild node_modules/@asciidoctor/core/dist/browser/asciidoctor.js --format=esm --minify \
  --legal-comments=eof --outfile="$OUT/asciidoctor.js"
cp node_modules/@asciidoctor/core/LICENSE "$OUT/asciidoctor.LICENSE"
cp node_modules/codemirror/LICENSE "$OUT/codemirror.LICENSE"

cat > "$OUT/VERSIONS.txt" <<TXT
Built by tools/vendor.sh. Do not edit by hand.
codemirror $CODEMIRROR (@codemirror/state $CM_STATE), bundled with esbuild $ESBUILD
@asciidoctor/core $ASCIIDOCTOR (dist/browser/asciidoctor.js, minified with esbuild $ESBUILD)
TXT
ls -la "$OUT"
