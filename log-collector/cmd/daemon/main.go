package main

import (
	"flag"
	"fmt"
	"log"
	"os"
  "strings"
	"os/signal"
	"syscall"

	"migrate/internal/daemon"
)

func main() {
	// Parse command line flags
	logDir := flag.String("dir", "logs", "Directory to watch for log files")
	outputFile := flag.String("output", "output/daemon.json", "Output JSON file")
	configFile := flag.String("config", "configs/daemon_config.json", "Daemon configuration file")
	maxEntries := flag.Int("max", 10000, "Maximum entries to keep in output file")
	flag.Parse()

	fmt.Println("=" + strings.Repeat("=", 60))
	fmt.Println("🔄 LOG INTELLIGENCE SYSTEM - DAEMON")
	fmt.Println("=" + strings.Repeat("=", 60))
	fmt.Printf("📁 Watching directory: %s\n", *logDir)
	fmt.Printf("📄 Output file: %s\n", *outputFile)
	fmt.Printf("⚙️  Config file: %s\n", *configFile)
	fmt.Printf("📊 Max entries: %d\n", *maxEntries)
	fmt.Println("=" + strings.Repeat("=", 60))

	// Create log directory if it doesn't exist
	if err := os.MkdirAll(*logDir, 0755); err != nil {
		log.Fatalf("❌ Error creating log directory: %v", err)
	}

	// Load server mapping
	serverMap, err := daemon.LoadServerMap(*configFile)
	if err != nil {
		log.Printf("⚠️  Error loading server map: %v", err)
		log.Println("   Using default mapping")
	}

	fmt.Printf("\n📋 Loaded %d server mappings\n", len(serverMap))
	for pattern, serverID := range serverMap {
		fmt.Printf("   • %s -> %s\n", pattern, serverID)
	}

	// Create parser and aggregator
	parser := daemon.NewLogParser(serverMap)
	aggregator := daemon.NewAggregator(*outputFile, *maxEntries)

	// Create file watcher
	watcher, err := daemon.NewFileWatcher(*logDir, parser, aggregator)
	if err != nil {
		log.Fatalf("❌ Error creating file watcher: %v", err)
	}

	// Process existing files first
	fmt.Println("\n📂 Scanning existing log files...")
	watcher.ProcessExistingFiles(*logDir)

	// Start watching
	fmt.Println("\n👁️  Starting file watcher...")
	watcher.Start()

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	fmt.Println("\n✅ Daemon is running!")
	fmt.Println("📝 Watching for new log entries...")
	fmt.Println("🛑 Press Ctrl+C to stop\n")

	<-sigChan

	fmt.Println("\n\n🛑 Shutting down daemon...")
	watcher.Stop()

	// Final stats
	fmt.Printf("\n📊 Final statistics:")
	fmt.Printf("\n   • Total entries processed: %d", aggregator.Count())
	fmt.Printf("\n   • Output file: %s", *outputFile)
	fmt.Println("\n\n✅ Daemon stopped gracefully")
}
