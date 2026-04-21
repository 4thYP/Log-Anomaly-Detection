package daemon

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"migrate/internal/models"
)

// Aggregator manages the daemon.json output file
type Aggregator struct {
	outputFile string
	maxEntries int
	entries    []models.DaemonEntry
	mu         sync.RWMutex
}

// NewAggregator creates a new aggregator
func NewAggregator(outputFile string, maxEntries int) *Aggregator {
	agg := &Aggregator{
		outputFile: outputFile,
		maxEntries: maxEntries,
		entries:    make([]models.DaemonEntry, 0),
	}
	
	// Create output directory if it doesn't exist
	dir := filepath.Dir(outputFile)
	if err := os.MkdirAll(dir, 0755); err != nil {
		fmt.Printf("⚠️  Error creating output directory: %v\n", err)
	}
	
	// Initialize with empty array
	agg.initialize()
	
	return agg
}

// initialize creates an empty JSON array if file doesn't exist
func (a *Aggregator) initialize() {
	if _, err := os.Stat(a.outputFile); os.IsNotExist(err) {
		a.WriteEntries()
	}
}

// Add adds a new log entry
func (a *Aggregator) Add(entry *models.DaemonEntry) {
	if entry == nil {
		return
	}
	
	a.mu.Lock()
	defer a.mu.Unlock()
	
	a.entries = append(a.entries, *entry)
	
	// Trim if exceeding max entries
	if len(a.entries) > a.maxEntries {
		a.entries = a.entries[len(a.entries)-a.maxEntries:]
	}
}

// AddBatch adds multiple entries at once
func (a *Aggregator) AddBatch(entries []*models.DaemonEntry) {
	a.mu.Lock()
	defer a.mu.Unlock()
	
	for _, entry := range entries {
		if entry != nil {
			a.entries = append(a.entries, *entry)
		}
	}
	
	// Trim if exceeding max entries
	if len(a.entries) > a.maxEntries {
		a.entries = a.entries[len(a.entries)-a.maxEntries:]
	}
}

// WriteEntries writes all entries to the output file
func (a *Aggregator) WriteEntries() error {
	a.mu.RLock()
	data, err := json.MarshalIndent(a.entries, "", "  ")
	a.mu.RUnlock()
	
	if err != nil {
		return fmt.Errorf("error marshaling entries: %w", err)
	}
	
	if err := os.WriteFile(a.outputFile, data, 0644); err != nil {
		return fmt.Errorf("error writing output file: %w", err)
	}
	
	return nil
}

// GetAll returns all entries
func (a *Aggregator) GetAll() []models.DaemonEntry {
	a.mu.RLock()
	defer a.mu.RUnlock()
	
	entries := make([]models.DaemonEntry, len(a.entries))
	copy(entries, a.entries)
	return entries
}

// Count returns the number of entries
func (a *Aggregator) Count() int {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return len(a.entries)
}

// Clear removes all entries
func (a *Aggregator) Clear() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.entries = make([]models.DaemonEntry, 0)
}

// Reset clears entries and writes empty array to file
func (a *Aggregator) Reset() error {
	a.Clear()
	return a.WriteEntries()
}
