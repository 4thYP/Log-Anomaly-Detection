package models

import "time"

// LogEntry represents a parsed log line from any server type
type LogEntry struct {
	ServerType string                 // healthcare, linux, windows, zookeeper
	Timestamp  time.Time              // Parsed timestamp
	RawLine    string                 // Original log line
	Fields     map[string]interface{} // Parsed fields specific to server type
}

// DaemonEntry represents a single entry in daemon.json
type DaemonEntry struct {
	Timestamp  string `json:"timestamp"`
	ServerType string `json:"server_type"`
	SID        string `json:"sid"`
	Message    string `json:"message"`
	LogFile    string `json:"log_file"`
}
