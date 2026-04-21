#!/bin/bash
cd "$(dirname "$0")"
pkill -f "bin/daemon" 2>/dev/null || true
pkill -f "bin/generator" 2>/dev/null || true
rm -f logs/*.log
rm -f output/daemon.json 2>/dev/null || sudo rm -f output/daemon.json
echo "[]" > output/daemon.json
rm -f server_sids.json list.json
echo "✅ Cleaned all generated files (patterns preserved)"
