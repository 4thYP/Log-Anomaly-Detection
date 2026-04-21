package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

func main() {
	file, _ := os.Open("datasets/healthcare/HealthApp_2k.log")
	defer file.Close()
	
	scanner := bufio.NewScanner(file)
	count := 0
	for scanner.Scan() && count < 20 {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if line == "" {
			fmt.Printf("Line %d: EMPTY\n", count+1)
		} else {
			fmt.Printf("Line %d: %s\n", count+1, line[:50])
		}
		count++
	}
}
