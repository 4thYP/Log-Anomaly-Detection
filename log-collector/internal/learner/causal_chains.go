package learner

import (
	"sort"
	"strings"

	"migrate/internal/models"
)

// CausalChainExtractor extracts event sequences and cause-effect relationships
type CausalChainExtractor struct{}

// NewCausalChainExtractor creates a new causal chain extractor
func NewCausalChainExtractor() *CausalChainExtractor {
	return &CausalChainExtractor{}
}

// Extract extracts causal chains
func (cce *CausalChainExtractor) Extract(logs []models.LogEntry) models.CausalChains {
	chains := cce.findSequencesByComponent(logs)
	probabilities := cce.calculateTransitionProbabilities(chains)
	patterns := cce.findCommonPatterns(chains)
	
	return models.CausalChains{
		Chains:                 cce.topChains(chains, 20),
		TransitionProbabilities: probabilities,
		CommonPatterns:         patterns,
		TotalChains:            len(chains),
	}
}

// ChainData represents a sequence event
type ChainData struct {
	Component string
	From      string
	To        string
	TimeDiff  int
}

// findSequencesByComponent groups logs by component and finds sequences
func (cce *CausalChainExtractor) findSequencesByComponent(logs []models.LogEntry) []ChainData {
	// Group by component
	componentLogs := make(map[string][]models.LogEntry)
	for _, log := range logs {
		component, ok := log.Fields["component"].(string)
		if !ok {
			component = "unknown"
		}
		componentLogs[component] = append(componentLogs[component], log)
	}
	
	sequences := make([]ChainData, 0)
	
	for _, logsList := range componentLogs {
		if len(logsList) < 2 {
			continue
		}
		
		for i := 0; i < len(logsList)-1; i++ {
			currentMsg, ok1 := logsList[i].Fields["message"].(string)
			nextMsg, ok2 := logsList[i+1].Fields["message"].(string)
			
			if !ok1 || !ok2 {
				continue
			}
			
			// Use first 50 chars as event identifier
			if len(currentMsg) > 50 {
				currentMsg = currentMsg[:50]
			}
			if len(nextMsg) > 50 {
				nextMsg = nextMsg[:50]
			}
			
			component, _ := logsList[i].Fields["component"].(string)
			
			timeDiff := 1
			if !logsList[i].Timestamp.IsZero() && !logsList[i+1].Timestamp.IsZero() {
				timeDiff = int(logsList[i+1].Timestamp.Sub(logsList[i].Timestamp).Seconds())
			}
			
			sequences = append(sequences, ChainData{
				Component: component,
				From:      currentMsg,
				To:        nextMsg,
				TimeDiff:  timeDiff,
			})
		}
	}
	
	return sequences
}

// calculateTransitionProbabilities calculates probability of B following A
func (cce *CausalChainExtractor) calculateTransitionProbabilities(sequences []ChainData) map[string]map[string]float64 {
	transitions := make(map[string]map[string]int)
	totals := make(map[string]int)
	
	for _, seq := range sequences {
		if _, exists := transitions[seq.From]; !exists {
			transitions[seq.From] = make(map[string]int)
		}
		transitions[seq.From][seq.To]++
		totals[seq.From]++
	}
	
	// Convert to probabilities
	probabilities := make(map[string]map[string]float64)
	for from, toMap := range transitions {
		probabilities[from] = make(map[string]float64)
		for to, count := range toMap {
			if totals[from] > 0 {
				probabilities[from][to] = float64(count) / float64(totals[from])
			}
		}
	}
	
	// Sort and return top 20 by total frequency
	type fromTotal struct {
		from  string
		total int
	}
	
	var sorted []fromTotal
	for from, total := range totals {
		sorted = append(sorted, fromTotal{from, total})
	}
	
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].total > sorted[j].total
	})
	
	result := make(map[string]map[string]float64)
	for i, ft := range sorted {
		if i >= 20 {
			break
		}
		result[ft.from] = probabilities[ft.from]
	}
	
	return result
}

// findCommonPatterns finds common 3-event patterns
func (cce *CausalChainExtractor) findCommonPatterns(sequences []ChainData) []models.Pattern {
	if len(sequences) < 3 {
		return []models.Pattern{}
	}
	
	patternCounts := make(map[string]int)
	
	for i := 0; i < len(sequences)-2; i++ {
		pattern := sequences[i].From + "|" + sequences[i+1].From + "|" + sequences[i+2].From
		patternCounts[pattern]++
	}
	
	// Sort patterns
	type patternCount struct {
		pattern string
		count   int
	}
	
	var sorted []patternCount
	for p, c := range patternCounts {
		sorted = append(sorted, patternCount{p, c})
	}
	
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].count > sorted[j].count
	})
	
	// Convert to Pattern structs
	patterns := make([]models.Pattern, 0)
	for i, pc := range sorted {
		if i >= 10 {
			break
		}
		
		parts := strings.Split(pc.pattern, "|")
		patterns = append(patterns, models.Pattern{
			Pattern:   parts,
			Frequency: pc.count,
		})
	}
	
	return patterns
}

// topChains returns the top N chains
func (cce *CausalChainExtractor) topChains(sequences []ChainData, n int) []models.Chain {
	if len(sequences) <= n {
		chains := make([]models.Chain, len(sequences))
		for i, seq := range sequences {
			chains[i] = models.Chain{
				Component: seq.Component,
				From:      seq.From,
				To:        seq.To,
				TimeDiff:  seq.TimeDiff,
			}
		}
		return chains
	}
	
	chains := make([]models.Chain, n)
	for i := 0; i < n; i++ {
		chains[i] = models.Chain{
			Component: sequences[i].Component,
			From:      sequences[i].From,
			To:        sequences[i].To,
			TimeDiff:  sequences[i].TimeDiff,
		}
	}
	return chains
}
