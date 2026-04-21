package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"migrate/internal/models"
	"migrate/internal/orchestrator"
)

var processes []*exec.Cmd

func main() {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGINT, syscall.SIGTERM)
	
	go func() {
		<-signalChan
		fmt.Println("\n\n🛑 Stopping all servers...")
		for _, p := range processes {
			if p.Process != nil {
				p.Process.Kill()
			}
		}
		time.Sleep(2 * time.Second)
		fmt.Println("✅ All servers stopped.")
		os.Exit(0)
	}()
	
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("🚀 LOG INTELLIGENT SYSTEM - SERVER MANAGER")
	fmt.Println(strings.Repeat("=", 80))
	
	registry := orchestrator.NewInstanceRegistry("list.json")
	sidGen := orchestrator.NewSIDGenerator("server_sids.json")
	
	reader := bufio.NewReader(os.Stdin)
	
	for {
		fmt.Println("\n" + strings.Repeat("-", 40))
		fmt.Println("Options:")
		fmt.Println("   1. ADD MORE servers to list")
		fmt.Println("   2. Show current servers")
		fmt.Println("   3. Clear ALL servers (start fresh)")
		fmt.Println("   4. --RUN all servers (start generating logs)")
		fmt.Println("   5. Exit")
		fmt.Println(strings.Repeat("-", 40))
		
		fmt.Print("Enter choice (1-5): ")
		choice, _ := reader.ReadString('\n')
		choice = strings.TrimSpace(choice)
		
		switch choice {
		case "1":
			addServers(registry, sidGen, reader)
		case "2":
			showServers(registry)
		case "3":
			registry.Clear()
			fmt.Println("\n🗑️ Cleared ALL server registrations!")
		case "4":
			runServers(registry)
		case "5":
			fmt.Println("\n👋 Goodbye!")
			return
		default:
			fmt.Println("\n❌ Invalid choice")
		}
	}
}

func addServers(registry *orchestrator.InstanceRegistry, sidGen *orchestrator.SIDGenerator, reader *bufio.Reader) {
	fmt.Println("\n📊 Enter number of servers for each type:")
	fmt.Println(strings.Repeat("-", 40))
	
	types := []string{"HEALTHCARE", "ZOOKEEPER", "WINDOWS", "LINUX"}
	icons := map[string]string{
		"HEALTHCARE": "🏥", "ZOOKEEPER": "🦓", "WINDOWS": "🪟", "LINUX": "🐧",
	}
	
	counts := make(map[string]int)
	for _, st := range types {
		fmt.Printf("%s %s servers (to ADD): ", icons[st], st)
		input, _ := reader.ReadString('\n')
		input = strings.TrimSpace(input)
		if input == "" { input = "0" }
		counts[st], _ = strconv.Atoi(input)
	}
	
	fmt.Println("\n🔧 Adding servers...")
	newInstances := []models.ServerInstance{}
	
	for _, st := range types {
		startNum := registry.GetHighestInstance(st) + 1
		for i := 0; i < counts[st]; i++ {
			sid := sidGen.GenerateWithInstance(st, startNum+i)
			newInstances = append(newInstances, models.ServerInstance{
				SID: sid, Type: st, Instance: startNum + i, Status: "registered",
			})
			fmt.Printf("   ➕ Added %s #%03d\n", st, startNum+i)
		}
	}
	registry.AddMultiple(newInstances)
	showServers(registry)
}

func showServers(registry *orchestrator.InstanceRegistry) {
	servers := registry.GetAll()
	if len(servers) == 0 {
		fmt.Println("\n📋 No servers registered yet.")
		return
	}
	
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("📋 REGISTERED SERVERS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("%-35s %-12s %-8s %-10s\n", "SID", "Type", "Instance", "Status")
	fmt.Println(strings.Repeat("-", 80))
	
	for _, s := range servers {
		shortSID := s.SID
		if len(shortSID) > 30 {
			shortSID = shortSID[:27] + "..."
		}
		fmt.Printf("%-35s %-12s #%03d      %-10s\n", shortSID, s.Type, s.Instance, s.Status)
	}
	
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("📊 Total: %d servers\n", len(servers))
}

func runServers(registry *orchestrator.InstanceRegistry) {
	servers := registry.GetAll()
	if len(servers) == 0 {
		fmt.Println("\n❌ No servers to run!")
		return
	}
	
	fmt.Printf("\n🚀 Launching %d servers...\n", len(servers))
	
	files, _ := filepath.Glob("logs/*.log")
	for _, f := range files {
		os.Remove(f)
	}
	os.MkdirAll("logs", 0755)
	os.MkdirAll("output", 0755)
	os.WriteFile("output/daemon.json", []byte("[]"), 0644)
	fmt.Println("   🗑️ Logs cleaned")
	
	fmt.Println("   🚀 Starting generators...")
	
	cwd, _ := os.Getwd()
	genPath := filepath.Join(cwd, "bin", "generator")
	
	for _, server := range servers {
		cmd := exec.Command(genPath, "--server="+strings.ToLower(server.Type))
		cmd.Env = append(os.Environ(),
			"SERVER_SID="+server.SID,
			"SERVER_INSTANCE="+strconv.Itoa(server.Instance),
		)
		cmd.Start()
		processes = append(processes, cmd)
		fmt.Printf("   ✅ Started %s #%03d\n", server.Type, server.Instance)
		time.Sleep(300 * time.Millisecond)
	}
	
	fmt.Printf("\n✅ All %d servers running!\n", len(servers))
	fmt.Println("📁 logs/ | 📄 output/daemon.json")
	fmt.Println("\n🛑 Press Ctrl+C to stop all servers")
}
