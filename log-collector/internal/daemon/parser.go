package daemon

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"

	"migrate/internal/models"
)

// LogParser parses log lines into structured entries
type LogParser struct {
	serverMap map[string]string // Maps filenames to server IDs
}

// NewLogParser creates a new log parser
func NewLogParser(serverMap map[string]string) *LogParser {
	return &LogParser{
		serverMap: serverMap,
	}
}

// ExtractSIDFromFile reads the first line of a log file to extract SID
func (p *LogParser) ExtractSIDFromFile(filepath string) (string, error) {
	file, err := os.Open(filepath)
	if err != nil {
		return "", fmt.Errorf("error opening file: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	if scanner.Scan() {
		firstLine := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(firstLine, "# SID:") {
			sid := strings.TrimSpace(strings.TrimPrefix(firstLine, "# SID:"))
			return sid, nil
		}
	}
	
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("error reading file: %w", err)
	}
	
	return "", fmt.Errorf("no SID found in file")
}

// GetServerIDFromFile extracts server ID from filename
func (p *LogParser) GetServerIDFromFile(filepath string) string {
	// Extract just the basename
	filename := filepath
	if strings.Contains(filepath, "/") {
		parts := strings.Split(filepath, "/")
		filename = parts[len(parts)-1]
	}
	
	// Strategy 1: Direct match on full path
	if serverID, exists := p.serverMap[filepath]; exists {
		return serverID
	}
	
	// Strategy 2: Direct match on filename
	if serverID, exists := p.serverMap[filename]; exists {
		return serverID
	}
	
	// Strategy 3: Extract base name without instance number
	// e.g., healthcare_1.log -> healthcare
	re := regexp.MustCompile(`_\d+\.log$`)
	baseName := re.ReplaceAllString(filename, "")
	baseName = strings.TrimSuffix(baseName, ".log")
	
	if serverID, exists := p.serverMap[baseName]; exists {
		return serverID
	}
	
	// Strategy 4: Try partial match
	for key, serverID := range p.serverMap {
		if strings.Contains(strings.ToLower(baseName), strings.ToLower(key)) {
			return serverID
		}
	}
	
	return "UNKNOWN"
}

// ParseLog parses a single log line into a DaemonEntry
func (p *LogParser) ParseLog(filepath, serverID, line, sid string) *models.DaemonEntry {
	// Skip SID lines
	if strings.HasPrefix(line, "# SID:") {
		return nil
	}
	
	timestamp := p.extractTimestamp(line)
	
	// Extract just the filename for the log_file field
	filename := filepath
	if strings.Contains(filepath, "/") {
		parts := strings.Split(filepath, "/")
		filename = parts[len(parts)-1]
	}
	
	return &models.DaemonEntry{
		Timestamp:  timestamp,
		ServerType: serverID,
		SID:        sid,
		Message:    strings.TrimSpace(line),
		LogFile:    filename,
	}
}

// extractTimestamp extracts timestamp from different log formats
func (p *LogParser) extractTimestamp(line string) string {
	// 1. Healthcare format: YYYYMMDD-HH:MM:SS:mmm|component|...
	if strings.Contains(line, "|") {
		parts := strings.Split(line, "|")
		firstPart := strings.TrimSpace(parts[0])
		
		// Check if first part looks like healthcare timestamp
		healthcareRe := regexp.MustCompile(`^\d{8}-\d{2}:\d{2}:\d{2}`)
		if healthcareRe.MatchString(firstPart) {
			return firstPart
		}
		
		// Try to find timestamp in other parts
		for _, part := range parts {
			part = strings.TrimSpace(part)
			if healthcareRe.MatchString(part) {
				return part
			}
		}
	}
	
	// 2. Linux format: "Jun 14 15:16:01 ..."
	linuxRe := regexp.MustCompile(`^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+\s+\d{2}:\d{2}:\d{2}`)
	if linuxRe.MatchString(line) {
		parts := strings.Fields(line)
		if len(parts) >= 3 {
			return fmt.Sprintf("%s %s %s", parts[0], parts[1], parts[2])
		}
	}
	
	// 3. Zookeeper/Windows format: YYYY-MM-DD HH:MM:SS,mmm
	datetimeRe := regexp.MustCompile(`^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}`)
	if datetimeRe.MatchString(line) {
		// Try to extract including milliseconds
		millisRe := regexp.MustCompile(`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]\d+)`)
		if match := millisRe.FindString(line); match != "" {
			return match
		}
		
		// Fallback to just date and time
		if len(line) >= 19 {
			return line[:19]
		}
	}
	
	return "unknown"
}

// LoadServerMap loads server mapping from config file
func LoadServerMap(configPath string) (map[string]string, error) {
	// Default mapping
	defaultMap := map[string]string{
		"healthcare": "HEALTHCARE_SERVER",
		"linux":      "LINUX_SERVER",
		"windows":    "WINDOWS_SERVER",
		"zookeeper":  "ZOOKEEPER_SERVER",
	}
	
	// Try to read config file if it exists
	data, err := os.ReadFile(configPath)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Printf("⚠️  Config file not found, using default mapping\n")
			return defaultMap, nil
		}
		return defaultMap, fmt.Errorf("error reading config: %w", err)
	}
	
	// Parse JSON
	var config struct {
		Servers []struct {
			LogFile  string `json:"log_file"`
			ServerID string `json:"server_id"`
		} `json:"servers"`
	}
	
	if err := json.Unmarshal(data, &config); err != nil {
		return defaultMap, fmt.Errorf("error parsing config: %w", err)
	}
	
	// Build mapping
	mapping := make(map[string]string)
	for _, server := range config.Servers {
		mapping[server.LogFile] = server.ServerID
		// Also add without .log extension
		baseName := strings.TrimSuffix(server.LogFile, ".log")
		mapping[baseName] = server.ServerID
	}
	
	// Merge with defaults
	for k, v := range defaultMap {
		if _, exists := mapping[k]; !exists {
			mapping[k] = v
		}
	}
	
	return mapping, nil
}

// UpdateServerMap updates the server mapping
func (p *LogParser) UpdateServerMap(serverMap map[string]string) {
	p.serverMap = serverMap
}

// GetServerMap returns the current server mapping
func (p *LogParser) GetServerMap() map[string]string {
	return p.serverMap
}
