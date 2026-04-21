package learner

import (
	"regexp"
	"strings"
	"time"

	"migrate/internal/models"
)

// LogParser parses different log formats
type LogParser struct {
	serverType string
	config     models.ServerConfig
}

// NewLogParser creates a new parser for a server type
func NewLogParser(serverType string, config models.ServerConfig) *LogParser {
	return &LogParser{
		serverType: serverType,
		config:     config,
	}
}

// Parse parses a raw log line into a LogEntry
func (p *LogParser) Parse(line string) *models.LogEntry {
	line = strings.TrimSpace(line)
	if line == "" {
		return nil
	}
	
	entry := &models.LogEntry{
		ServerType: p.serverType,
		RawLine:    line,
		Fields:     make(map[string]interface{}),
	}
	
	switch p.serverType {
	case "healthcare":
		p.parseHealthcare(line, entry)
	case "linux":
		p.parseLinux(line, entry)
	case "windows":
		p.parseWindows(line, entry)
	case "zookeeper":
		p.parseZookeeper(line, entry)
	default:
		// Fallback: just store the raw line
		entry.Fields["message"] = line
	}
	
	return entry
}

// parseHealthcare parses healthcare format: timestamp|component|user_id|message
func (p *LogParser) parseHealthcare(line string, entry *models.LogEntry) {
	parts := strings.Split(line, "|")
	if len(parts) >= 4 {
		entry.Timestamp = p.parseHealthcareTimestamp(strings.TrimSpace(parts[0]))
		entry.Fields["component"] = strings.TrimSpace(parts[1])
		entry.Fields["user_id"] = strings.TrimSpace(parts[2])
		entry.Fields["message"] = strings.TrimSpace(strings.Join(parts[3:], "|"))
	} else {
		// If parsing fails, still store the raw line
		entry.Fields["raw"] = line
		entry.Fields["message"] = line
	}
}

// parseHealthcareTimestamp parses: 20171223-22:15:29:606
func (p *LogParser) parseHealthcareTimestamp(ts string) time.Time {
	// Handle format: 20171223-22:15:29:606
	// Remove milliseconds part for parsing (everything after the last colon)
	lastColon := strings.LastIndex(ts, ":")
	if lastColon > 0 {
		ts = ts[:lastColon]
	}
	
	// Try parsing with standard format
	t, err := time.Parse("20060102-15:04:05", ts)
	if err != nil {
		// Try alternative format if standard fails
		t, _ = time.Parse("2006-01-02-15:04:05", ts)
	}
	return t
}

// parseLinux parses Linux format: MMM DD HH:MM:SS hostname process[pid]: message
func (p *LogParser) parseLinux(line string, entry *models.LogEntry) {
	// Try to parse with regex first
	re := regexp.MustCompile(`^(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)$`)
	matches := re.FindStringSubmatch(line)
	if len(matches) >= 5 {
		entry.Timestamp = p.parseLinuxTimestamp(matches[1])
		entry.Fields["hostname"] = matches[2]
		entry.Fields["component"] = extractComponent(matches[3])
		entry.Fields["message"] = matches[4]
		return
	}
	
	// Fallback: simple space split
	parts := strings.SplitN(line, " ", 6)
	if len(parts) >= 6 {
		timestamp := parts[0] + " " + parts[1] + " " + parts[2]
		entry.Timestamp = p.parseLinuxTimestamp(timestamp)
		entry.Fields["hostname"] = parts[3]
		entry.Fields["component"] = extractComponent(parts[4])
		entry.Fields["message"] = parts[5]
	} else {
		entry.Fields["message"] = line
	}
}

// parseLinuxTimestamp parses: Jun 14 15:16:01
func (p *LogParser) parseLinuxTimestamp(ts string) time.Time {
	// Remove extra spaces
	ts = regexp.MustCompile(`\s+`).ReplaceAllString(ts, " ")
	
	t, err := time.Parse("Jan 2 15:04:05", ts)
	if err != nil {
		// Try with current year
		return time.Time{}
	}
	// Set year to 2005 (based on the logs)
	return time.Date(2005, t.Month(), t.Day(), t.Hour(), t.Minute(), t.Second(), 0, time.UTC)
}

// parseWindows parses Windows format: YYYY-MM-DD HH:MM:SS, Level Component Message
func (p *LogParser) parseWindows(line string, entry *models.LogEntry) {
	// Try regex first
	re := regexp.MustCompile(`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\s*(\w+)\s+(\S+)\s+(.*)$`)
	matches := re.FindStringSubmatch(line)
	if len(matches) >= 5 {
		entry.Timestamp = p.parseWindowsTimestamp(matches[1])
		entry.Fields["level"] = matches[2]
		entry.Fields["component"] = matches[3]
		entry.Fields["message"] = matches[4]
		return
	}
	
	// Fallback: simple split
	parts := strings.SplitN(line, ",", 2)
	if len(parts) >= 2 {
		timestamp := strings.TrimSpace(parts[0])
		entry.Timestamp = p.parseWindowsTimestamp(timestamp)
		
		rest := strings.TrimSpace(parts[1])
		spaceParts := strings.SplitN(rest, " ", 3)
		if len(spaceParts) >= 3 {
			entry.Fields["level"] = spaceParts[0]
			entry.Fields["component"] = spaceParts[1]
			entry.Fields["message"] = spaceParts[2]
		} else {
			entry.Fields["message"] = rest
		}
	} else {
		entry.Fields["message"] = line
	}
}

// parseWindowsTimestamp parses: 2016-09-28 04:30:30
func (p *LogParser) parseWindowsTimestamp(ts string) time.Time {
	ts = strings.TrimSpace(ts)
	t, err := time.Parse("2006-01-02 15:04:05", ts)
	if err != nil {
		return time.Time{}
	}
	return t
}

// parseZookeeper parses Zookeeper format: YYYY-MM-DD HH:MM:SS,SSS - LEVEL [Component] - Message
func (p *LogParser) parseZookeeper(line string, entry *models.LogEntry) {
	// Try regex first
	re := regexp.MustCompile(`^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s*-\s*(\w+)\s+\[([^\]]+)\]\s*-\s*(.*)$`)
	matches := re.FindStringSubmatch(line)
	if len(matches) >= 5 {
		entry.Timestamp = p.parseZookeeperTimestamp(matches[1])
		entry.Fields["level"] = matches[2]
		entry.Fields["component"] = matches[3]
		entry.Fields["message"] = matches[4]
		return
	}
	
	// Fallback: split by " - "
	parts := strings.SplitN(line, " - ", 3)
	if len(parts) >= 3 {
		timestampPart := strings.TrimSpace(parts[0])
		entry.Timestamp = p.parseZookeeperTimestamp(timestampPart)
		
		middlePart := strings.TrimSpace(parts[1])
		spaceIdx := strings.Index(middlePart, " ")
		if spaceIdx > 0 {
			entry.Fields["level"] = middlePart[:spaceIdx]
			component := strings.TrimSpace(middlePart[spaceIdx:])
			component = strings.Trim(component, "[]")
			entry.Fields["component"] = component
		}
		entry.Fields["message"] = strings.TrimSpace(parts[2])
	} else {
		entry.Fields["message"] = line
	}
}

// parseZookeeperTimestamp parses: 2015-07-29 17:41:44,747
func (p *LogParser) parseZookeeperTimestamp(ts string) time.Time {
	ts = strings.TrimSpace(ts)
	// Replace comma with dot for Go's time parser
	ts = strings.Replace(ts, ",", ".", 1)
	t, err := time.Parse("2006-01-02 15:04:05.000", ts)
	if err != nil {
		// Try without milliseconds
		t, _ = time.Parse("2006-01-02 15:04:05", ts)
	}
	return t
}

// extractComponent extracts component name from process string
func extractComponent(process string) string {
	// Remove PID if present: sshd(pam_unix)[19939] -> sshd
	re := regexp.MustCompile(`^(\w+)\([^)]*\)\[\d+\]$`)
	if matches := re.FindStringSubmatch(process); len(matches) > 1 {
		return matches[1]
	}
	
	// Handle format: sshd[19939]
	re2 := regexp.MustCompile(`^(\w+)\[\d+\]$`)
	if matches := re2.FindStringSubmatch(process); len(matches) > 1 {
		return matches[1]
	}
	
	// Remove trailing colon
	process = strings.TrimSuffix(process, ":")
	
	return process
}
