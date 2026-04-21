package learner

import (
	"math"
	"regexp"
	"sort"
	"strconv"

	"migrate/internal/models"
)

// ValueRelationshipExtractor extracts correlations between values
type ValueRelationshipExtractor struct{}

// NewValueRelationshipExtractor creates a new value relationship extractor
func NewValueRelationshipExtractor() *ValueRelationshipExtractor {
	return &ValueRelationshipExtractor{}
}

// Extract extracts value relationships
func (vre *ValueRelationshipExtractor) Extract(logs []models.LogEntry) models.ValueRelationships {
	values := vre.extractValues(logs)
	
	return models.ValueRelationships{
		Correlations:  vre.findCorrelations(values),
		Formulas:      vre.findFormulas(values),
		Distributions: vre.findDistributions(values),
	}
}

// extractValues extracts all numeric values with context
func (vre *ValueRelationshipExtractor) extractValues(logs []models.LogEntry) map[string][]int {
	values := make(map[string][]int)
	
	valuePatterns := []struct {
		pattern string
		ptype   string
	}{
		{`(\w+)=(\d+)`, "field"},
		{`(\w+):\s*(\d+)`, "field"},
		{`(\w+)\s+(\d+)`, "word_value"},
		{`##(\d+)`, "separated"},
		{`\b(\d+)\b`, "bare_number"},
	}
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		component, _ := log.Fields["component"].(string)
		if component == "" {
			component = "unknown"
		}
		
		for _, vp := range valuePatterns {
			re := regexp.MustCompile(vp.pattern)
			matches := re.FindAllStringSubmatch(message, -1)
			
			for _, match := range matches {
				if len(match) > 1 {
					var name string
					var valStr string
					
					if vp.ptype == "field" || vp.ptype == "word_value" {
						name = match[1]
						valStr = match[2]
					} else if vp.ptype == "separated" {
						name = "separated_value"
						valStr = match[1]
					} else {
						name = "number"
						valStr = match[1]
					}
					
					val, err := strconv.Atoi(valStr)
					if err != nil {
						continue
					}
					
					// Filter small numbers for bare numbers
					if vp.ptype == "bare_number" && val < 100 {
						continue
					}
					
					key := component + "." + name
					values[key] = append(values[key], val)
				}
			}
		}
	}
	
	return values
}

// findCorrelations finds relationships between value pairs
func (vre *ValueRelationshipExtractor) findCorrelations(values map[string][]int) []models.Correlation {
	correlations := make([]models.Correlation, 0)
	
	// Get value names with enough samples
	validNames := make([]string, 0)
	for name, vals := range values {
		if len(vals) > 5 {
			validNames = append(validNames, name)
		}
	}
	
	for i := 0; i < len(validNames); i++ {
		for j := i + 1; j < len(validNames); j++ {
			name1 := validNames[i]
			name2 := validNames[j]
			
			vals1 := values[name1]
			vals2 := values[name2]
			
			// Take first 20 samples
			if len(vals1) > 20 {
				vals1 = vals1[:20]
			}
			if len(vals2) > 20 {
				vals2 = vals2[:20]
			}
			
			minLen := len(vals1)
			if len(vals2) < minLen {
				minLen = len(vals2)
			}
			
			if minLen < 5 {
				continue
			}
			
			// Check for constant ratio
			if ratio := vre.checkRatio(vals1[:minLen], vals2[:minLen]); ratio > 0 {
				confidence := "medium"
				if math.Abs(ratio-math.Round(ratio)) < 0.1 {
					confidence = "high"
				}
				
				correlations = append(correlations, models.Correlation{
					Value1:       name1,
					Value2:       name2,
					Relationship: name1 + " ≈ " + formatFloat(ratio) + " × " + name2,
					Confidence:   confidence,
				})
			}
			
			// Check for constant difference
			if diff := vre.checkDifference(vals1[:minLen], vals2[:minLen]); diff != nil {
				correlations = append(correlations, models.Correlation{
					Value1:       name1,
					Value2:       name2,
					Relationship: name1 + " = " + name2 + " + " + strconv.Itoa(*diff),
					Confidence:   "high",
				})
			}
		}
	}
	
	// Return top 20
	if len(correlations) > 20 {
		correlations = correlations[:20]
	}
	
	return correlations
}

// checkRatio checks if values maintain a constant ratio
func (vre *ValueRelationshipExtractor) checkRatio(vals1, vals2 []int) float64 {
	ratios := make([]float64, 0)
	
	for i := 0; i < len(vals1); i++ {
		if vals2[i] != 0 {
			ratios = append(ratios, float64(vals1[i])/float64(vals2[i]))
		}
	}
	
	if len(ratios) > 3 {
		sum := 0.0
		for _, r := range ratios {
			sum += r
		}
		avg := sum / float64(len(ratios))
		
		// Check variance
		variance := 0.0
		for _, r := range ratios {
			variance += math.Pow(r-avg, 2)
		}
		variance /= float64(len(ratios))
		
		if variance < 0.1 {
			return avg
		}
	}
	
	return 0
}

// checkDifference checks if values maintain a constant difference
func (vre *ValueRelationshipExtractor) checkDifference(vals1, vals2 []int) *int {
	if len(vals1) < 3 {
		return nil
	}
	
	diff := vals1[0] - vals2[0]
	for i := 1; i < len(vals1); i++ {
		if vals1[i]-vals2[i] != diff {
			return nil
		}
	}
	
	return &diff
}

// findFormulas finds formulaic relationships
func (vre *ValueRelationshipExtractor) findFormulas(values map[string][]int) []models.Formula {
	formulas := make([]models.Formula, 0)
	
	for name, vals := range values {
		if len(vals) > 10 {
			// Check for increments
			diffs := make([]int, 0)
			for i := 0; i < len(vals)-1; i++ {
				diffs = append(diffs, vals[i+1]-vals[i])
			}
			
			// Check if all diffs are the same and positive
			allSame := true
			for i := 1; i < len(diffs); i++ {
				if diffs[i] != diffs[0] {
					allSame = false
					break
				}
			}
			
			if allSame && diffs[0] > 0 {
				formulas = append(formulas, models.Formula{
					Variable:    name,
					Pattern:     "increments_by",
					Value:       diffs[0],
					Description: name + " increases by " + strconv.Itoa(diffs[0]) + " each time",
				})
			}
			
			// Check for arithmetic progression
			if vre.isArithmeticProgression(vals[:10]) {
				formulas = append(formulas, models.Formula{
					Variable:    name,
					Pattern:     "arithmetic_progression",
					Description: name + " follows an arithmetic progression",
				})
			}
		}
	}
	
	return formulas
}

// isArithmeticProgression checks if values form an arithmetic progression
func (vre *ValueRelationshipExtractor) isArithmeticProgression(vals []int) bool {
	if len(vals) < 3 {
		return false
	}
	
	diff := vals[1] - vals[0]
	for i := 1; i < len(vals)-1; i++ {
		if vals[i+1]-vals[i] != diff {
			return false
		}
	}
	
	return true
}

// findDistributions finds value ranges and distributions
func (vre *ValueRelationshipExtractor) findDistributions(values map[string][]int) map[string]models.Distribution {
	distributions := make(map[string]models.Distribution)
	
	for name, vals := range values {
		if len(vals) > 3 {
			// Sort values
			sorted := make([]int, len(vals))
			copy(sorted, vals)
			sort.Ints(sorted)
			
			// Calculate statistics
			min := sorted[0]
			max := sorted[len(sorted)-1]
			sum := 0
			for _, v := range vals {
				sum += v
			}
			avg := float64(sum) / float64(len(vals))
			median := sorted[len(sorted)/2]
			
			// Count unique values
			uniqueMap := make(map[int]bool)
			for _, v := range vals {
				uniqueMap[v] = true
			}
			
			dist := models.Distribution{
				Min:          min,
				Max:          max,
				Avg:          avg,
				Median:       median,
				Count:        len(vals),
				UniqueValues: len(uniqueMap),
			}
			
			// Calculate standard deviation
			if len(vals) > 1 {
				variance := 0.0
				for _, v := range vals {
					variance += math.Pow(float64(v)-avg, 2)
				}
				variance /= float64(len(vals))
				dist.StdDev = math.Sqrt(variance)
			}
			
			distributions[name] = dist
		}
	}
	
	// Sort by count and return top 30
	type kv struct {
		Key   string
		Value models.Distribution
	}
	
	var sorted []kv
	for k, v := range distributions {
		sorted = append(sorted, kv{k, v})
	}
	
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Value.Count > sorted[j].Value.Count
	})
	
	result := make(map[string]models.Distribution)
	for i, kv := range sorted {
		if i >= 30 {
			break
		}
		result[kv.Key] = kv.Value
	}
	
	return result
}
