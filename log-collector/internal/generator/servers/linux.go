package servers

import (
	"fmt"
	"math/rand"
	"os"
	"path/filepath"

	"migrate/internal/generator"
)

// LinuxServer generates Linux system logs
type LinuxServer struct {
	*generator.BaseServer
	eventProbabilities map[string]float64
}

// NewLinuxServer creates a new Linux server
func NewLinuxServer() *LinuxServer {
	patternsFile := "linux_patterns.json"
	if _, err := os.Stat(patternsFile); os.IsNotExist(err) {
		patternsFile = filepath.Join("..", "patterns", "linux_patterns.json")
	}
	
	ls := &LinuxServer{
		BaseServer: generator.NewBaseServer("linux", "linux_server.log", patternsFile),
		eventProbabilities: map[string]float64{
			"sshd_check_pass": 0.25,
			"sshd_auth_fail":  0.35,
			"sshd_session":    0.10,
			"ftp_connection":  0.15,
			"su_session":      0.08,
			"system_event":    0.05,
			"service_event":   0.02,
		},
	}
	
	// Initialize Linux-specific state
	ls.State["pid"] = 1000
	ls.State["sshd_pid"] = 19900
	ls.State["ftpd_pid"] = 29000
	ls.State["klogind_pid"] = 19200
	ls.State["su_pid"] = 21000
	ls.State["users"] = []string{"root", "test", "guest", "cyrus", "news", "unknown"}
	ls.State["current_user"] = "root"
	ls.State["auth_attempts"] = 0
	ls.State["failed_logins"] = 0
	ls.State["ips"] = []string{
		"218.188.2.4",
		"220-135-151-1.hinet-ip.hinet.net",
		"061092085098.ctinets.com",
		"d211-116-254-214.rev.krline.net",
		"adsl-70-242-75-179.dsl.ksc2mo.swbell.net",
		"massive.merukuru.org",
		"zummit.com",
		"c9063558.virtua.com.br",
	}
	
	ls.MaxLogs = 20
	
	fmt.Printf("   🐧 Linux server initialized with %d patterns\n", 
		len(ls.Patterns.Templates.ByFrequency))
	
	return ls
}

// GenerateLogLine generates Linux-specific log
func (ls *LinuxServer) GenerateLogLine() map[string]interface{} {
	rand := rand.Float64()
	
	if rand < ls.eventProbabilities["sshd_check_pass"] {
		return ls.generateSSHDCheckPass()
	} else if rand < ls.eventProbabilities["sshd_check_pass"]+ls.eventProbabilities["sshd_auth_fail"] {
		return ls.generateSSHDAuthFail()
	} else if rand < ls.eventProbabilities["sshd_check_pass"]+ls.eventProbabilities["sshd_auth_fail"]+ls.eventProbabilities["sshd_session"] {
		return ls.generateSSHDSession()
	} else if rand < ls.eventProbabilities["sshd_check_pass"]+ls.eventProbabilities["sshd_auth_fail"]+ls.eventProbabilities["sshd_session"]+ls.eventProbabilities["ftp_connection"] {
		return ls.generateFTPConnection()
	} else if rand < ls.eventProbabilities["sshd_check_pass"]+ls.eventProbabilities["sshd_auth_fail"]+ls.eventProbabilities["sshd_session"]+ls.eventProbabilities["ftp_connection"]+ls.eventProbabilities["su_session"] {
		return ls.generateSUSession()
	} else if rand < ls.eventProbabilities["sshd_check_pass"]+ls.eventProbabilities["sshd_auth_fail"]+ls.eventProbabilities["sshd_session"]+ls.eventProbabilities["ftp_connection"]+ls.eventProbabilities["su_session"]+ls.eventProbabilities["system_event"] {
		return ls.generateSystemEvent()
	}
	
	return ls.generateServiceEvent()
}

// generateSSHDCheckPass generates SSH check pass events
func (ls *LinuxServer) generateSSHDCheckPass() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	sshdPid := ls.State["sshd_pid"].(int) + 1
	ls.State["pid"] = pid
	ls.State["sshd_pid"] = sshdPid
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": "combo",
		"process":   fmt.Sprintf("sshd(pam_unix)[%d]", sshdPid),
		"message":   "check pass; user unknown",
	}
}

// generateSSHDAuthFail generates authentication failure events
func (ls *LinuxServer) generateSSHDAuthFail() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	sshdPid := ls.State["sshd_pid"].(int) + 1
	failedLogins := ls.State["failed_logins"].(int) + 1
	ls.State["pid"] = pid
	ls.State["sshd_pid"] = sshdPid
	ls.State["failed_logins"] = failedLogins
	
	ips := ls.State["ips"].([]string)
	ip := ips[rand.Intn(len(ips))]
	
	var message string
	if rand.Float64() < 0.5 {
		message = fmt.Sprintf("authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=%s", ip)
	} else {
		users := ls.State["users"].([]string)
		user := users[rand.Intn(len(users))]
		message = fmt.Sprintf("authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=%s  user=%s", ip, user)
	}
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": "combo",
		"process":   fmt.Sprintf("sshd(pam_unix)[%d]", sshdPid),
		"message":   message,
	}
}

// generateSSHDSession generates session opened/closed events
func (ls *LinuxServer) generateSSHDSession() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	sshdPid := ls.State["sshd_pid"].(int) + 1
	ls.State["pid"] = pid
	ls.State["sshd_pid"] = sshdPid
	
	users := []string{"test", "root"}
	user := users[rand.Intn(len(users))]
	uid := "509"
	if user == "root" {
		uid = "0"
	}
	
	var message string
	if rand.Float64() < 0.5 {
		message = fmt.Sprintf("session opened for user %s by (uid=%s)", user, uid)
	} else {
		message = fmt.Sprintf("session closed for user %s", user)
	}
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": "combo",
		"process":   fmt.Sprintf("sshd(pam_unix)[%d]", sshdPid),
		"message":   message,
	}
}

// generateFTPConnection generates FTP connection events
func (ls *LinuxServer) generateFTPConnection() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	ftpdPid := ls.State["ftpd_pid"].(int) + 1
	ls.State["pid"] = pid
	ls.State["ftpd_pid"] = ftpdPid
	
	ips := ls.State["ips"].([]string)
	ip := ips[rand.Intn(len(ips))]
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": "combo",
		"process":   fmt.Sprintf("ftpd[%d]", ftpdPid),
		"message":   fmt.Sprintf("connection from %s () at some time", ip),
	}
}

// generateSUSession generates su (switch user) events
func (ls *LinuxServer) generateSUSession() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	suPid := ls.State["su_pid"].(int) + 1
	ls.State["pid"] = pid
	ls.State["su_pid"] = suPid
	
	users := []string{"cyrus", "news", "root"}
	targetUser := users[rand.Intn(len(users))]
	
	var message string
	if rand.Float64() < 0.5 {
		message = fmt.Sprintf("session opened for user %s by (uid=0)", targetUser)
	} else {
		message = fmt.Sprintf("session closed for user %s", targetUser)
	}
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": "combo",
		"process":   fmt.Sprintf("su(pam_unix)[%d]", suPid),
		"message":   message,
	}
}

// generateSystemEvent generates system events
func (ls *LinuxServer) generateSystemEvent() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	ls.State["pid"] = pid
	
	eventType := rand.Intn(4)
	
	switch eventType {
	case 0: // cups
		if rand.Float64() < 0.5 {
			return map[string]interface{}{
				"timestamp": ls.GenerateTimestamp(),
				"component": "combo",
				"process":   "cups",
				"message":   "cupsd shutdown succeeded",
			}
		}
		return map[string]interface{}{
			"timestamp": ls.GenerateTimestamp(),
			"component": "combo",
			"process":   "cups",
			"message":   "cupsd startup succeeded",
		}
	case 1: // syslog
		return map[string]interface{}{
			"timestamp": ls.GenerateTimestamp(),
			"component": "combo",
			"process":   "syslogd 1.4.1",
			"message":   "restart.",
		}
	case 2: // logrotate
		return map[string]interface{}{
			"timestamp": ls.GenerateTimestamp(),
			"component": "combo",
			"process":   "logrotate",
			"message":   "ALERT exited abnormally with [1]",
		}
	default: // kernel
		kernelMsgs := []string{
			"Linux version 2.6.5-1.358",
			"BIOS-provided physical RAM map:",
			"BIOS-e820: 0000000000000000 - 00000000000a0000 (usable)",
			"Detected 731.219 MHz processor.",
			"CPU: Intel Pentium III (Coppermine) stepping 06",
			"Checking 'hlt' instruction... OK.",
		}
		return map[string]interface{}{
			"timestamp": ls.GenerateTimestamp(),
			"component": "combo",
			"process":   "kernel",
			"message":   kernelMsgs[rand.Intn(len(kernelMsgs))],
		}
	}
}

// generateServiceEvent generates service start/stop events
func (ls *LinuxServer) generateServiceEvent() map[string]interface{} {
	pid := ls.State["pid"].(int) + 1
	ls.State["pid"] = pid
	
	services := []string{"portmap", "nfslock", "rpcidmapd", "bluetooth", "irqbalance", "random"}
	service := services[rand.Intn(len(services))]
	
	return map[string]interface{}{
		"timestamp": ls.GenerateTimestamp(),
		"component": service,
		"process":   "",
		"message":   fmt.Sprintf("%s startup succeeded", service),
	}
}
