#!/usr/bin/env python3
"""
State Machine Extractor
Identifies state variables and their transitions from logs
"""

import re

class StateMachineExtractor:
    def __init__(self):
        self.state_variables = {}
        self.transitions = []
        
    def extract(self, logs):
        """Extract state machines from logs"""
        print("   - Analyzing state changes...")
        
        # Look for common state patterns
        state_patterns = {
            'counters': self._find_counters(logs),
            'flags': self._find_flags(logs),
            'sequences': self._find_sequences(logs),
            'values': self._find_tracking_values(logs)
        }
        
        return state_patterns
    
    def _find_counters(self, logs):
        """Find variables that increment (like step counts)"""
        counters = {}
        last_values = {}
        
        for log in logs:
            if 'message' not in log:
                continue
                
            msg = log['message']
            
            # Look for patterns like "onStandStepChanged 3579"
            counter_matches = re.findall(r'(\w+)\s+(\d+)', msg)
            
            for name, value in counter_matches:
                value = int(value)
                if name not in last_values:
                    last_values[name] = value
                    counters[name] = {'type': 'counter', 'samples': [value]}
                else:
                    if value > last_values[name]:
                        counters[name]['type'] = 'incrementing_counter'
                    counters[name]['samples'].append(value)
                    last_values[name] = value
        
        return counters
    
    def _find_flags(self, logs):
        """Find boolean state variables"""
        flags = {}
        flag_patterns = ['SCREEN_ON', 'SCREEN_OFF', 'true', 'false']
        
        for log in logs:
            if 'message' not in log:
                continue
                
            msg = log['message']
            for pattern in flag_patterns:
                if pattern in msg:
                    flags[pattern] = flags.get(pattern, 0) + 1
        
        return flags
    
    def _find_sequences(self, logs):
        """Find sequential state changes"""
        sequences = []
        last_state = None
        
        for log in logs:
            if 'message' not in log:
                continue
                
            current = log['message'][:30]  # First 30 chars as rough state
            
            if last_state and last_state != current:
                sequences.append({
                    'from': last_state,
                    'to': current,
                    'component': log.get('component', 'unknown')
                })
            
            last_state = current
        
        # Find common transitions
        transition_counts = {}
        for seq in sequences:
            key = f"{seq['from']} → {seq['to']}"
            transition_counts[key] = transition_counts.get(key, 0) + 1
        
        return {
            'common_transitions': dict(sorted(transition_counts.items(), 
                                             key=lambda x: x[1], reverse=True)[:20]),
            'total_sequences': len(sequences)
        }
    
    def _find_tracking_values(self, logs):
        """Find values that are tracked over time"""
        tracked = {}
        
        value_patterns = [
            (r'totalSteps=(\d+)', 'totalSteps'),
            (r'totalCalories=(\d+)', 'totalCalories'),
            (r'totalAltitude=(\d+)', 'totalAltitude'),
            (r'patient_id=(\d+)', 'patient_id')
        ]
        
        for log in logs:
            if 'message' not in log:
                continue
                
            msg = log['message']
            for pattern, name in value_patterns:
                match = re.search(pattern, msg)
                if match:
                    if name not in tracked:
                        tracked[name] = []
                    tracked[name].append(int(match.group(1)))
        
        # Calculate ranges
        for name, values in tracked.items():
            if values:
                tracked[name] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'samples': len(values)
                }
        
        return tracked
