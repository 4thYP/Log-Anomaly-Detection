package orchestrator

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"

	"migrate/internal/models"
)

// InstanceRegistry manages the list.json file
type InstanceRegistry struct {
	instances []models.ServerInstance
	file      string
	mu        sync.RWMutex
}

// NewInstanceRegistry creates a new instance registry
func NewInstanceRegistry(listFile string) *InstanceRegistry {
	reg := &InstanceRegistry{
		instances: make([]models.ServerInstance, 0),
		file:      listFile,
	}
	reg.load()
	return reg
}

// load loads existing instances from file
func (r *InstanceRegistry) load() error {
	r.mu.Lock()
	defer r.mu.Unlock()

	data, err := os.ReadFile(r.file)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // File doesn't exist yet
		}
		return fmt.Errorf("error reading registry: %w", err)
	}

	if len(data) == 0 {
		return nil
	}

	if err := json.Unmarshal(data, &r.instances); err != nil {
		return fmt.Errorf("error parsing registry: %w", err)
	}

	return nil
}

// save saves instances to file
func (r *InstanceRegistry) save() error {
	r.mu.RLock()
	data, err := json.MarshalIndent(r.instances, "", "  ")
	r.mu.RUnlock()

	if err != nil {
		return fmt.Errorf("error marshaling instances: %w", err)
	}

	if err := os.WriteFile(r.file, data, 0644); err != nil {
		return fmt.Errorf("error writing registry file: %w", err)
	}

	return nil
}

// Add adds a new server instance
func (r *InstanceRegistry) Add(instance models.ServerInstance) error {
	r.mu.Lock()
	r.instances = append(r.instances, instance)
	r.mu.Unlock()
	
	return r.save()
}

// AddMultiple adds multiple server instances
func (r *InstanceRegistry) AddMultiple(instances []models.ServerInstance) error {
	r.mu.Lock()
	r.instances = append(r.instances, instances...)
	r.mu.Unlock()
	
	return r.save()
}

// GetAll returns all instances
func (r *InstanceRegistry) GetAll() []models.ServerInstance {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	// Return a copy
	instances := make([]models.ServerInstance, len(r.instances))
	copy(instances, r.instances)
	return instances
}

// GetByType returns instances of a specific server type
func (r *InstanceRegistry) GetByType(serverType string) []models.ServerInstance {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	var result []models.ServerInstance
	for _, inst := range r.instances {
		if inst.Type == serverType {
			result = append(result, inst)
		}
	}
	return result
}

// GetHighestInstance returns the highest instance number for a server type
func (r *InstanceRegistry) GetHighestInstance(serverType string) int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	highest := 0
	for _, inst := range r.instances {
		if inst.Type == serverType && inst.Instance > highest {
			highest = inst.Instance
		}
	}
	return highest
}

// UpdateStatus updates the status of an instance
func (r *InstanceRegistry) UpdateStatus(sid string, status string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	for i := range r.instances {
		if r.instances[i].SID == sid {
			r.instances[i].Status = status
			return r.save()
		}
	}
	
	return fmt.Errorf("instance with SID %s not found", sid)
}

// UpdateAllStatus updates status for all instances
func (r *InstanceRegistry) UpdateAllStatus(status string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	for i := range r.instances {
		r.instances[i].Status = status
	}
	
	return r.save()
}

// Clear removes all instances
func (r *InstanceRegistry) Clear() error {
	r.mu.Lock()
	r.instances = make([]models.ServerInstance, 0)
	r.mu.Unlock()
	
	return r.save()
}

// Count returns the total number of instances
func (r *InstanceRegistry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.instances)
}

// CountByType returns the number of instances of a specific type
func (r *InstanceRegistry) CountByType(serverType string) int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	count := 0
	for _, inst := range r.instances {
		if inst.Type == serverType {
			count++
		}
	}
	return count
}

// Exists checks if an instance with given SID exists
func (r *InstanceRegistry) Exists(sid string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	for _, inst := range r.instances {
		if inst.SID == sid {
			return true
		}
	}
	return false
}
