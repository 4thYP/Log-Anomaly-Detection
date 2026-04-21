.PHONY: build clean run

build:
	@echo "🔨 Building..."
	@mkdir -p bin
	go build -o bin/daemon cmd/daemon/main.go
	go build -o bin/learner cmd/learner/main.go
	go build -o bin/generator cmd/generator/main.go
	go build -o bin/run cmd/run/main.go
	@echo "✅ Build complete!"

clean:
	@./clean.sh

run:
	@./run.sh

help:
	@echo "make build  - Build binaries"
	@echo "make clean  - Clean all generated files"
	@echo "make run    - Run the system"
