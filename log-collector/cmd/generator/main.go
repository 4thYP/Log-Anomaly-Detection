package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"migrate/internal/generator/servers"
)

func main() {
	serverType := flag.String("server", "healthcare", "Server type to generate logs for (healthcare, linux, windows, zookeeper)")
	flag.Parse()

	fmt.Println("============================================================")
	fmt.Printf("🚀 LOG GENERATOR - %s SERVER\n", *serverType)
	fmt.Println("============================================================")

	var server interface{ Run() }
	
	switch *serverType {
	case "healthcare":
		server = servers.NewHealthcareServer()
	case "linux":
		server = servers.NewLinuxServer()
	case "windows":
		server = servers.NewWindowsServer()
	case "zookeeper":
		server = servers.NewZookeeperServer()
	default:
		log.Fatalf("❌ Unknown server type: %s", *serverType)
	}

	// Run the server
	fmt.Println("\n📝 Generating logs...")
	server.Run()
	
	fmt.Println("\n✅ Generation complete!")
	fmt.Printf("📁 Logs written to: logs/%s_%s.log\n", *serverType, os.Getenv("SERVER_INSTANCE"))
}
