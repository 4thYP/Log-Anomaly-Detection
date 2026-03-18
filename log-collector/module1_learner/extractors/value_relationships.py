#!/usr/bin/env python3
"""
Value Relationship Extractor
Discovers how different values relate to each other
"""

import re
from collections import defaultdict
import statistics

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
            (r'##(\d+)', 'separated'),             # ##value
            (r'(\d+)', 'bare_number')               # Just a number
        ]
        
        for log in logs:
            if 'message' not in log:
                continue
                
            msg = log['message']
            component = log.get('component', 'unknown')
            
            for pattern, ptype in value_patterns:
                matches = re.findall(pattern, msg)
                for match in matches:
                    try:
                        if ptype == 'field':
                            if isinstance(match, tuple):
                                name, val = match
                                values[f"{component}.{name}"].append(int(val))
                            else:
                                # Handle non-tuple matches
                                values[f"{component}.value"].append(int(match))
                        elif ptype == 'word_value':
                            if isinstance(match, tuple):
                                name, val = match
                                if name.isalpha():
                                    values[f"{component}.{name}"].append(int(val))
                            else:
                                if str(match).isalpha():
                                    values[f"{component}.value"].append(int(match))
                        elif ptype == 'separated':
                            values['separated_value'].append(int(match))
                        elif ptype == 'bare_number':
                            # Only capture significant numbers (not small ones that might be counters)
                            if int(match) > 100:  # Filter out small numbers
                                values[f"{component}.number"].append(int(match))
                    except (ValueError, TypeError):
                        continue
        
        return values
    
    def _find_correlations(self, values):
        """Find relationships between value pairs"""
        correlations = []
        
        # Get value names that have enough samples
        valid_names = [name for name, vals in values.items() if len(vals) > 5]
        
        for i in range(len(valid_names)):
            for j in range(i+1, len(valid_names)):
                name1 = valid_names[i]
                name2 = valid_names[j]
                vals1 = values[name1][:20]  # Take first 20 samples
                vals2 = values[name2][:20]
                
                # Check if they have the same length for comparison
                min_len = min(len(vals1), len(vals2))
                if min_len < 5:
                    continue
                
                # Check for constant ratio
                ratio = self._check_ratio(vals1[:min_len], vals2[:min_len])
                if ratio:
                    correlations.append({
                        'value1': name1,
                        'value2': name2,
                        'relationship': f"{name1} ≈ {ratio:.2f} × {name2}",
                        'confidence': 'high' if abs(ratio - round(ratio)) < 0.1 else 'medium'
                    })
                
                # Check for constant difference
                diff = self._check_difference(vals1[:min_len], vals2[:min_len])
                if diff is not None:
                    correlations.append({
                        'value1': name1,
                        'value2': name2,
                        'relationship': f"{name1} = {name2} + {diff:.0f}",
                        'confidence': 'high'
                    })
        
        return correlations[:20]  # Top 20 correlations
    
    def _check_ratio(self, vals1, vals2):
        """Check if values maintain a constant ratio"""
        ratios = []
        for v1, v2 in zip(vals1, vals2):
            if v2 != 0:
                ratios.append(v1 / v2)
        
        if ratios and len(ratios) > 3:
            avg_ratio = sum(ratios) / len(ratios)
            # Check if ratios are consistent (low variance)
            variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
            if variance < 0.1:  # Very consistent
                return avg_ratio
        return None
    
    def _check_difference(self, vals1, vals2):
        """Check if values maintain a constant difference"""
        diffs = [v1 - v2 for v1, v2 in zip(vals1, vals2)]
        
        if diffs and len(diffs) > 3:
            if len(set(diffs)) == 1:  # All differences same
                return diffs[0]
        return None
    
    def _find_formulas(self, values):
        """Find formulaic relationships"""
        formulas = []
        
        for name, vals in values.items():
            if len(vals) > 10:
                # Check for increments
                diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
                if diffs and len(set(diffs)) == 1 and diffs[0] > 0:
                    formulas.append({
                        'variable': name,
                        'pattern': 'increments_by',
                        'value': diffs[0],
                        'description': f"{name} increases by {diffs[0]} each time"
                    })
                
                # Check for patterns in the sequence
                if self._is_arithmetic_progression(vals[:10]):
                    formulas.append({
                        'variable': name,
                        'pattern': 'arithmetic_progression',
                        'description': f"{name} follows an arithmetic progression"
                    })
        
        return formulas
    
    def _is_arithmetic_progression(self, vals):
        """Check if values form an arithmetic progression"""
        if len(vals) < 3:
            return False
        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
        return len(set(diffs)) == 1
    
    def _find_distributions(self, values):
        """Find value ranges and distributions"""
        distributions = {}
        
        for name, vals in values.items():
            if vals and len(vals) > 3:
                try:
                    distributions[name] = {
                        'min': min(vals),
                        'max': max(vals),
                        'avg': sum(vals) / len(vals),
                        'median': sorted(vals)[len(vals)//2],
                        'count': len(vals),
                        'unique_values': len(set(vals))
                    }
                    
                    # Add standard deviation if possible
                    if len(vals) > 1:
                        distributions[name]['std_dev'] = statistics.stdev(vals)
                    
                except Exception as e:
                    # Skip if any calculation fails
                    continue
        
        # FIXED: Sort by count (which is an integer, not a dictionary with 'samples')
        sorted_distributions = dict(sorted(
            distributions.items(), 
            key=lambda x: x[1].get('count', 0), 
            reverse=True
        )[:30])
        
        return sorted_distributions
