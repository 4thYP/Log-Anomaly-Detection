#!/usr/bin/env python3
"""
Value Relationship Extractor
Discovers how different values relate to each other
"""

import re
from collections import defaultdict

class ValueRelationshipExtractor:
    def __init__(self):
        self.relationships = {}
        
    def extract(self, logs):
        """Extract value relationships from logs"""
        print("   - Analyzing value relationships...")
        
        # Extract all numeric values with context
        values = self._extract_values(logs)
        
        # Find correlations
        correlations = self._find_correlations(values)
        
        # Find formulas
        formulas = self._find_formulas(values)
        
        # Find ranges and distributions
        distributions = self._find_distributions(values)
        
        return {
            'correlations': correlations,
            'formulas': formulas,
            'distributions': distributions
        }
    
    def _extract_values(self, logs):
        """Extract all numeric values with their context"""
        values = defaultdict(list)
        
        value_patterns = [
            (r'(\w+)=(\d+)', 'field'),           # field=value
            (r'(\w+):\s*(\d+)', 'field'),        # field: value
            (r'(\w+)\s+(\d+)', 'word_value'),     # word value
            (r'##(\d+)', 'separated')             # ##value
        ]
        
        for log in logs:
            if 'message' not in log:
                continue
                
            msg = log['message']
            component = log.get('component', 'unknown')
            
            for pattern, ptype in value_patterns:
                matches = re.findall(pattern, msg)
                for match in matches:
                    if ptype == 'field':
                        name, val = match
                        values[f"{component}.{name}"].append(int(val))
                    elif ptype == 'word_value':
                        name, val = match
                        if name.isalpha():  # Avoid capturing random numbers
                            values[f"{component}.{name}"].append(int(val))
                    elif ptype == 'separated':
                        values['separated_value'].append(int(match))
        
        return values
    
    def _find_correlations(self, values):
        """Find relationships between value pairs"""
        correlations = []
        
        # Look for values that appear together
        value_pairs = list(values.items())
        
        for i in range(len(value_pairs)):
            for j in range(i+1, len(value_pairs)):
                name1, vals1 = value_pairs[i]
                name2, vals2 = value_pairs[j]
                
                # Check if they have similar patterns
                if len(vals1) > 5 and len(vals2) > 5:
                    ratio = self._check_ratio(vals1, vals2)
                    if ratio:
                        correlations.append({
                            'value1': name1,
                            'value2': name2,
                            'relationship': f"{name1} ≈ {ratio:.2f} × {name2}",
                            'confidence': 'high' if abs(ratio - round(ratio)) < 0.1 else 'medium'
                        })
        
        return correlations[:20]  # Top 20 correlations
    
    def _check_ratio(self, vals1, vals2):
        """Check if values maintain a constant ratio"""
        if len(vals1) != len(vals2):
            return None
            
        ratios = []
        for v1, v2 in zip(vals1[:10], vals2[:10]):  # Check first 10
            if v2 != 0:
                ratios.append(v1 / v2)
        
        if ratios and len(set(ratios)) == 1:  # All ratios same
            return ratios[0]
        return None
    
    def _find_formulas(self, values):
        """Find formulaic relationships"""
        formulas = []
        
        # Look for incremental relationships
        for name, vals in values.items():
            if len(vals) > 10:
                diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
                if len(set(diffs)) == 1 and diffs[0] > 0:
                    formulas.append({
                        'variable': name,
                        'pattern': 'increments_by',
                        'value': diffs[0],
                        'description': f"{name} increases by {diffs[0]} each time"
                    })
        
        return formulas
    
    def _find_distributions(self, values):
        """Find value ranges and distributions"""
        distributions = {}
        
        for name, vals in values.items():
            if vals:
                distributions[name] = {
                    'min': min(vals),
                    'max': max(vals),
                    'avg': sum(vals) / len(vals),
                    'median': sorted(vals)[len(vals)//2],
                    'samples': len(vals),
                    'unique_values': len(set(vals))
                }
        
        return dict(sorted(distributions.items(), key=lambda x: len(x[1].get('samples', 0)), reverse=True)[:30])
