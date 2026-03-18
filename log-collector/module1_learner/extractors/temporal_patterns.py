#!/usr/bin/env python3
"""
Temporal Pattern Extractor
Finds time-based patterns in logs
"""

import re
from collections import defaultdict
from datetime import datetime

class TemporalPatternExtractor:
    def __init__(self):
        self.patterns = {}
        
    def extract(self, logs):
        """Extract temporal patterns from logs"""
        print("   - Analyzing temporal patterns...")
        
        # Parse timestamps
        timed_logs = self._parse_timestamps(logs)
        
        # Find periodic events
        periodic = self._find_periodic_events(timed_logs)
        
        # Find event clusters
        clusters = self._find_event_clusters(timed_logs)
        
        # Find time-of-day patterns
        time_patterns = self._find_time_of_day_patterns(timed_logs)
        
        # Find gaps and bursts
        gaps = self._find_gaps_and_bursts(timed_logs)
        
        return {
            'periodic_events': periodic,
            'event_clusters': clusters,
            'time_of_day': time_patterns,
            'gaps_and_bursts': gaps
        }
    
    def _parse_timestamps(self, logs):
        """Parse timestamps into datetime objects"""
        timed_logs = []
        
        for log in logs:
            if 'timestamp' not in log:
                continue
                
            ts_str = log['timestamp']
            try:
                # Handle format: 20171223-22:15:29:606
                if len(ts_str) >= 19:
                    date_part = ts_str[:8]
                    time_part = ts_str[9:19]
                    dt = datetime.strptime(f"{date_part} {time_part}", "%Y%m%d %H:%M:%S")
                    timed_logs.append({
                        'datetime': dt,
                        'component': log.get('component', 'unknown'),
                        'message': log.get('message', ''),
                        'raw': log
                    })
            except:
                pass
        
        return timed_logs
    
    def _find_periodic_events(self, timed_logs):
        """Find events that occur at regular intervals"""
        event_times = defaultdict(list)
        
        for log in timed_logs:
            msg = log['message']
            # Look for TIME_TICK events
            if 'TIME_TICK' in msg:
                event_times['TIME_TICK'].append(log['datetime'])
            
            # Look for REPORT events
            if 'REPORT' in msg:
                event_times['REPORT'].append(log['datetime'])
        
        periodic = {}
        for event, times in event_times.items():
            if len(times) > 5:
                intervals = []
                for i in range(len(times)-1):
                    interval = (times[i+1] - times[i]).total_seconds()
                    intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    periodic[event] = {
                        'frequency': f"every {avg_interval:.1f} seconds",
                        'samples': len(times),
                        'interval_consistency': 'high' if max(intervals) - min(intervals) < 5 else 'medium'
                    }
        
        return periodic
    
    def _find_event_clusters(self, timed_logs):
        """Find events that often happen together in time"""
        clusters = []
        
        # Simple clustering: events within 2 seconds of each other
        for i in range(len(timed_logs)-1):
            cluster = [timed_logs[i]]
            j = i + 1
            
            while j < len(timed_logs):
                time_diff = (timed_logs[j]['datetime'] - timed_logs[i]['datetime']).total_seconds()
                if time_diff < 2:  # Within 2 seconds
                    cluster.append(timed_logs[j])
                    j += 1
                else:
                    break
            
            if len(cluster) > 3:  # Meaningful cluster
                messages = [c['message'][:30] for c in cluster[:5]]
                clusters.append({
                    'time': str(cluster[0]['datetime']),
                    'size': len(cluster),
                    'sample_messages': messages
                })
            
            i = j
        
        return clusters[:10]  # Top 10 clusters
    
    def _find_time_of_day_patterns(self, timed_logs):
        """Find patterns based on time of day"""
        hourly_counts = defaultdict(int)
        
        for log in timed_logs:
            hour = log['datetime'].hour
            hourly_counts[hour] += 1
        
        # Normalize
        total = len(timed_logs)
        hourly_pattern = {
            hour: count / total
            for hour, count in hourly_counts.items()
        }
        
        # Find peak hours
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'hourly_distribution': dict(sorted(hourly_pattern.items())),
            'peak_hours': [{'hour': h, 'count': c} for h, c in peak_hours]
        }
    
    def _find_gaps_and_bursts(self, timed_logs):
        """Find long gaps and high-activity bursts"""
        if len(timed_logs) < 2:
            return {}
        
        intervals = []
        for i in range(len(timed_logs)-1):
            interval = (timed_logs[i+1]['datetime'] - timed_logs[i]['datetime']).total_seconds()
            intervals.append(interval)
        
        # Find gaps (intervals > 60 seconds)
        gaps = [i for i in intervals if i > 60]
        
        # Find bursts (many logs in short time)
        bursts = []
        i = 0
        while i < len(timed_logs):
            burst_start = i
            burst_end = i
            while burst_end < len(timed_logs)-1:
                next_interval = (timed_logs[burst_end+1]['datetime'] - timed_logs[burst_end]['datetime']).total_seconds()
                if next_interval < 1:  # Very short intervals indicate burst
                    burst_end += 1
                else:
                    break
            
            if burst_end - burst_start > 5:  # Burst of 5+ logs
                bursts.append({
                    'start': str(timed_logs[burst_start]['datetime']),
                    'duration_sec': (timed_logs[burst_end]['datetime'] - timed_logs[burst_start]['datetime']).total_seconds(),
                    'log_count': burst_end - burst_start + 1
                })
            
            i = burst_end + 1
        
        return {
            'avg_interval_sec': sum(intervals) / len(intervals),
            'max_gap_sec': max(intervals),
            'min_interval_sec': min(intervals),
            'gaps_over_60s': len(gaps),
            'bursts': bursts[:5]
        }
