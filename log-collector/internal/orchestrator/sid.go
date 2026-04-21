package orchestrator

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

// SIDGenerator generates and manages unique Server IDs
type SIDGenerator struct {
	registry map[string]ServerSIDInfo
	file     string
	mu       sync.RWMutex
}

// ServerSIDInfo stores metadata about a generated SID
type ServerSIDInfo struct {
	ServerType string `json:"server_type"`
	Instance   int    `json:"instance"`
	Created    string `json:"created"`
}

// NewSIDGenerator creates a new SID generator
func NewSIDGenerator(sidFile string) *SIDGenerator {
	gen := &SIDGenerator{
		registry: make(map[string]ServerSIDInfo),
		file:     sidFile,
	}
	gen.loadRegistry()
	return gen
}

// loadRegistry loads existing SID registry from file
func (g *SIDGenerator) loadRegistry() {
	g.mu.Lock()
	defer g.mu.Unlock()

	data, err := os.ReadFile(g.file)
	if err != nil {
		if os.IsNotExist(err) {
			// File doesn't exist yet, that's okay
			return
		}
		fmt.Printf("⚠️  Error reading SID registry: %v\n", err)
		return
	}

	if len(data) == 0 {
		return
	}

	if err := json.Unmarshal(data, &g.registry); err != nil {
		fmt.Printf("⚠️  Error parsing SID registry: %v\n", err)
		// Start fresh if corrupted
		g.registry = make(map[string]ServerSIDInfo)
	}
}

// saveRegistry saves the SID registry to file
func (g *SIDGenerator) saveRegistry() error {
	g.mu.RLock()
	data, err := json.MarshalIndent(g.registry, "", "  ")
	g.mu.RUnlock()

	if err != nil {
		return fmt.Errorf("error marshaling registry: %w", err)
	}

	if err := os.WriteFile(g.file, data, 0644); err != nil {
		return fmt.Errorf("error writing registry file: %w", err)
	}

	return nil
}

// generateRandomString creates a unique random string
func (g *SIDGenerator) generateRandomString() string {
	// Combine UUID + timestamp for uniqueness
	uniqueStr := uuid.New().String() + time.Now().String()
	
	// SHA256 hash
	hash := sha256.Sum256([]byte(uniqueStr))
	
	// Base64 encode
	encoded := base64.StdEncoding.EncodeToString(hash[:])
	
	// Take first 30 chars and keep only alphanumeric
	var result strings.Builder
	for _, c := range encoded {
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') {
			result.WriteRune(c)
		}
		if result.Len() >= 30 {
			break
		}
	}
	
	return result.String()
}

// getNextInstanceNumber returns the next instance number for a server type
func (g *SIDGenerator) getNextInstanceNumber(serverType string) int {
	g.mu.Lock()
	defer g.mu.Unlock()

	counterKey := serverType + "_counter"
	
	// Find the counter in registry
	var counter int
	if val, exists := g.registry[counterKey]; exists {
		counter = val.Instance
	}
	
	counter++
	
	// Store updated counter
	g.registry[counterKey] = ServerSIDInfo{
		ServerType: serverType,
		Instance:   counter,
		Created:    time.Now().Format(time.RFC3339),
	}
	
	return counter
}

// Generate creates a new SID for a server type
func (g *SIDGenerator) Generate(serverType string) string {
	randomPart := g.generateRandomString()
	instanceNum := g.getNextInstanceNumber(serverType)
	
	sid := fmt.Sprintf("%s_%s_%03d", randomPart, strings.ToUpper(serverType), instanceNum)
	
	// Store the SID mapping
	g.mu.Lock()
	g.registry[sid] = ServerSIDInfo{
		ServerType: serverType,
		Instance:   instanceNum,
		Created:    time.Now().Format(time.RFC3339),
	}
	g.mu.Unlock()
	
	// Save to file
	if err := g.saveRegistry(); err != nil {
		fmt.Printf("⚠️  Error saving SID registry: %v\n", err)
	}
	
	return sid
}

// GenerateWithInstance creates a SID with a specific instance number
func (g *SIDGenerator) GenerateWithInstance(serverType string, instance int) string {
	randomPart := g.generateRandomString()
	sid := fmt.Sprintf("%s_%s_%03d", randomPart, strings.ToUpper(serverType), instance)
	
	// Store the SID mapping
	g.mu.Lock()
	g.registry[sid] = ServerSIDInfo{
		ServerType: serverType,
		Instance:   instance,
		Created:    time.Now().Format(time.RFC3339),
	}
	g.mu.Unlock()
	
	// Update counter if needed
	counterKey := serverType + "_counter"
	g.mu.Lock()
	if val, exists := g.registry[counterKey]; !exists || val.Instance < instance {
		g.registry[counterKey] = ServerSIDInfo{
			ServerType: serverType,
			Instance:   instance,
			Created:    time.Now().Format(time.RFC3339),
		}
	}
	g.mu.Unlock()
	
	// Save to file
	if err := g.saveRegistry(); err != nil {
		fmt.Printf("⚠️  Error saving SID registry: %v\n", err)
	}
	
	return sid
}

// GetSID retrieves an existing SID or creates a new one
func (g *SIDGenerator) GetSID(serverType string, instanceNum int) string {
	g.mu.RLock()
	// Look for existing SID with this instance number
	for sid, info := range g.registry {
		if info.ServerType == serverType && info.Instance == instanceNum {
			g.mu.RUnlock()
			return sid
		}
	}
	g.mu.RUnlock()
	
	// Not found, generate new one
	return g.GenerateWithInstance(serverType, instanceNum)
}

// GetHighestInstance returns the highest instance number for a server type
func (g *SIDGenerator) GetHighestInstance(serverType string) int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	
	highest := 0
	for _, info := range g.registry {
		if info.ServerType == serverType && info.Instance > highest {
			highest = info.Instance
		}
	}
	
	return highest
}

// ValidateSID checks if a SID exists in the registry
func (g *SIDGenerator) ValidateSID(sid string) bool {
	g.mu.RLock()
	defer g.mu.RUnlock()
	
	_, exists := g.registry[sid]
	return exists
}
