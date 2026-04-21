package servers

import (
	"fmt"
	"math/rand"
	"os"
	"path/filepath"

	"migrate/internal/generator"
)

// ZookeeperServer generates Zookeeper distributed coordination logs
type ZookeeperServer struct {
	*generator.BaseServer
	eventProbabilities map[string]float64
}

// NewZookeeperServer creates a new Zookeeper server
func NewZookeeperServer() *ZookeeperServer {
	patternsFile := "zookeeper_patterns.json"
	if _, err := os.Stat(patternsFile); os.IsNotExist(err) {
		patternsFile = filepath.Join("..", "patterns", "zookeeper_patterns.json")
	}
	
	zs := &ZookeeperServer{
		BaseServer: generator.NewBaseServer("zookeeper", "zookeeper_server.log", patternsFile),
		eventProbabilities: map[string]float64{
			"quorum_event":     0.25,
			"connection_event": 0.30,
			"session_event":    0.20,
			"worker_event":     0.15,
			"notification":     0.10,
		},
	}
	
	// Initialize Zookeeper-specific state
	zs.State["myid"] = rand.Intn(3) + 1
	zs.State["zxid"] = 0x100000000
	zs.State["session_id"] = 0x14ed93111f20000
	zs.State["epoch"] = 1
	zs.State["connection_counter"] = 10000
	zs.State["peers"] = []int{1, 2, 3}
	
	zs.MaxLogs = 20
	
	fmt.Printf("   🦓 Zookeeper server initialized with myid=%v\n", zs.State["myid"])
	
	return zs
}

// GenerateLogLine generates Zookeeper-specific log
func (zs *ZookeeperServer) GenerateLogLine() map[string]interface{} {
	rand := rand.Float64()
	timestamp := zs.GenerateTimestamp()
	
	if rand < zs.eventProbabilities["quorum_event"] {
		return zs.generateQuorumEvent(timestamp)
	} else if rand < zs.eventProbabilities["quorum_event"]+zs.eventProbabilities["connection_event"] {
		return zs.generateConnectionEvent(timestamp)
	} else if rand < zs.eventProbabilities["quorum_event"]+zs.eventProbabilities["connection_event"]+zs.eventProbabilities["session_event"] {
		return zs.generateSessionEvent(timestamp)
	} else if rand < zs.eventProbabilities["quorum_event"]+zs.eventProbabilities["connection_event"]+zs.eventProbabilities["session_event"]+zs.eventProbabilities["worker_event"] {
		return zs.generateWorkerEvent(timestamp)
	}
	
	return zs.generateNotificationEvent(timestamp)
}

// generateQuorumEvent generates QuorumPeer events
func (zs *ZookeeperServer) generateQuorumEvent(timestamp string) map[string]interface{} {
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // looking
		epoch := zs.State["epoch"].(int) + 1
		zs.State["epoch"] = epoch
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "QuorumPeer",
			"level":     "INFO",
			"message":   "LOOKING",
		}
	case 1: // leading
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "QuorumPeer",
			"level":     "INFO",
			"message":   "LEADING",
		}
	case 2: // following
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "QuorumPeer",
			"level":     "INFO",
			"message":   fmt.Sprintf("FOLLOWING - LEADER ELECTION TOOK - %d", rand.Intn(490)+10),
		}
	default: // election
		zxid := zs.State["zxid"].(int) + rand.Intn(100) + 1
		zs.State["zxid"] = zxid
		myid := zs.State["myid"].(int)
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "FastLeaderElection",
			"level":     "INFO",
			"message":   fmt.Sprintf("New election. My id = %d, proposed zxid=0x%x", myid, zxid),
		}
	}
}

// generateConnectionEvent generates connection events
func (zs *ZookeeperServer) generateConnectionEvent(timestamp string) map[string]interface{} {
	connCounter := zs.State["connection_counter"].(int) + 1
	zs.State["connection_counter"] = connCounter
	
	peers := zs.State["peers"].([]int)
	peer := peers[rand.Intn(len(peers))]
	ip := fmt.Sprintf("10.10.34.%d", rand.Intn(40)+11)
	port := rand.Intn(28000) + 32000
	
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // accepted
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "NIOServerCxn.Factory",
			"level":     "INFO",
			"message":   fmt.Sprintf("Accepted socket connection from /%s:%d", ip, port),
		}
	case 1: // closed
		sessionID := zs.State["session_id"].(int)
		zs.State["session_id"] = sessionID + rand.Intn(10) + 1
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "NIOServerCxn.Factory",
			"level":     "INFO",
			"message":   fmt.Sprintf("Closed socket connection for client /%s:%d which had sessionid 0x%x", ip, port, sessionID),
		}
	case 2: // broken
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "NIOServerCxn.Factory",
			"level":     "WARN",
			"message":   "caught end of stream exception",
		}
	default: // received
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": fmt.Sprintf("/10.10.34.%d:3888", peer),
			"level":     "INFO",
			"message":   fmt.Sprintf("Received connection request /10.10.34.%d:%d", peer, port),
		}
	}
}

// generateSessionEvent generates session events
func (zs *ZookeeperServer) generateSessionEvent(timestamp string) map[string]interface{} {
	sessionID := zs.State["session_id"].(int)
	zs.State["session_id"] = sessionID + rand.Intn(5) + 1
	
	timeout := 10000
	if rand.Float64() < 0.5 {
		timeout = 20000
	}
	
	ip := fmt.Sprintf("10.10.34.%d", rand.Intn(40)+11)
	port := rand.Intn(28000) + 32000
	
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // established
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "CommitProcessor",
			"level":     "INFO",
			"message":   fmt.Sprintf("Established session 0x%x with negotiated timeout %d for client /%s:%d", sessionID, timeout, ip, port),
		}
	case 1: // expiring
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "SessionTracker",
			"level":     "INFO",
			"message":   fmt.Sprintf("Expiring session 0x%x, timeout of %dms exceeded", sessionID, timeout),
		}
	case 2: // terminated
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "ProcessThread",
			"level":     "INFO",
			"message":   fmt.Sprintf("Processed session termination for sessionid: 0x%x", sessionID),
		}
	default: // renew
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": "NIOServerCxn.Factory",
			"level":     "INFO",
			"message":   fmt.Sprintf("Client attempting to renew session 0x%x at /%s:%d", sessionID, ip, port),
		}
	}
}

// generateWorkerEvent generates SendWorker/RecvWorker events
func (zs *ZookeeperServer) generateWorkerEvent(timestamp string) map[string]interface{} {
	peers := zs.State["peers"].([]int)
	peer := peers[rand.Intn(len(peers))]
	myid := zs.State["myid"].(int)
	
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // send_leave
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": fmt.Sprintf("SendWorker:%d", peer),
			"level":     "WARN",
			"message":   "Send worker leaving thread",
		}
	case 1: // recv_interrupt
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": fmt.Sprintf("RecvWorker:%d", peer),
			"level":     "WARN",
			"message":   "Interrupting SendWorker",
		}
	case 2: // send_interrupt
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": fmt.Sprintf("SendWorker:%d", peer),
			"level":     "WARN",
			"message":   "Interrupted while waiting for message on queue",
		}
	default: // connection_broken
		return map[string]interface{}{
			"timestamp": timestamp,
			"component": fmt.Sprintf("RecvWorker:%d", peer),
			"level":     "WARN",
			"message":   fmt.Sprintf("Connection broken for id %d, my id = %d, error = ", peer, myid),
		}
	}
}

// generateNotificationEvent generates FastLeaderElection notifications
func (zs *ZookeeperServer) generateNotificationEvent(timestamp string) map[string]interface{} {
	zxid := zs.State["zxid"].(int) + rand.Intn(50) + 1
	zs.State["zxid"] = zxid
	
	peers := zs.State["peers"].([]int)
	leader := peers[rand.Intn(len(peers))]
	epoch := zs.State["epoch"].(int)
	
	states := []string{"LOOKING", "FOLLOWING", "LEADING"}
	state := states[rand.Intn(len(states))]
	
	return map[string]interface{}{
		"timestamp": timestamp,
		"component": "WorkerReceiver",
		"level":     "INFO",
		"message":   fmt.Sprintf("Notification: %d (n.leader), 0x%x (n.zxid), 0x%x (n.round), %s (n.state), %d (n.sid), 0x%x (n.peerEPoch), %s (my state)", leader, zxid, epoch, state, leader, epoch, state),
	}
}
