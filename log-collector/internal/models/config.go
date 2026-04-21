package models

// ServerConfig defines the configuration for a server type
type ServerConfig struct {
	Server         string                 `json:"server"`
	LogFormat      LogFormat              `json:"log_format"`
	StateVariables map[string]StateVar    `json:"state_variables"`
	CausalChains   map[string][]string    `json:"causal_chains"`
}

type LogFormat struct {
	Delimiter       string   `json:"delimiter"`
	Parts           []string `json:"parts"`
	TimestampFormat string   `json:"timestamp_format"`
}

type StateVar struct {
	Pattern string `json:"pattern"`
	Type    string `json:"type"`
}

// DaemonConfig defines the daemon configuration
type DaemonConfig struct {
	Servers []ServerMapping `json:"servers"`
}

type ServerMapping struct {
	LogFile  string `json:"log_file"`
	ServerID string `json:"server_id"`
}

// ServerInstance represents a server instance in list.json
type ServerInstance struct {
	SID      string `json:"sid"`
	Type     string `json:"type"`
	Instance int    `json:"instance"`
	Status   string `json:"status"`
}
