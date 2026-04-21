package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"migrate/internal/learner"
	"migrate/internal/models"
)

func main() {
	serverType := flag.String("server", "healthcare", "Server type to learn patterns for")
	maxLines := flag.Int("max", 10000, "Maximum lines to read")
	flag.Parse()

	fmt.Println(strings.Repeat("=", 60))
	fmt.Printf("🎯 LEARNING PATTERNS FOR: %s\n", strings.ToUpper(*serverType))
	fmt.Println(strings.Repeat("=", 60))

	// Find log file
	logFile := findLogFile(*serverType)
	if logFile == "" {
		fmt.Printf("\n❌ No .log file found for %s\n", *serverType)
		fmt.Printf("📁 Please place your log file in: datasets/%s/\n", *serverType)
		return
	}

	fmt.Printf("\n📖 Reading logs from: %s\n", logFile)

	// Read logs
	logs := readLogs(logFile, *serverType, *maxLines)
	if len(logs) == 0 {
		fmt.Println("❌ No logs to analyze")
		return
	}

	fmt.Printf("\n📊 Analyzed %d log lines\n", len(logs))

	// Initialize patterns
	patterns := models.PatternFile{
		Server: *serverType,
	}

	// Step 1: Extract templates and components
	fmt.Println("\n🔍 Step 1/6: Extracting templates and components...")
	templateExtractor := learner.NewTemplateExtractor()
	patterns.Templates, patterns.Components = templateExtractor.Extract(logs)
	fmt.Printf("   ✅ Found %d unique templates\n", patterns.Templates.TotalTemplates)
	fmt.Printf("   ✅ Found %d unique components\n", patterns.Components.TotalComponents)

	// Step 2: Extract state machine
	fmt.Println("\n🔍 Step 2/6: Extracting state machine...")
	stateExtractor := learner.NewStateMachineExtractor()
	patterns.StateMachine = stateExtractor.Extract(logs)
	fmt.Printf("   ✅ Found %d state variables\n", len(patterns.StateMachine.Counters))

	// Step 3: Extract causal chains
	fmt.Println("\n🔍 Step 3/6: Extracting causal chains...")
	causalExtractor := learner.NewCausalChainExtractor()
	patterns.CausalChains = causalExtractor.Extract(logs)
	fmt.Printf("   ✅ Found %d causal chains\n", patterns.CausalChains.TotalChains)

	// Step 4: Extract value relationships
	fmt.Println("\n🔍 Step 4/6: Extracting value relationships...")
	valueExtractor := learner.NewValueRelationshipExtractor()
	patterns.ValueRelationships = valueExtractor.Extract(logs)
	fmt.Printf("   ✅ Found %d value correlations\n", len(patterns.ValueRelationships.Correlations))

	// Step 5: Extract temporal patterns
	fmt.Println("\n🔍 Step 5/6: Extracting temporal patterns...")
	temporalExtractor := learner.NewTemporalExtractor()
	patterns.TemporalPatterns = temporalExtractor.Extract(logs)
	fmt.Printf("   ✅ Found %d periodic events\n", len(patterns.TemporalPatterns.PeriodicEvents))

	// Step 6: Calculate statistics
	fmt.Println("\n🔍 Step 6/6: Calculating statistics...")
	patterns.Statistics = calculateStatistics(logs, patterns)

	// Save patterns
	savePatterns(patterns, *serverType)

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("✅ LEARNING COMPLETE!")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Printf("📁 Patterns saved to: patterns/%s_patterns.json\n", *serverType)
}

func findLogFile(serverType string) string {
	datasetPath := filepath.Join("datasets", serverType)
	
	if _, err := os.Stat(datasetPath); os.IsNotExist(err) {
		return ""
	}
	
	files, _ := os.ReadDir(datasetPath)
	for _, file := range files {
		if strings.HasSuffix(file.Name(), ".log") {
			return filepath.Join(datasetPath, file.Name())
		}
	}
	
	return ""
}

func readLogs(logFile, serverType string, maxLines int) []models.LogEntry {
	config := loadConfig(serverType)
	parser := learner.NewLogParser(serverType, config)
	
	file, err := os.Open(logFile)
	if err != nil {
		fmt.Printf("❌ Error opening file: %v\n", err)
		return nil
	}
	defer file.Close()
	
	logs := make([]models.LogEntry, 0)
	scanner := bufio.NewScanner(file)
	
	lineCount := 0
	for scanner.Scan() && lineCount < maxLines {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		
		entry := parser.Parse(line)
		if entry != nil {
			logs = append(logs, *entry)
			lineCount++
		}
		
		// Show progress every 500 lines
		if lineCount%500 == 0 {
			fmt.Printf("   📖 Read %d lines...\n", lineCount)
		}
	}
	
	if err := scanner.Err(); err != nil {
		fmt.Printf("❌ Error reading file: %v\n", err)
	}
	
	fmt.Printf("   ✅ Successfully parsed %d log lines\n", len(logs))
	return logs
}

func loadConfig(serverType string) models.ServerConfig {
	configs := map[string]models.ServerConfig{
		"healthcare": {
			Server: "healthcare",
			LogFormat: models.LogFormat{
				Delimiter:       "|",
				Parts:           []string{"timestamp", "component", "user_id", "message"},
				TimestampFormat: "20060102-15:04:05",
			},
		},
		"linux": {
			Server: "linux",
			LogFormat: models.LogFormat{
				Delimiter:       " ",
				Parts:           []string{"timestamp", "hostname", "process", "message"},
				TimestampFormat: "Jan 2 15:04:05",
			},
		},
		"windows": {
			Server: "windows",
			LogFormat: models.LogFormat{
				Delimiter:       " ",
				Parts:           []string{"timestamp", "level", "component", "message"},
				TimestampFormat: "2006-01-02 15:04:05",
			},
		},
		"zookeeper": {
			Server: "zookeeper",
			LogFormat: models.LogFormat{
				Delimiter:       " - ",
				Parts:           []string{"timestamp", "level", "component", "message"},
				TimestampFormat: "2006-01-02 15:04:05",
			},
		},
	}
	
	if config, exists := configs[serverType]; exists {
		return config
	}
	return configs["healthcare"]
}

func calculateStatistics(logs []models.LogEntry, patterns models.PatternFile) models.Statistics {
	stats := models.Statistics{
		TotalLogs:        len(logs),
		UniqueComponents: patterns.Components.TotalComponents,
		UniqueTemplates:  patterns.Templates.TotalTemplates,
		AvgLogsPerMinute: "N/A",
	}
	
	if len(logs) >= 2 {
		first := logs[0]
		last := logs[len(logs)-1]
		
		if !first.Timestamp.IsZero() && !last.Timestamp.IsZero() {
			stats.TimeSpan = map[string]string{
				"first": first.Timestamp.Format(time.RFC3339),
				"last":  last.Timestamp.Format(time.RFC3339),
			}
		}
	}
	
	return stats
}

func savePatterns(patterns models.PatternFile, serverType string) {
	os.MkdirAll("patterns", 0755)
	
	outputPath := filepath.Join("patterns", serverType+"_patterns.json")
	
	data, err := json.MarshalIndent(patterns, "", "  ")
	if err != nil {
		fmt.Printf("❌ Error marshaling patterns: %v\n", err)
		return
	}
	
	if err := os.WriteFile(outputPath, data, 0644); err != nil {
		fmt.Printf("❌ Error saving patterns: %v\n", err)
		return
	}
	
	fmt.Printf("\n💾 Successfully saved patterns to: %s\n", outputPath)
}
