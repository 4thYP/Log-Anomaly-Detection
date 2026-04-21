package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	fmt.Println("🧹 Cleaning up ALL generated files...")
	
	// 1. Delete all .log files
	logFiles, _ := filepath.Glob("logs/*.log")
	for _, file := range logFiles {
		if err := os.Remove(file); err == nil {
			fmt.Printf("   ✅ Deleted: %s\n", file)
		}
	}
	
	// 2. Reset daemon.json
	os.MkdirAll("output", 0755)
	if err := os.WriteFile("output/daemon.json", []byte("[]"), 0644); err == nil {
		fmt.Println("   ✅ Reset output/daemon.json to []")
	}
	
	// 3. Delete SID registry
	if err := os.Remove("server_sids.json"); err == nil {
		fmt.Println("   ✅ Deleted: server_sids.json")
	}
	
	// 4. Delete list.json
	if err := os.Remove("list.json"); err == nil {
		fmt.Println("   ✅ Deleted: list.json")
	}
	
	fmt.Println("\n✨ Clean up complete!")
}
