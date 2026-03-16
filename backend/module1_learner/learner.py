#!/usr/bin/env python3
"""
Master Learner Script
Usage: python learner.py --server=healthcare
"""

import os
import json
import argparse
from extractors.state_machine import StateMachineExtractor
from extractors.causal_chains import CausalChainExtractor
from extractors.value_relationships import ValueRelationshipExtractor
from extractors.temporal_patterns import TemporalPatternExtractor

class Learner:
    def __init__(self, server_name):
        self.server_name = server_name
        self.dataset_path = f"../datasets/{server_name}/"
        self.patterns_path = f"patterns/{server_name}_patterns.json"
        self.config_path = f"config/{server_name}_config.json"
        
        # Find the log file
        self.log_file = self._find_log_file()
        
        # Initialize extractors
        self.state_machine = StateMachineExtractor()
        self.causal_chains = CausalChainExtractor()
        self.value_relationships = ValueRelationshipExtractor()
        self.temporal_patterns = TemporalPatternExtractor()
        
        # Collected patterns
        self.patterns = {
            "server": server_name,
            "templates": {},
            "components": {},
            "state_machine": {},
            "causal_chains": [],
            "value_relationships": {},
            "temporal_patterns": {},
            "statistics": {}
        }
    
    def _find_log_file(self):
        """Find the first .log file in the dataset directory"""
        if not os.path.exists(self.dataset_path):
            os.makedirs(self.dataset_path, exist_ok=True)
            print(f"Created dataset directory: {self.dataset_path}")
            print(f"Please place your {self.server_name} log file in this directory")
            return None
            
        for file in os.listdir(self.dataset_path):
            if file.endswith('.log'):
                return os.path.join(self.dataset_path, file)
        
        print(f"No .log file found in {self.dataset_path}")
        return None
    
    def load_config(self):
        """Load server-specific configuration if exists"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def read_logs(self, max_lines=10000):
        """Read and parse log lines"""
        if not self.log_file:
            return []
        
        logs = []
        with open(self.log_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if line:
                    logs.append(self._parse_log(line))
        return logs
    
    def _parse_log(self, line):
        """Parse a log line into components"""
        try:
            parts = line.split('|')
            if len(parts) >= 4:
                return {
                    'timestamp': parts[0].strip(),
                    'component': parts[1].strip(),
                    'user_id': parts[2].strip(),
                    'message': '|'.join(parts[3:]).strip(),
                    'raw': line
                }
        except:
            pass
        return {'raw': line}
    
    def learn(self):
        """Run all extractors to learn patterns"""
        print(f"\n{'='*60}")
        print(f"LEARNING PATTERNS FOR: {self.server_name.upper()}")
        print(f"{'='*60}")
        
        # Check if log file exists
        if not self.log_file:
            print(f"\n❌ No log file found for {self.server_name}")
            print(f"Please place your {self.server_name} log file in: {self.dataset_path}")
            return False
        
        print(f"\n📁 Reading logs from: {self.log_file}")
        logs = self.read_logs()
        print(f"📊 Read {len(logs)} log lines")
        
        if not logs:
            print("❌ No logs to analyze")
            return False
        
        # Step 1: Extract templates and components
        print("\n🔍 Step 1: Extracting templates and components...")
        self._extract_templates(logs)
        
        # Step 2: Extract state machine
        print("\n🔍 Step 2: Extracting state machine...")
        self.patterns['state_machine'] = self.state_machine.extract(logs)
        
        # Step 3: Extract causal chains
        print("\n🔍 Step 3: Extracting causal chains...")
        self.patterns['causal_chains'] = self.causal_chains.extract(logs)
        
        # Step 4: Extract value relationships
        print("\n🔍 Step 4: Extracting value relationships...")
        self.patterns['value_relationships'] = self.value_relationships.extract(logs)
        
        # Step 5: Extract temporal patterns
        print("\n🔍 Step 5: Extracting temporal patterns...")
        self.patterns['temporal_patterns'] = self.temporal_patterns.extract(logs)
        
        # Step 6: Calculate statistics
        print("\n🔍 Step 6: Calculating statistics...")
        self._calculate_statistics(logs)
        
        # Save patterns
        self._save_patterns()
        
        print(f"\n✅ Learning complete! Patterns saved to: {self.patterns_path}")
        return True
    
    def _extract_templates(self, logs):
        """Extract message templates and component frequencies"""
        templates = {}
        components = {}
        
        for log in logs:
            if 'message' in log:
                # Extract template by replacing numbers with <*>
                message = log['message']
                template = self._create_template(message)
                
                if template not in templates:
                    templates[template] = 0
                templates[template] += 1
                
                # Count components
                component = log.get('component', 'unknown')
                if component not in components:
                    components[component] = 0
                components[component] += 1
        
        self.patterns['templates'] = {
            'by_frequency': dict(sorted(templates.items(), key=lambda x: x[1], reverse=True)[:50]),
            'total_templates': len(templates)
        }
        
        self.patterns['components'] = {
            'by_frequency': dict(sorted(components.items(), key=lambda x: x[1], reverse=True)),
            'total_components': len(components)
        }
    
    def _create_template(self, message):
        """Replace numbers and common variables with <*>"""
        import re
        # Replace numbers
        template = re.sub(r'\b\d+\b', '<*>', message)
        # Replace hex values
        template = re.sub(r'0x[0-9a-f]+', '<*>', template)
        # Replace UUIDs (simplified)
        template = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<*>', template)
        return template
    
    def _calculate_statistics(self, logs):
        """Calculate overall statistics"""
        self.patterns['statistics'] = {
            'total_logs': len(logs),
            'unique_components': len(self.patterns['components'].get('by_frequency', {})),
            'unique_templates': self.patterns['templates'].get('total_templates', 0),
            'time_span': self._get_time_span(logs),
            'avg_logs_per_minute': self._calculate_log_frequency(logs)
        }
    
    def _get_time_span(self, logs):
        """Get first and last timestamp"""
        timestamps = []
        for log in logs:
            if 'timestamp' in log:
                timestamps.append(log['timestamp'])
        
        if len(timestamps) >= 2:
            return {
                'first': timestamps[0],
                'last': timestamps[-1]
            }
        return {}
    
    def _calculate_log_frequency(self, logs):
        """Calculate average logs per minute"""
        # Simplified - would need proper timestamp parsing
        return "N/A"
    
    def _save_patterns(self):
        """Save learned patterns to JSON file"""
        os.makedirs('patterns', exist_ok=True)
        
        with open(self.patterns_path, 'w') as f:
            json.dump(self.patterns, f, indent=2)
        
        print(f"\n📝 Pattern Summary:")
        print(f"   - Templates found: {self.patterns['templates'].get('total_templates', 0)}")
        print(f"   - Components found: {self.patterns['components'].get('total_components', 0)}")
        print(f"   - Causal chains: {len(self.patterns['causal_chains'])}")

def main():
    parser = argparse.ArgumentParser(description='Learn patterns from server logs')
    parser.add_argument('--server', required=True, 
                       choices=['healthcare', 'db', 'api', 'auth', 'infra'],
                       help='Server type to learn patterns for')
    
    args = parser.parse_args()
    
    learner = Learner(args.server)
    success = learner.learn()
    
    if success:
        print(f"\n🎉 Successfully learned patterns for {args.server} server!")
    else:
        print(f"\n❌ Failed to learn patterns for {args.server} server")

if __name__ == "__main__":
    main()
