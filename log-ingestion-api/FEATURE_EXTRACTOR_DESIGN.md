# STEP 4: Feature Extractor Redesign

## Overview

Redesign all 3 feature extractors to:
1. **Per-server state tracking**: Replace global state with per-sid (server_id) state isolation
2. **Timestamp from logs**: Use `log_internal.timestamp` instead of `datetime.now()`
3. **Fixed feature vectors**: Reduce from 50+ features (Dict) to 10-14 features (List)
4. **Consistent interface**: All extractors return `List[float]` in fixed order

---

## Architecture: Per-Server State Isolation

### Current Problem (❌ BROKEN)
```python
class LinuxFeatureExtractor:
    def __init__(self):
        self.event_counts = defaultdict(int)      # Global across ALL servers
        self.ip_auth_failures = defaultdict(int)  # Global across ALL servers
```

When processing logs from multiple servers simultaneously:
- Server A's state pollutes Server B's calculations
- No isolation between independent anomaly detection tasks

### New Design (✅ FIXED)

**Per-Server State Storage:**
```python
class LinuxFeatureExtractor:
    def __init__(self):
        self.server_states: Dict[str, ServerState] = {}  # sid -> state
    
    def _get_or_create_server_state(self, sid: str) -> ServerState:
        if sid not in self.server_states:
            self.server_states[sid] = ServerState()
        return self.server_states[sid]
    
    def extract(self, log_internal: LogInternal) -> List[float]:
        state = self._get_or_create_server_state(log_internal.sid)
        # All subsequent operations use state for this specific server
```

**Benefits:**
- ✅ Proper isolation between servers
- ✅ Supports multiple parallel streams
- ✅ State persists for temporal features
- ✅ No global state pollution

---

## Fixed Feature Vectors (10-14 Features per Type)

### Linux Feature Vector (14 features)

```python
LINUX_FEATURES = [
    "event_type_code",              # 0: 1-19 (see EventTypeCode enum)
    "template_id_normalized",       # 1: 0-50 (normalized to 0-1 range)
    "auth_failure_rate_5m",         # 2: 0-1 (auth failures / total events in 5m)
    "unique_ips_5m",                # 3: 0-1 (normalized count)
    "ip_failure_streak",             # 4: 0-1 (consecutive failures from same IP)
    "ftp_connection_burst",          # 5: 0-1 (rapid FTP connections)
    "session_anomaly_score",         # 6: 0-1 (unusual session patterns)
    "error_event_density",           # 7: 0-1 (error events / total in 5m window)
    "is_auth_failure_flag",          # 8: 0 or 1 (binary: is current event auth failure)
    "is_new_ip_flag",                # 9: 0 or 1 (binary: first time seeing this IP)
    "auth_burst_detected",           # 10: 0-1 (multiple auth failures in short window)
    "component_anomaly",             # 11: 0-1 (unusual component activity)
    "temporal_entropy",              # 12: 0-1 (how random/chaotic is timing)
    "overall_anomaly_score",         # 13: 0-1 (final ML input)
]
```

**Constraints:**
- ✅ Fixed length (14 elements, always)
- ✅ All values normalized to 0-1 range
- ✅ Ordered consistently (used as LSTM input sequence)
- ✅ Meaningful feature names
- ✅ Includes temporal AND current-event information

### Windows Feature Vector (12 features)

```python
WINDOWS_FEATURES = [
    "event_type_code",              # 0: 1-16 (WindowsEventType)
    "template_id_normalized",       # 1: 0-1
    "error_rate_5m",                # 2: 0-1 (errors / total events)
    "transaction_failure_rate",     # 3: 0-1 (failed / total transactions)
    "error_cascade_indicator",      # 4: 0-1 (similar errors in sequence)
    "hresult_code_bucket",          # 5: 0-1 (normalized error code clustering)
    "service_health_transition",    # 6: 0-1 (start after stop rapidly = bad)
    "package_install_failure_rate", # 7: 0-1
    "is_error_flag",                # 8: 0 or 1 (current event is error)
    "consecutive_errors_normalized",# 9: 0-1 (normalized max streak)
    "temporal_irregularity",        # 10: 0-1 (event timing patterns)
    "overall_anomaly_score",        # 11: 0-1
]
```

### Zookeeper Feature Vector (10 features)

```python
ZOOKEEPER_FEATURES = [
    "event_type_code",              # 0: 1-16 (ZookeeperEventType)
    "connection_churn_rate",        # 1: 0-1 (connections broken / received)
    "worker_instability",           # 2: 0-1 (worker interruptions / total)
    "election_frequency",           # 3: 0-1 (elections per 5m window)
    "session_timeout_rate",         # 4: 0-1 (expirations / established)
    "quorum_health",                # 5: 0-1 (inverse of failures)
    "error_event_rate",             # 6: 0-1 (error events / total)
    "is_error_flag",                # 7: 0 or 1 (current event type)
    "consensus_lag_indicator",      # 8: 0-1 (anomaly in consensus)
    "overall_anomaly_score",        # 9: 0-1
]
```

---

## Timestamp Handling

### Current Problem (❌ BROKEN)
```python
def extract(self, log_internal: LogInternal) -> Dict[str, float]:
    current_time = datetime.now()  # ❌ Wrong! Uses wall clock, not log time
    # Features are based on "now", not log timestamp
```

Issues:
- Features computed with `datetime.now()` don't match log's actual timestamp
- Temporal windows (5m, 10m) are based on current wall clock, not log sequence
- Replaying historical logs gives wrong results

### New Design (✅ FIXED)
```python
def extract(self, log_internal: LogInternal) -> List[float]:
    # Use log's actual timestamp, not wall clock
    log_time = log_internal.timestamp  # datetime object from log header
    state = self._get_or_create_server_state(log_internal.sid)
    
    # All sliding windows and temporal calculations use log_time
    # not datetime.now()
    
    return self._compute_features(parsed_log, state, log_time)
```

**Parsing Timestamp:**
```python
# LogInternal comes from models/log_models.py
class LogInternal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sid: str                    # ✅ Server ID for state isolation
    timestamp: datetime         # ✅ Use for all temporal calculations
    server_type: ServerType
    log_file: str
    message: str
    metadata: Optional[Dict] = None
    ingested_at: datetime = Field(default_factory=datetime.now)
```

---

## ServerState Class (Per-Server Storage)

Each log type defines its own ServerState, common pattern:

```python
# Example: LinuxServerState
class LinuxServerState:
    """Per-server state for Linux feature extraction"""
    
    def __init__(self):
        # Event frequency tracking
        self.event_timestamp_queue: deque = deque(maxlen=1000)  # For 5m window
        self.event_type_counts: Dict[str, int] = defaultdict(int)
        
        # IP tracking
        self.ip_last_seen: Dict[str, datetime] = {}
        self.ip_failure_counts: Dict[str, int] = defaultdict(int)
        self.ip_failure_streaks: Dict[str, int] = defaultdict(int)
        self.ip_first_seen: Dict[str, datetime] = {}
        
        # User tracking
        self.user_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.user_success_count: Dict[str, int] = defaultdict(int)
        self.user_failure_count: Dict[str, int] = defaultdict(int)
        
        # Session tracking
        self.active_sessions: Dict[str, datetime] = {}
        
        # Temporal state
        self.last_event_time: datetime = None
        self.event_intervals: deque = deque(maxlen=100)
```

---

## Feature Computation Pattern

### Sliding Window Pattern (5-minute windows)

```python
def _get_5m_events(self, state: ServerState, current_time: datetime) -> List[Dict]:
    """Get all events from last 5 minutes"""
    cutoff = current_time - timedelta(minutes=5)
    return [
        event for event in state.event_timestamp_queue
        if event['timestamp'] > cutoff
    ]

def _compute_auth_failure_rate_linux(self, parsed: Dict, state: ServerState, current_time: datetime) -> float:
    """Compute auth failure rate in 5m window"""
    recent_events = self._get_5m_events(state, current_time)
    
    if not recent_events:
        return 0.0
    
    failures = sum(1 for e in recent_events if e['event_type'] == 'auth_failure')
    return min(failures / len(recent_events), 1.0)  # Normalize to 0-1
```

---

## Event Type Encoding

### Normalization: String → Integer → Float (0-1)

**For each log type:**

```python
# STRING from parser
event_type = "auth_failure"

# INTEGER from enum (established in STEP 2)
event_type_code = EventTypeCode.AUTH_FAILURE.value  # 1

# FLOAT normalized (0-1) for ML input
max_type_code = 19  # Total event types
normalized = event_type_code / max_type_code  # 0.053
```

**Template ID normalization:**
```python
# From parser: template_id is integer 1-50
template_id = 16

# Normalize to 0-1 range
max_template = 50
normalized_template = template_id / max_template  # 0.32
```

---

## Testing Strategy

### Test 1: Per-Server Isolation
```python
def test_per_server_isolation():
    extractor = LinuxFeatureExtractor()
    
    # Server A log
    log_a = LogInternal(sid="server_a", timestamp=now, ...)
    features_a1 = extractor.extract(log_a)
    
    # Server B log (should not affect A's state)
    log_b = LogInternal(sid="server_b", timestamp=now, ...)
    features_b = extractor.extract(log_b)
    
    # Server A again (should continue from previous state)
    log_a2 = LogInternal(sid="server_a", timestamp=now, ...)
    features_a2 = extractor.extract(log_a2)
    
    # Verify A1 → A2 are consistent, B doesn't interfere
```

### Test 2: Temporal Accuracy
```python
def test_temporal_window_accuracy():
    extractor = LinuxFeatureExtractor()
    
    # Log at T=0
    log1 = LogInternal(sid="s1", timestamp=datetime(2023, 1, 1, 10, 0, 0))
    extractor.extract(log1)
    
    # Log at T=4:59 (same 5m window)
    log2 = LogInternal(sid="s1", timestamp=datetime(2023, 1, 1, 10, 4, 59))
    features2 = extractor.extract(log2)
    # Should include log1 in 5m window
    
    # Log at T=5:01 (new 5m window)
    log3 = LogInternal(sid="s1", timestamp=datetime(2023, 1, 1, 10, 5, 1))
    features3 = extractor.extract(log3)
    # Should NOT include log1 in 5m window
```

### Test 3: Fixed Vector Length
```python
def test_feature_vector_is_fixed_length():
    extractor = LinuxFeatureExtractor()
    
    for i in range(100):
        log = LogInternal(sid="s1", timestamp=now + timedelta(seconds=i), ...)
        features = extractor.extract(log)
        
        assert isinstance(features, list), "Features must be list not dict"
        assert len(features) == 14, f"Linux must return exactly 14 features, got {len(features)}"
        assert all(isinstance(f, (int, float)) for f in features)
        assert all(0 <= f <= 1 for f in features), "All features must be normalized 0-1"
```

---

## Implementation Checklist

- [ ] **LinuxFeatureExtractor**: 
  - [ ] Create `LinuxServerState` class
  - [ ] Add per-sid state tracking
  - [ ] Replace `datetime.now()` with `log_internal.timestamp`
  - [ ] Implement 14-feature vector
  - [ ] Update tests

- [ ] **WindowsFeatureExtractor**:
  - [ ] Create `WindowsServerState` class
  - [ ] Remove singleton pattern
  - [ ] Add per-sid state tracking
  - [ ] Replace `datetime.now()` with `log_internal.timestamp`
  - [ ] Implement 12-feature vector
  - [ ] Update tests

- [ ] **ZookeeperFeatureExtractor**:
  - [ ] Create `ZookeeperServerState` class
  - [ ] Remove singleton pattern
  - [ ] Add per-sid state tracking
  - [ ] Replace `datetime.now()` with `log_internal.timestamp`
  - [ ] Implement 10-feature vector
  - [ ] Update tests

- [ ] **Feature Extractor Factory**:
  - [ ] ~~Update factory for per-sid instances~~ (single instance is OK, uses per-sid state internally)
  - [ ] Verify backward compatibility

- [ ] **Test Suite Updates**:
  - [ ] Fix imports (remove ParsedZookeeperLogEvent reference)
  - [ ] Update assertions for List[float] instead of Dict
  - [ ] Add per-server isolation tests
  - [ ] Add temporal window accuracy tests

---

## Feature Computation Examples

### Example: Linux Auth Failure Rate

**Current (broken):**
```python
def _extract_ip_features(self, ip: str) -> Dict[str, float]:
    recent_failures = [
        t for t in self.ip_failure_times.get(ip, [])
        if (datetime.now() - t).total_seconds() < 300  # ❌ Uses wall clock
    ]
    return {
        "ip_auth_failures_5m": len(recent_failures),
        "ip_failure_rate": len(recent_failures) / max(self.ip_total_events.get(ip, 1), 1)
    }
```

**New (correct):**
```python
def _compute_ip_auth_failure_rate(
    self, ip: Optional[str], state: LinuxServerState, current_time: datetime
) -> float:
    if not ip:
        return 0.0
    
    # Get events in last 5 minutes using LOG TIME, not wall clock
    cutoff = current_time - timedelta(minutes=5)
    recent_events = [
        e for e in state.event_timestamp_queue
        if e['ip'] == ip and e['timestamp'] > cutoff
    ]
    
    if not recent_events:
        return 0.0
    
    failures = sum(1 for e in recent_events if e['event_type'] == 'auth_failure')
    rate = failures / len(recent_events)
    
    return min(rate, 1.0)  # Normalize to [0, 1]
```

---

## Success Criteria

✅ **All feature extractors must:**
1. Return `List[float]` (not Dict) with fixed length
2. Use `log_internal.timestamp` for all temporal calculations (not `datetime.now()`)
3. Maintain per-server state isolated by `log_internal.sid`
4. Produce normalized features (all values in 0-1 range)
5. Pass all test cases with 100% coverage of event types
6. Handle edge cases (first event, no history, etc.)

✅ **No breaking changes to:**
- ParserFactory interface
- FeatureExtractorFactory interface
- LogInternal model

---

## Migration Path

**Phase 1:** Refactor feature extractors (this task)
- Keep factory interface stable
- Internal state management changes only
- New tests validate behavior

**Phase 2:** Update ML pipeline (STEP 6)
- Adjust LSTM input layer for fixed-length List[float]
- No parser/factory changes needed

**Phase 3:** Update test suites (STEP 7)
- Fix import statements
- Update assertions for new output format

