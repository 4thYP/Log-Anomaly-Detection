package models

// PatternFile represents the complete pattern output from learner
type PatternFile struct {
	Server             string                       `json:"server"`
	Templates          Templates                    `json:"templates"`
	Components         Components                   `json:"components"`
	StateMachine       StateMachine                 `json:"state_machine"`
	CausalChains       CausalChains                 `json:"causal_chains"`
	ValueRelationships ValueRelationships           `json:"value_relationships"`
	TemporalPatterns   TemporalPatterns             `json:"temporal_patterns"`
	Statistics         Statistics                   `json:"statistics"`
}

type Templates struct {
	ByFrequency    map[string]int `json:"by_frequency"`
	TotalTemplates int            `json:"total_templates"`
}

type Components struct {
	ByFrequency      map[string]int `json:"by_frequency"`
	TotalComponents  int            `json:"total_components"`
}

type StateMachine struct {
	Counters   map[string]Counter   `json:"counters"`
	Flags      map[string]int       `json:"flags"`
	Sequences  SequenceInfo         `json:"sequences"`
	Values     map[string]ValueInfo `json:"values"`
}

type Counter struct {
	Type    string `json:"type"`
	Samples []int  `json:"samples"`
}

type SequenceInfo struct {
	CommonTransitions map[string]int `json:"common_transitions"`
	TotalSequences    int            `json:"total_sequences"`
}

type ValueInfo struct {
	Min     int     `json:"min"`
	Max     int     `json:"max"`
	Avg     float64 `json:"avg"`
	Samples int     `json:"samples"`
}

type CausalChains struct {
	Chains                []Chain                      `json:"chains"`
	TransitionProbabilities map[string]map[string]float64 `json:"transition_probabilities"`
	CommonPatterns        []Pattern                    `json:"common_patterns"`
	TotalChains           int                          `json:"total_chains"`
}

type Chain struct {
	Component string `json:"component"`
	From      string `json:"from"`
	To        string `json:"to"`
	TimeDiff  int    `json:"time_diff"`
}

type Pattern struct {
	Pattern   []string `json:"pattern"`
	Frequency int      `json:"frequency"`
}

type ValueRelationships struct {
	Correlations  []Correlation            `json:"correlations"`
	Formulas      []Formula                `json:"formulas"`
	Distributions map[string]Distribution  `json:"distributions"`
}

type Correlation struct {
	Value1       string  `json:"value1"`
	Value2       string  `json:"value2"`
	Relationship string  `json:"relationship"`
	Confidence   string  `json:"confidence"`
}

type Formula struct {
	Variable    string `json:"variable"`
	Pattern     string `json:"pattern"`
	Value       int    `json:"value,omitempty"`
	Description string `json:"description"`
}

type Distribution struct {
	Min           int     `json:"min"`
	Max           int     `json:"max"`
	Avg           float64 `json:"avg"`
	Median        int     `json:"median"`
	Count         int     `json:"count"`
	UniqueValues  int     `json:"unique_values"`
	StdDev        float64 `json:"std_dev,omitempty"`
}

type TemporalPatterns struct {
	PeriodicEvents map[string]PeriodicEvent `json:"periodic_events"`
	EventClusters  []EventCluster           `json:"event_clusters"`
	TimeOfDay      TimeOfDayPattern         `json:"time_of_day"`
	GapsAndBursts  GapsAndBursts            `json:"gaps_and_bursts"`
}

type PeriodicEvent struct {
	Frequency           string  `json:"frequency"`
	Samples             int     `json:"samples"`
	IntervalConsistency string  `json:"interval_consistency"`
}

type EventCluster struct {
	Time           string   `json:"time"`
	Size           int      `json:"size"`
	SampleMessages []string `json:"sample_messages"`
}

type TimeOfDayPattern struct {
	HourlyDistribution map[int]float64  `json:"hourly_distribution"`
	PeakHours          []PeakHour       `json:"peak_hours"`
}

type PeakHour struct {
	Hour  int `json:"hour"`
	Count int `json:"count"`
}

type GapsAndBursts struct {
	AvgIntervalSec float64 `json:"avg_interval_sec"`
	MaxGapSec      float64 `json:"max_gap_sec"`
	MinIntervalSec float64 `json:"min_interval_sec"`
	GapsOver60s    int     `json:"gaps_over_60s"`
	Bursts         []Burst `json:"bursts"`
}

type Burst struct {
	Start       string  `json:"start"`
	DurationSec float64 `json:"duration_sec"`
	LogCount    int     `json:"log_count"`
}

type Statistics struct {
	TotalLogs         int                    `json:"total_logs"`
	UniqueComponents  int                    `json:"unique_components"`
	UniqueTemplates   int                    `json:"unique_templates"`
	TimeSpan          map[string]string      `json:"time_span"`
	AvgLogsPerMinute  string                 `json:"avg_logs_per_minute"`
}
