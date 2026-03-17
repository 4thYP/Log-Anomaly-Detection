#!/usr/bin/env python3
"""
Causal Chain Extractor
Discovers event sequences and cause-effect relationships
"""

from collections import defaultdict

class CausalChainExtractor:
    def __init__(self):
        self.chains = []
        self.sequence_probabilities = {}
        
    def extract(self, logs):
        """Extract causal chains from logs"""
        print("   - Building event sequences...")
        
        # Group by component and user to find chains
        chains = self._find_sequences_by_component(logs)
        
        # Calculate transition probabilities
        probabilities = self._calculate_transition_probabilities(chains)
        
        # Find common patterns
        common_patterns = self._find_common_patterns(chains)
        
        return {
            'chains': chains[:20],  # Top 20 chains
            'transition_probabilities': probabilities,
            'common_patterns': common_patterns,
            'total_chains': len(chains)
        }
    
    def _find_sequences_by_component(self, logs):
        """Group logs by component and find sequences"""
        component_logs = defaultdict(list)
        
        # Group by component
        for log in logs:
            if 'component' in log:
                component_logs[log['component']].append(log)
        
        # Find sequences within each component
        sequences = []
        for component, logs_list in component_logs.items():
            if len(logs_list) > 1:
                for i in range(len(logs_list) - 1):
                    current = logs_list[i]['message'][:50] if 'message' in logs_list[i] else ''
                    next_msg = logs_list[i+1]['message'][:50] if 'message' in logs_list[i+1] else ''
                    
                    sequences.append({
                        'component': component,
                        'from': current,
                        'to': next_msg,
                        'time_diff': self._get_time_diff(logs_list[i], logs_list[i+1])
                    })
        
        return sequences
    
    def _get_time_diff(self, log1, log2):
        """Calculate time difference between logs"""
        # Simplified - would need proper timestamp parsing
        return 1  # Placeholder
    
    def _calculate_transition_probabilities(self, sequences):
        """Calculate probability of event B following event A"""
        transitions = defaultdict(lambda: defaultdict(int))
        totals = defaultdict(int)
        
        for seq in sequences:
            from_event = seq['from']
            to_event = seq['to']
            
            transitions[from_event][to_event] += 1
            totals[from_event] += 1
        
        # Convert to probabilities
        probabilities = {}
        for from_event, to_events in transitions.items():
            probabilities[from_event] = {
                to_event: count / totals[from_event]
                for to_event, count in to_events.items()
            }
        
        return dict(sorted(probabilities.items(), 
                          key=lambda x: sum(x[1].values()), reverse=True)[:20])
    
    def _find_common_patterns(self, sequences):
        """Find common 3-event patterns"""
        patterns = defaultdict(int)
        
        for i in range(len(sequences) - 2):
            pattern = (
                sequences[i]['from'],
                sequences[i+1]['from'],
                sequences[i+2]['from']
            )
            patterns[pattern] += 1
        
        common = []
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            common.append({
                'pattern': list(pattern),
                'frequency': count
            })
        
        return common
