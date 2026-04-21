package learner

import (
	"regexp"
	"sort"

	"migrate/internal/models"
)

// TemplateExtractor extracts message templates
type TemplateExtractor struct{}

// NewTemplateExtractor creates a new template extractor
func NewTemplateExtractor() *TemplateExtractor {
	return &TemplateExtractor{}
}

// Extract extracts templates and components from logs
func (te *TemplateExtractor) Extract(logs []models.LogEntry) (models.Templates, models.Components) {
	templates := make(map[string]int)
	components := make(map[string]int)
	
	for _, log := range logs {
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		// Create template
		template := te.createTemplate(message)
		templates[template]++
		
		// Count components
		if component, ok := log.Fields["component"].(string); ok {
			components[component]++
		}
	}
	
	// Sort templates by frequency
	sortedTemplates := te.sortByFrequency(templates, 50)
	
	return models.Templates{
		ByFrequency:    sortedTemplates,
		TotalTemplates: len(templates),
	}, models.Components{
		ByFrequency:     te.sortByFrequency(components, 0),
		TotalComponents: len(components),
	}
}

// createTemplate replaces numbers and variables with <*>
func (te *TemplateExtractor) createTemplate(message string) string {
	// Replace numbers
	re := regexp.MustCompile(`\b\d+\b`)
	template := re.ReplaceAllString(message, "<*>")
	
	// Replace hex values
	hexRe := regexp.MustCompile(`0x[0-9a-fA-F]+`)
	template = hexRe.ReplaceAllString(template, "<*>")
	
	// Replace UUIDs
	uuidRe := regexp.MustCompile(`[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}`)
	template = uuidRe.ReplaceAllString(template, "<*>")
	
	// Replace IP addresses
	ipRe := regexp.MustCompile(`\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`)
	template = ipRe.ReplaceAllString(template, "<*>")
	
	return template
}

// sortByFrequency sorts map by frequency and returns top N
func (te *TemplateExtractor) sortByFrequency(m map[string]int, limit int) map[string]int {
	type kv struct {
		Key   string
		Value int
	}
	
	var sorted []kv
	for k, v := range m {
		sorted = append(sorted, kv{k, v})
	}
	
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Value > sorted[j].Value
	})
	
	result := make(map[string]int)
	for i, kv := range sorted {
		if limit > 0 && i >= limit {
			break
		}
		result[kv.Key] = kv.Value
	}
	
	return result
}
