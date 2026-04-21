package learner

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"migrate/internal/models"
)

// TemporalExtractor extracts time-based patterns
type TemporalExtractor struct{}

// NewTemporalExtractor creates a new temporal extractor
func NewTemporalExtractor() *TemporalExtractor {
	return &TemporalExtractor{}
}

// Extract extracts temporal patterns
func (te *TemporalExtractor) Extract(logs []models.LogEntry) models.TemporalPatterns {
	return models.TemporalPatterns{
		PeriodicEvents: te.findPeriodicEvents(logs),
		EventClusters:  te.findEventClusters(logs),
		TimeOfDay:      te.findTimeOfDayPatterns(logs),
		GapsAndBursts:  te.findGapsAndBursts(logs),
	}
}

// findPeriodicEvents finds events that occur at regular intervals
func (te *TemporalExtractor) findPeriodicEvents(logs []models.LogEntry) map[string]models.PeriodicEvent {
	eventTimes := make(map[string][]time.Time)
	
	for _, log := range logs {
		if log.Timestamp.IsZero() {
			continue
		}
		
		message, ok := log.Fields["message"].(string)
		if !ok {
			continue
		}
		
		// Look for periodic events
		if strings.Contains(message, "TIME_TICK") {
			eventTimes["TIME_TICK"] = append(eventTimes["TIME_TICK"], log.Timestamp)
		}
		if strings.Contains(message, "REPORT") {
			eventTimes["REPORT"] = append(eventTimes["REPORT"], log.Timestamp)
		}
	}
	
	periodic := make(map[string]models.PeriodicEvent)
	for event, times := range eventTimes {
		if len(times) > 5 {
			intervals := make([]float64, 0)
			for i := 0; i < len(times)-1; i++ {
				interval := times[i+1].Sub(times[i]).Seconds()
				intervals = append(intervals, interval)
			}
			
			if len(intervals) > 0 {
				sum := 0.0
				min, max := intervals[0], intervals[0]
				for _, v := range intervals {
					sum += v
					if v < min {
						min = v
					}
					if v > max {
						max = v
					}
				}
				
				avg := sum / float64(len(intervals))
				consistency := "medium"
				if max-min < 5 {
					consistency = "high"
				}
				
				periodic[event] = models.PeriodicEvent{
					Frequency:           formatDuration(avg),
					Samples:             len(times),
					IntervalConsistency: consistency,
				}
			}
		}
	}
	
	return periodic
}

// findEventClusters finds events that happen together
func (te *TemporalExtractor) findEventClusters(logs []models.LogEntry) []models.EventCluster {
	clusters := make([]models.EventCluster, 0)
	
	for i := 0; i < len(logs)-1; i++ {
		if logs[i].Timestamp.IsZero() {
			continue
		}
		
		cluster := []models.LogEntry{logs[i]}
		j := i + 1
		
		for j < len(logs) {
			if logs[j].Timestamp.IsZero() {
				j++
				continue
			}
			
			diff := logs[j].Timestamp.Sub(logs[i].Timestamp).Seconds()
			if diff < 2 {
				cluster = append(cluster, logs[j])
				j++
			} else {
				break
			}
		}
		
		if len(cluster) > 3 {
			messages := make([]string, 0)
			for k := 0; k < len(cluster) && k < 5; k++ {
				if msg, ok := cluster[k].Fields["message"].(string); ok {
					if len(msg) > 30 {
						msg = msg[:30]
					}
					messages = append(messages, msg)
				}
			}
			
			clusters = append(clusters, models.EventCluster{
				Time:           logs[i].Timestamp.Format(time.RFC3339),
				Size:           len(cluster),
				SampleMessages: messages,
			})
		}
		
		i = j - 1
	}
	
	// Return top 10
	if len(clusters) > 10 {
		clusters = clusters[:10]
	}
	
	return clusters
}

// findTimeOfDayPatterns finds patterns based on time of day
func (te *TemporalExtractor) findTimeOfDayPatterns(logs []models.LogEntry) models.TimeOfDayPattern {
	hourlyCounts := make(map[int]int)
	total := 0
	
	for _, log := range logs {
		if !log.Timestamp.IsZero() {
			hour := log.Timestamp.Hour()
			hourlyCounts[hour]++
			total++
		}
	}
	
	// Calculate distribution
	distribution := make(map[int]float64)
	for hour, count := range hourlyCounts {
		if total > 0 {
			distribution[hour] = float64(count) / float64(total)
		}
	}
	
	// Find peak hours
	type hourCount struct {
		hour  int
		count int
	}
	peaks := make([]hourCount, 0)
	for h, c := range hourlyCounts {
		peaks = append(peaks, hourCount{h, c})
	}
	
	sort.Slice(peaks, func(i, j int) bool {
		return peaks[i].count > peaks[j].count
	})
	
	peakHours := make([]models.PeakHour, 0)
	for i := 0; i < len(peaks) && i < 3; i++ {
		peakHours = append(peakHours, models.PeakHour{
			Hour:  peaks[i].hour,
			Count: peaks[i].count,
		})
	}
	
	return models.TimeOfDayPattern{
		HourlyDistribution: distribution,
		PeakHours:          peakHours,
	}
}

// findGapsAndBursts finds long gaps and high-activity bursts
func (te *TemporalExtractor) findGapsAndBursts(logs []models.LogEntry) models.GapsAndBursts {
	if len(logs) < 2 {
		return models.GapsAndBursts{}
	}
	
	intervals := make([]float64, 0)
	gaps := 0
	minInterval := 999999.0
	maxGap := 0.0
	sum := 0.0
	
	for i := 0; i < len(logs)-1; i++ {
		if logs[i].Timestamp.IsZero() || logs[i+1].Timestamp.IsZero() {
			continue
		}
		
		interval := logs[i+1].Timestamp.Sub(logs[i].Timestamp).Seconds()
		intervals = append(intervals, interval)
		sum += interval
		
		if interval < minInterval {
			minInterval = interval
		}
		if interval > maxGap {
			maxGap = interval
		}
		if interval > 60 {
			gaps++
		}
	}
	
	avgInterval := 0.0
	if len(intervals) > 0 {
		avgInterval = sum / float64(len(intervals))
	}
	
	// Find bursts
	bursts := make([]models.Burst, 0)
	i := 0
	for i < len(logs) {
		if logs[i].Timestamp.IsZero() {
			i++
			continue
		}
		
		burstStart := i
		burstEnd := i
		
		for burstEnd < len(logs)-1 {
			if logs[burstEnd+1].Timestamp.IsZero() {
				break
			}
			nextInterval := logs[burstEnd+1].Timestamp.Sub(logs[burstEnd].Timestamp).Seconds()
			if nextInterval < 1 {
				burstEnd++
			} else {
				break
			}
		}
		
		if burstEnd-burstStart > 5 {
			bursts = append(bursts, models.Burst{
				Start:       logs[burstStart].Timestamp.Format(time.RFC3339),
				DurationSec: logs[burstEnd].Timestamp.Sub(logs[burstStart].Timestamp).Seconds(),
				LogCount:    burstEnd - burstStart + 1,
			})
		}
		
		i = burstEnd + 1
	}
	
	// Return top 5 bursts
	if len(bursts) > 5 {
		bursts = bursts[:5]
	}
	
	return models.GapsAndBursts{
		AvgIntervalSec: avgInterval,
		MaxGapSec:      maxGap,
		MinIntervalSec: minInterval,
		GapsOver60s:    gaps,
		Bursts:         bursts,
	}
}

// formatDuration formats seconds into readable string
func formatDuration(seconds float64) string {
	if seconds < 60 {
		return "every " + formatFloat(seconds) + " seconds"
	} else if seconds < 3600 {
		return "every " + formatFloat(seconds/60) + " minutes"
	}
	return "every " + formatFloat(seconds/3600) + " hours"
}

// formatFloat formats a float to string with appropriate precision
func formatFloat(f float64) string {
	if f == float64(int(f)) {
		return fmt.Sprintf("%.0f", f)
	}
	return fmt.Sprintf("%.1f", f)
}
