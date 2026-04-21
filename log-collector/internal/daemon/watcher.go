package daemon

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"migrate/internal/models"
)

// FileWatcher watches log files for changes
type FileWatcher struct {
	watcher    *fsnotify.Watcher
	parser     *LogParser
	aggregator *Aggregator
	positions  map[string]int64      // Track file read positions
	sids       map[string]string     // Cache SIDs per file
	mu         sync.RWMutex
	done       chan bool
}

// NewFileWatcher creates a new file watcher
func NewFileWatcher(logDir string, parser *LogParser, aggregator *Aggregator) (*FileWatcher, error) {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("error creating watcher: %w", err)
	}
	
	// Add the log directory to watcher
	if err := watcher.Add(logDir); err != nil {
		return nil, fmt.Errorf("error watching directory: %w", err)
	}
	
	fw := &FileWatcher{
		watcher:    watcher,
		parser:     parser,
		aggregator: aggregator,
		positions:  make(map[string]int64),
		sids:       make(map[string]string),
		done:       make(chan bool),
	}
	
	return fw, nil
}

// Start begins watching for file changes
func (fw *FileWatcher) Start() {
	fmt.Println("👁️  File watcher started")
	
	go func() {
		// Periodically write aggregator data
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		
		for {
			select {
			case event, ok := <-fw.watcher.Events:
				if !ok {
					return
				}
				
				// Only process .log files
				if filepath.Ext(event.Name) == ".log" {
					if event.Op&fsnotify.Write == fsnotify.Write {
						fw.processFile(event.Name)
					}
				}
				
			case err, ok := <-fw.watcher.Errors:
				if !ok {
					return
				}
				fmt.Printf("⚠️  Watcher error: %v\n", err)
				
			case <-ticker.C:
				// Flush aggregator periodically
				if err := fw.aggregator.WriteEntries(); err != nil {
					fmt.Printf("⚠️  Error writing aggregator: %v\n", err)
				}
				
			case <-fw.done:
				return
			}
		}
	}()
}

// Stop stops the file watcher
func (fw *FileWatcher) Stop() {
	fw.done <- true
	fw.watcher.Close()
	
	// Final flush
	if err := fw.aggregator.WriteEntries(); err != nil {
		fmt.Printf("⚠️  Error writing aggregator: %v\n", err)
	}
	
	fmt.Println("👁️  File watcher stopped")
}

// ProcessExistingFiles processes all existing log files in the directory
func (fw *FileWatcher) ProcessExistingFiles(logDir string) {
	files, err := filepath.Glob(filepath.Join(logDir, "*.log"))
	if err != nil {
		fmt.Printf("⚠️  Error scanning for log files: %v\n", err)
		return
	}
	
	for _, file := range files {
		fmt.Printf("📁 Processing existing file: %s\n", filepath.Base(file))
		fw.processFile(file)
	}
}

// processFile processes new lines in a log file
func (fw *FileWatcher) processFile(filepath string) {
	fw.mu.Lock()
	defer fw.mu.Unlock()
	
	// Get server ID
	serverID := fw.parser.GetServerIDFromFile(filepath)
	
	// Get SID (cached or extract)
	sid, exists := fw.sids[filepath]
	if !exists {
		var err error
		sid, err = fw.parser.ExtractSIDFromFile(filepath)
		if err != nil {
			fmt.Printf("⚠️  Could not extract SID from %s: %v\n", filepath, err)
			sid = ""
		} else {
			fw.sids[filepath] = sid
			fmt.Printf("✅ Extracted SID: %s from %s\n", sid, filepath)
		}
	}
	
	// Get last read position
	lastPos := fw.positions[filepath]
	
	// Check if file was truncated
	fileInfo, err := os.Stat(filepath)
	if err != nil {
		fmt.Printf("⚠️  Error stating file %s: %v\n", filepath, err)
		return
	}
	
	if fileInfo.Size() < lastPos {
		fmt.Printf("⚠️  File %s was truncated, resetting position\n", filepath)
		lastPos = 0
	}
	
	// Open and read new lines
	file, err := os.Open(filepath)
	if err != nil {
		fmt.Printf("⚠️  Error opening file %s: %v\n", filepath, err)
		return
	}
	defer file.Close()
	
	// Seek to last position
	if _, err := file.Seek(lastPos, 0); err != nil {
		fmt.Printf("⚠️  Error seeking file %s: %v\n", filepath, err)
		return
	}
	
	// Read new lines
	reader := bufio.NewReader(file)
	var entries []*models.DaemonEntry
	
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if err != io.EOF {
				fmt.Printf("⚠️  Error reading file %s: %v\n", filepath, err)
			}
			break
		}
		
		line = strings.TrimSpace(line)
		if line != "" {
			entry := fw.parser.ParseLog(filepath, serverID, line, sid)
			if entry != nil {
				entries = append(entries, entry)
			}
		}
	}
	
	// Update position
	currentPos, _ := file.Seek(0, io.SeekCurrent)
	fw.positions[filepath] = currentPos
	
	// Add entries to aggregator
	if len(entries) > 0 {
		fw.aggregator.AddBatch(entries)
		fmt.Printf("📝 Processed %d new lines from %s\n", len(entries), filepath)
	}
}
