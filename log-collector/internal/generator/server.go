package generator

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
  "strings"
	"sync"
	"time"

	"migrate/internal/models"
)

// Server interface defines the contract for all server types
type Server interface {
	GenerateLogLine() map[string]interface{}
	WriteLog(logData map[string]interface{})
	Run()
	GetSID() string
	GetLogFile() string
}

// BaseServer provides common functionality for all servers
type BaseServer struct {
	ServerType      string
	LogFile         string
	PatternsFile    string
	SID             string
	InstanceNum     string
	Patterns        models.PatternFile
	State           map[string]interface{}
	LogCount        int
	MaxLogs         int
	LastTimestamp   string
	TimestampCounter int
	QuietMode       bool
	mu              sync.RWMutex
}

// NewBaseServer creates a new base server
func NewBaseServer(serverType, logFile, patternsFile string) *BaseServer {
	instanceNum := os.Getenv("SERVER_INSTANCE")
	if instanceNum == "" {
		instanceNum = "1"
	}
	
	sid := os.Getenv("SERVER_SID")
	if sid == "" {
		sid = generateFallbackSID(serverType)
	}
	
	// Create instance-specific log file
	baseName := strings.TrimSuffix(logFile, "_server.log")
	if baseName == logFile {
		baseName = strings.ToLower(serverType)
	}
	
	instanceLogFile := filepath.Join("logs", fmt.Sprintf("%s_%s.log", baseName, instanceNum))
	
	bs := &BaseServer{
		ServerType:   serverType,
		LogFile:      instanceLogFile,
		PatternsFile: patternsFile,
		SID:          sid,
		InstanceNum:  instanceNum,
		State:        make(map[string]interface{}),
		LogCount:     0,
		MaxLogs:      20,
		QuietMode:    true,
	}
	
	// Create logs directory
	os.MkdirAll("logs", 0755)
	
	// Load patterns
	bs.loadPatterns()
	
	// Write SID to log file
	bs.writeSIDToLog()
	
	return bs
}

// generateFallbackSID creates a fallback SID
func generateFallbackSID(serverType string) string {
	return fmt.Sprintf("FALLBACK_%s_%d_%d", 
		strings.ToUpper(serverType), 
		time.Now().Unix(), 
		rand.Intn(10000))
}

// writeSIDToLog writes SID as first line
func (bs *BaseServer) writeSIDToLog() {
	file, err := os.Create(bs.LogFile)
	if err != nil {
		fmt.Printf("⚠️  Could not create log file: %v\n", err)
		return
	}
	defer file.Close()
	
	file.WriteString(fmt.Sprintf("# SID: %s\n", bs.SID))
}

// loadPatterns loads patterns from JSON file
func (bs *BaseServer) loadPatterns() {
	paths := []string{
		bs.PatternsFile,
		filepath.Join("patterns", bs.PatternsFile),
		filepath.Join("..", "patterns", bs.PatternsFile),
	}
	
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err == nil {
			if err := json.Unmarshal(data, &bs.Patterns); err == nil {
				fmt.Printf("   📂 Loaded patterns from: %s\n", path)
				return
			}
		}
	}
	
	fmt.Printf("⚠️  Patterns file not found. Using fallback patterns.\n")
	bs.Patterns = bs.getFallbackPatterns()
}

// getFallbackPatterns returns default patterns
func (bs *BaseServer) getFallbackPatterns() models.PatternFile {
	return models.PatternFile{
		Templates: models.Templates{
			ByFrequency:    make(map[string]int),
			TotalTemplates: 0,
		},
		Components: models.Components{
			ByFrequency:     make(map[string]int),
			TotalComponents: 0,
		},
	}
}

// GenerateTimestamp creates a timestamp for the log
func (bs *BaseServer) GenerateTimestamp() string {
	now := time.Now()
	var ts string
	
	switch bs.ServerType {
	case "healthcare":
		ts = now.Format("20060102-15:04:05") + fmt.Sprintf(":%03d", rand.Intn(1000))
	case "linux":
		ts = now.Format("Jan 02 15:04:05")
	case "windows":
		ts = now.Format("2006-01-02 15:04:05")
	case "zookeeper":
		ts = now.Format("2006-01-02 15:04:05") + fmt.Sprintf(",%03d", rand.Intn(1000))
	default:
		ts = now.Format(time.RFC3339)
	}
	
	// Ensure monotonic
	if bs.LastTimestamp != "" && ts <= bs.LastTimestamp {
		bs.TimestampCounter++
		ts = bs.incrementTimestamp(ts)
	}
	
	bs.LastTimestamp = ts
	return ts
}

// incrementTimestamp adds time to ensure monotonic behavior
func (bs *BaseServer) incrementTimestamp(ts string) string {
	// Simple implementation - add counter as milliseconds
	if bs.ServerType == "healthcare" || bs.ServerType == "zookeeper" {
		base := ts[:len(ts)-3]
		ms := (bs.TimestampCounter % 1000)
		return fmt.Sprintf("%s%03d", base, ms)
	}
	return ts
}

// GetRandomComponent returns a random component
func (bs *BaseServer) GetRandomComponent() string {
	components := bs.Patterns.Components.ByFrequency
	if len(components) > 0 {
		keys := make([]string, 0, len(components))
		for k := range components {
			keys = append(keys, k)
		}
		return keys[rand.Intn(len(keys))]
	}
	return fmt.Sprintf("%s_component", bs.ServerType)
}

// GetRandomTemplate returns a random template
func (bs *BaseServer) GetRandomTemplate() string {
	templates := bs.Patterns.Templates.ByFrequency
	if len(templates) > 0 {
		keys := make([]string, 0, len(templates))
		for k := range templates {
			keys = append(keys, k)
		}
		return keys[rand.Intn(len(keys))]
	}
	return fmt.Sprintf("%s log message", bs.ServerType)
}

// FillTemplate replaces <*> with realistic values
func (bs *BaseServer) FillTemplate(template string) string {
	for strings.Contains(template, "<*>") {
		value := rand.Intn(9999) + 1
		template = strings.Replace(template, "<*>", fmt.Sprintf("%d", value), 1)
	}
	return template
}

// WriteLog writes a log entry to file
func (bs *BaseServer) WriteLog(logData map[string]interface{}) {
	bs.mu.Lock()
	defer bs.mu.Unlock()
	
	if skip, ok := logData["skip"].(bool); ok && skip {
		return
	}
	
	timestamp, ok := logData["timestamp"].(string)
	if !ok || timestamp == "" {
		timestamp = bs.GenerateTimestamp()
	}
	
	component, _ := logData["component"].(string)
	message, _ := logData["message"].(string)
	
	var logLine string
	
	switch bs.ServerType {
	case "healthcare":
		userID, _ := logData["user_id"].(string)
		logLine = fmt.Sprintf("%s|%s|%s|%s", timestamp, component, userID, message)
	case "linux":
		process, _ := logData["process"].(string)
		if process != "" {
			logLine = fmt.Sprintf("%s %s %s: %s", timestamp, component, process, message)
		} else {
			logLine = fmt.Sprintf("%s %s: %s", timestamp, component, message)
		}
	case "windows":
		level, _ := logData["level"].(string)
		if level == "" {
			level = "Info"
		}
		logLine = fmt.Sprintf("%s, %s %s %s", timestamp, level, component, message)
	case "zookeeper":
		level, _ := logData["level"].(string)
		if level == "" {
			level = "INFO"
		}
		logLine = fmt.Sprintf("%s - %s [%s] - %s", timestamp, level, component, message)
	default:
		logLine = fmt.Sprintf("%s|%s|%s", timestamp, component, message)
	}
	
	file, err := os.OpenFile(bs.LogFile, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		fmt.Printf("⚠️  Error opening log file: %v\n", err)
		return
	}
	defer file.Close()
	
	file.WriteString(logLine + "\n")
	bs.LogCount++
}

// GetSID returns the server's SID
func (bs *BaseServer) GetSID() string {
	return bs.SID
}

// GetLogFile returns the log file path
func (bs *BaseServer) GetLogFile() string {
	return bs.LogFile
}

// Run is the main generation loop (to be overridden)
func (bs *BaseServer) Run() {
	for bs.LogCount < bs.MaxLogs {
		logData := bs.GenerateLogLine()
		bs.WriteLog(logData)
		time.Sleep(time.Duration(rand.Intn(1000)+500) * time.Millisecond)
	}
}

// GenerateLogLine generates a single log line (to be overridden)
func (bs *BaseServer) GenerateLogLine() map[string]interface{} {
	return map[string]interface{}{
		"timestamp": bs.GenerateTimestamp(),
		"component": bs.GetRandomComponent(),
		"message":   bs.FillTemplate(bs.GetRandomTemplate()),
	}
}
