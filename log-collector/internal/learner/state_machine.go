package learner

import (
	"regexp"
	"sort"
	"strconv"
	"strings"

	"migrate/internal/models"
)

// StateMachineExtractor extracts state machines from logs
type StateMachineExtractor struct{}

// NewStateMachineExtractor creates a new state machine extractor
func NewStateMachineExtractor() *StateMachineExtractor {
	return &StateMachineExtractor{}
}

// Extract extracts state machine patterns
func (sme *StateMachineExtractor) Extract(logs []models.LogEntry) models.StateMachine {
	return models.StateMachine{
		Counters:  sme.findCounters(logs),
		Flags:     sme.findFlags(logs),
		Sequences: sme.findSequences(logs),
		Values:    sme.findTrackingValues(logs),
	}
}

// findCounters finds incrementing counters
func (sme *StateMachineExtractor) findCounters(logs []models.LogEntry) map[string]models.Counter {
	counters := make(map[string]models.Counter)
	lastValues := make(map[string]int)
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		// Look for patterns like "word number"
		re := regexp.MustCompile(`(\w+)\s+(\d+)`)
		matches := re.FindAllStringSubmatch(message, -1)
		
		for _, match := range matches {
			name := match[1]
			value, _ := strconv.Atoi(match[2])
			
			if lastVal, exists := lastValues[name]; exists {
				counter := counters[name]
				counter.Samples = append(counter.Samples, value)
				if value > lastVal {
					counter.Type = "incrementing_counter"
				}
				counters[name] = counter
			} else {
				counters[name] = models.Counter{
					Type:    "counter",
					Samples: []int{value},
				}
			}
			lastValues[name] = value
		}
	}
	
	return counters
}

// findFlags finds boolean state variables
func (sme *StateMachineExtractor) findFlags(logs []models.LogEntry) map[string]int {
	flags := make(map[string]int)
	flagPatterns := []string{"SCREEN_ON", "SCREEN_OFF", "true", "false", "ON", "OFF"}
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		for _, pattern := range flagPatterns {
			if strings.Contains(message, pattern) {
				flags[pattern]++
			}
		}
	}
	
	return flags
}

// findSequences finds sequential state changes
func (sme *StateMachineExtractor) findSequences(logs []models.LogEntry) models.SequenceInfo {
	type transition struct {
		from string
		to   string
	}
	
	sequences := make([]transition, 0)
	
	var lastMessage string
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		// Use first 30 chars as state
		current := message
		if len(current) > 30 {
			current = current[:30]
		}
		
		if lastMessage != "" && lastMessage != current {
			sequences = append(sequences, transition{lastMessage, current})
		}
		
		lastMessage = current
	}
	
	// Count transitions
	transitionCounts := make(map[string]int)
	for _, seq := range sequences {
		key := seq.from + " → " + seq.to
		transitionCounts[key]++
	}
	
	// Sort and get top 20
	sortedTransitions := make(map[string]int)
	type kv struct {
		Key   string
		Value int
	}
	var sorted []kv
	for k, v := range transitionCounts {
		sorted = append(sorted, kv{k, v})
	}
	
	// Sort descending
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Value > sorted[j].Value
	})
	
	for i, kv := range sorted {
		if i >= 20 {
			break
		}
		sortedTransitions[kv.Key] = kv.Value
	}
	
	return models.SequenceInfo{
		CommonTransitions: sortedTransitions,
		TotalSequences:    len(sequences),
	}
}

// findTrackingValues finds values that are tracked over time
func (sme *StateMachineExtractor) findTrackingValues(logs []models.LogEntry) map[string]models.ValueInfo {
	tracked := make(map[string][]int)
	
	valuePatterns := []struct {
		pattern string
		name    string
	}{
		{`totalSteps=(\d+)`, "totalSteps"},
		{`totalCalories=(\d+)`, "totalCalories"},
		{`totalAltitude=(\d+)`, "totalAltitude"},
		{`patient_id=(\d+)`, "patient_id"},
		{`step_count[=:\s]+(\d+)`, "step_count"},
	}
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		for _, vp := range valuePatterns {
			re := regexp.MustCompile(vp.pattern)
			if match := re.FindStringSubmatch(message); len(match) > 1 {
				val, _ := strconv.Atoi(match[1])
				tracked[vp.name] = append(tracked[vp.name], val)
			}
		}
	}
	
	// Calculate statistics
	result := make(map[string]models.ValueInfo)
	for name, values := range tracked {
		if len(values) > 0 {
			min, max, sum := values[0], values[0], 0
			for _, v := range values {
				if v < min {
					min = v
				}
				if v > max {
					max = v
				}
				sum += v
			}
			
			result[name] = models.ValueInfo{
				Min:     min,
				Max:     max,
				Avg:     float64(sum) / float64(len(values)),
				Samples: len(values),
			}
		}
	}
	
	return result
}
