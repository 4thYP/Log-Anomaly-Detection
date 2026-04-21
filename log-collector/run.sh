#!/bin/bash

cd "$(dirname "$0")"

# Check if patterns exist
for server in healthcare linux windows zookeeper; do
    if [ ! -f "patterns/${server}_patterns.json" ]; then
        echo "❌ Missing pattern: patterns/${server}_patterns.json"
        exit 1
    fi
done

# Kill existing daemon and start fresh one
pkill -f "bin/daemon" 2>/dev/null
sleep 1

echo "🔄 Starting daemon..."
./bin/daemon &
sleep 2

echo "✅ Daemon is running!"
echo ""

# Run the interactive orchestrator
./bin/run
