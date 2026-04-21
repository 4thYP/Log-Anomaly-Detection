package servers

import (
	"fmt"
	"math/rand"
	"os"
	"path/filepath"

	"migrate/internal/generator"
)

// WindowsServer generates Windows system logs
type WindowsServer struct {
	*generator.BaseServer
	eventProbabilities map[string]float64
}

// NewWindowsServer creates a new Windows server
func NewWindowsServer() *WindowsServer {
	patternsFile := "windows_patterns.json"
	if _, err := os.Stat(patternsFile); os.IsNotExist(err) {
		patternsFile = filepath.Join("..", "patterns", "windows_patterns.json")
	}
	
	ws := &WindowsServer{
		BaseServer: generator.NewBaseServer("windows", "windows_server.log", patternsFile),
		eventProbabilities: map[string]float64{
			"cbs_event":         0.35,
			"csi_event":         0.30,
			"trusted_installer": 0.15,
			"sqm_event":         0.10,
			"transaction_event": 0.10,
		},
	}
	
	// Initialize Windows-specific state
	ws.State["cbs_session"] = 30546173
	ws.State["csi_transaction"] = 1
	ws.State["reboot_mark"] = 0
	ws.State["package_counter"] = 0
	
	ws.MaxLogs = 20
	
	fmt.Printf("   🪟 Windows server initialized with %d patterns\n", 
		len(ws.Patterns.Templates.ByFrequency))
	
	return ws
}

// GenerateLogLine generates Windows-specific log
func (ws *WindowsServer) GenerateLogLine() map[string]interface{} {
	rand := rand.Float64()
	
	if rand < ws.eventProbabilities["cbs_event"] {
		return ws.generateCBSEvent()
	} else if rand < ws.eventProbabilities["cbs_event"]+ws.eventProbabilities["csi_event"] {
		return ws.generateCSIEvent()
	} else if rand < ws.eventProbabilities["cbs_event"]+ws.eventProbabilities["csi_event"]+ws.eventProbabilities["trusted_installer"] {
		return ws.generateTrustedInstallerEvent()
	} else if rand < ws.eventProbabilities["cbs_event"]+ws.eventProbabilities["csi_event"]+ws.eventProbabilities["trusted_installer"]+ws.eventProbabilities["sqm_event"] {
		return ws.generateSQMEvent()
	}
	
	return ws.generateTransactionEvent()
}

// generateCBSEvent generates CBS events
func (ws *WindowsServer) generateCBSEvent() map[string]interface{} {
	cbsSession := ws.State["cbs_session"].(int) + rand.Intn(100) + 1
	ws.State["cbs_session"] = cbsSession
	
	eventType := rand.Intn(5)
	
	switch eventType {
	case 0: // startup
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "Starting TrustedInstaller initialization.",
		}
	case 1: // shutdown
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "Ending TrustedInstaller main loop.",
		}
	case 2: // package
		packageCounter := ws.State["package_counter"].(int) + 1
		ws.State["package_counter"] = packageCounter
		
		packages := []string{
			"Package_for_KB3121255~31bf3856ad364e35~amd64~~6.1.1.0",
			"Package_for_KB3060716~31bf3856ad364e35~amd64~~6.1.1.0",
			"Package_for_KB3177186~31bf3856ad364e35~amd64~~6.1.1.1",
			"Package_for_KB3086255~31bf3856ad364e35~amd64~~6.1.1.0",
			"Package_for_KB3146706~31bf3856ad364e35~amd64~~6.1.1.2",
		}
		packageName := packages[rand.Intn(len(packages))]
		state := []string{"112", "80", "0"}[rand.Intn(3)]
		
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   fmt.Sprintf("Read out cached package applicability for package: %s, ApplicableState: %s, CurrentState:%s", packageName, state, state),
		}
	case 3: // service
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "TrustedInstaller service starts successfully.",
		}
	default: // loading
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "Loaded Servicing Stack v6.1.7601.23505 with Core: C:\\Windows\\winsxs\\amd64_microsoft-windows-servicingstack_31bf3856ad364e35_6.1.7601.23505_none_681aa442f6fed7f0\\cbscore.dll",
		}
	}
}

// generateCSIEvent generates CSI events
func (ws *WindowsServer) generateCSIEvent() map[string]interface{} {
	csiTransaction := ws.State["csi_transaction"].(int) + 1
	ws.State["csi_transaction"] = csiTransaction
	
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // initialize
		storeID := rand.Intn(49000000) + 1000000
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CSI",
			"level":     "Info",
			"message":   fmt.Sprintf("%08d CSI Store %d (0x%x) initialized", csiTransaction, storeID, storeID),
		}
	case 1: // transaction
		seq := rand.Intn(10) + 1
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CSI",
			"level":     "Info",
			"message":   fmt.Sprintf("%08d Creating NT transaction (seq %d), objectname [6]\"(null)\"", csiTransaction, seq),
		}
	case 2: // perf
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CSI",
			"level":     "Info",
			"message":   fmt.Sprintf("%08d CSI perf trace:", csiTransaction),
		}
	default: // wcp
		version := fmt.Sprintf("%d.%d.%d.%d", rand.Intn(10), rand.Intn(10), rand.Intn(10), rand.Intn(10))
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CSI",
			"level":     "Info",
			"message":   fmt.Sprintf("%08d@2016/9/27:20:30:31.455 WcpInitialize (wcp.dll version %s) called", csiTransaction, version),
		}
	}
}

// generateTrustedInstallerEvent generates TrustedInstaller events
func (ws *WindowsServer) generateTrustedInstallerEvent() map[string]interface{} {
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "Starting the TrustedInstaller main loop.",
		}
	case 1:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "Ending the TrustedInstaller main loop.",
		}
	case 2:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "NonStart: Checking to ensure startup processing was not required.",
		}
	default:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "No startup processing required, TrustedInstaller service was not set as autostart, or else a reboot is still pending.",
		}
	}
}

// generateSQMEvent generates SQM events
func (ws *WindowsServer) generateSQMEvent() map[string]interface{} {
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "SQM: Initializing online with Windows opt-in: False",
		}
	case 1:
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "SQM: Requesting upload of all unsent reports.",
		}
	case 2:
		files := rand.Intn(11)
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   fmt.Sprintf("SQM: Queued %d file(s) for upload with pattern: C:\\Windows\\servicing\\sqm\\*_all.sqm, flags: 0x6", files),
		}
	default:
		rebootMark := ws.State["reboot_mark"].(int) + 1
		ws.State["reboot_mark"] = rebootMark
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CBS",
			"level":     "Info",
			"message":   "SQM: Failed to start standard sample upload. [HRESULT = 0x80004005 - E_FAIL]",
		}
	}
}

// generateTransactionEvent generates NT transaction events
func (ws *WindowsServer) generateTransactionEvent() map[string]interface{} {
	csiTransaction := ws.State["csi_transaction"].(int)
	seq := rand.Intn(5) + 1
	handle := fmt.Sprintf("@0x%x", rand.Intn(900)+100)
	
	if rand.Float64() < 0.5 {
		return map[string]interface{}{
			"timestamp": ws.GenerateTimestamp(),
			"component": "CSI",
			"level":     "Info",
			"message":   fmt.Sprintf("%08d Created NT transaction (seq %d) result 0x00000000, handle %s", csiTransaction, seq, handle),
		}
	}
	
	return map[string]interface{}{
		"timestamp": ws.GenerateTimestamp(),
		"component": "CSI",
		"level":     "Info",
		"message":   fmt.Sprintf("%08d ICSITransaction::Commit calling IStorePendingTransaction::Apply - coldpatching=FALSE applyflags=7", csiTransaction),
	}
}
