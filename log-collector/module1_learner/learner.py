#!/usr/bin/env python3
"""
Master Learner Script
Usage: python learner.py --server=healthcare
"""

import os
import json
import argparse
import sys

# Add the current directory to path so extractors can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.state_machine import StateMachineExtractor
from extractors.causal_chains import CausalChainExtractor
from extractors.value_relationships import ValueRelationshipExtractor
from extractors.temporal_patterns import TemporalPatternExtractor

class Learner:
    def __init__(self, server_name):
        self.server_name = server_name
        # FIXED: Correct paths - no extra '..'
        self.dataset_path = f"../datasets/{server_name}/"
        self.patterns_path = f"patterns/{server_name}_patterns.json"
        self.config_path = f"config/{server_name}_config.json"
        
        print(f"\n📁 Dataset path: {os.path.abspath(self.dataset_path)}")
        print(f"📁 Patterns will be saved to: {os.path.abspath(self.patterns_path)}")
        
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
        # Check if dataset directory exists
        if not os.path.exists(self.dataset_path):
            print(f"⚠️  Dataset directory does not exist: {self.dataset_path}")
            print(f"📁 Creating directory: {self.dataset_path}")
            os.makedirs(self.dataset_path, exist_ok=True)
            print(f"✅ Created dataset directory. Please place your {self.server_name} log file here.")
            return None
        
        # Look for .log files
        log_files = []
        for file in os.listdir(self.dataset_path):
            if file.endswith('.log'):
                log_files.append(file)
        
        if not log_files:
            print(f"❌ No .log files found in {self.dataset_path}")
            print(f"📁 Please place your {self.server_name} log file in this directory")
            return None
        
        # Use the first log file found
        log_file = os.path.join(self.dataset_path, log_files[0])
        print(f"✅ Found log file: {log_file}")
        
        if len(log_files) > 1:
            print(f"⚠️  Multiple log files found. Using: {log_files[0]}")
        
        return log_file
    
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
        try:
            with open(self.log_file, 'r') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    line = line.strip()
                    if line:
                        parsed = self._parse_log(line)
                        if parsed:
                            logs.append(parsed)
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            return []
        
        print(f"✅ Successfully read {len(logs)} log lines")
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
            else:
                # Handle lines that don't match expected format
                return {
                    'timestamp': '',
                    'component': 'unknown',
                    'user_id': '',
                    'message': line,
                    'raw': line
                }
        except Exception as e:
            print(f"⚠️  Error parsing line: {line[:50]}... - {e}")
            return None
    
    def learn(self):
        """Run all extractors to learn patterns"""
        print(f"\n{'='*60}")
        print(f"🎯 LEARNING PATTERNS FOR: {self.server_name.upper()}")
        print(f"{'='*60}")
        
        # Check if log file exists
        if not self.log_file:
            print(f"\n❌ Cannot proceed: No log file found for {self.server_name}")
            return False
        
        print(f"\n📖 Reading logs from: {self.log_file}")
        logs = self.read_logs()
        
        if not logs:
            print("❌ No logs to analyze")
            return False
        
        print(f"\n📊 Analyzed {len(logs)} log lines")
        
        # Step 1: Extract templates and components
        print("\n🔍 Step 1/6: Extracting templates and components...")
        self._extract_templates(logs)
        print(f"   ✅ Found {self.patterns['templates'].get('total_templates', 0)} unique templates")
        print(f"   ✅ Found {self.patterns['components'].get('total_components', 0)} unique components")
        
        # Step 2: Extract state machine
        print("\n🔍 Step 2/6: Extracting state machine...")
        self.patterns['state_machine'] = self.state_machine.extract(logs)
        counters = self.patterns['state_machine'].get('counters', {})
        print(f"   ✅ Found {len(counters)} state variables")
        
        # Step 3: Extract causal chains
        print("\n🔍 Step 3/6: Extracting causal chains...")
        self.patterns['causal_chains'] = self.causal_chains.extract(logs)
        chains = self.patterns['causal_chains'].get('chains', [])
        print(f"   ✅ Found {len(chains)} causal chains")
        
        # Step 4: Extract value relationships
        print("\n🔍 Step 4/6: Extracting value relationships...")
        self.patterns['value_relationships'] = self.value_relationships.extract(logs)
        correlations = self.patterns['value_relationships'].get('correlations', [])
        print(f"   ✅ Found {len(correlations)} value correlations")
        
        # Step 5: Extract temporal patterns
        print("\n🔍 Step 5/6: Extracting temporal patterns...")
        self.patterns['temporal_patterns'] = self.temporal_patterns.extract(logs)
        periodic = self.patterns['temporal_patterns'].get('periodic_events', {})
        print(f"   ✅ Found {len(periodic)} periodic events")
        
        # Step 6: Calculate statistics
        print("\n🔍 Step 6/6: Calculating statistics...")
        self._calculate_statistics(logs)
        
        # Save patterns
        self._save_patterns()
        
        print(f"\n{'='*60}")
        print(f"✅ LEARNING COMPLETE!")
        print(f"{'='*60}")
        print(f"📁 Patterns saved to: {self.patterns_path}")
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
        
        # Sort templates by frequency
        sorted_templates = dict(sorted(templates.items(), key=lambda x: x[1], reverse=True)[:50])
        
        self.patterns['templates'] = {
            'by_frequency': sorted_templates,
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
            if 'timestamp' in log and log['timestamp']:
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
        # Create patterns directory if it doesn't exist
        os.makedirs('patterns', exist_ok=True)
        
        try:
            with open(self.patterns_path, 'w') as f:
                json.dump(self.patterns, f, indent=2)
            print(f"\n💾 Successfully saved patterns to: {self.patterns_path}")
        except Exception as e:
            print(f"❌ Error saving patterns: {e}")

def main():
    parser = argparse.ArgumentParser(description='Learn patterns from server logs')
    parser.add_argument('--server', required=True, 
                       choices=['healthcare', 'db', 'api', 'auth', 'infra', 'hpc', 'linux', 'spark', 'windows', 'zookeeper'],
                       help='Server type to learn patterns for')
    
    args = parser.parse_args()
    
    print(f"\n🚀 Starting Learner for {args.server} server...")
    learner = Learner(args.server)
    success = learner.learn()
    
    if success:
        print(f"\n🎉 Successfully learned patterns for {args.server} server!")
        print("\n📋 Next steps:")
        print("   1. Review the patterns in: patterns/{}_patterns.json".format(args.server))
        print("   2. Run Module 2 generator to create realistic logs")
        print("   3. Repeat for other servers: db, api, auth, infra")
    else:
        print(f"\n❌ Failed to learn patterns for {args.server} server")
        print("\n💡 Troubleshooting:")
        print("   1. Check if your log file exists in: datasets/{}/".format(args.server))
        print("   2. Make sure the log file has a .log extension")
        print("   3. Check file permissions")

if __name__ == "__main__":
    main()
