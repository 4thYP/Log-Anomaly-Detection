from collections import defaultdict
from datetime import timedelta
from typing import Dict


class LinuxFeatureExtractor:
    """
    Stateful feature extractor for Linux logs.
    Designed for LSTM + anomaly detection + analytics.
    """

    def __init__(self):

        # ===== USER BEHAVIOR =====
        self.user_login_history = defaultdict(list)

        # ===== IP BEHAVIOR =====
        self.ip_activity = defaultdict(list)

        # ===== SYSTEM BEHAVIOR =====
        self.system_events = []

        # ===== SESSION TRACKING =====
        self.active_sessions = {}

    def extract(self, log) -> Dict:

        parsed = log.metadata.get("parsed", {})
        event_type = parsed.get("event_type")

        timestamp = log.timestamp

        features = {}

        # ==================================================
        # 1. LOGIN FAILURE BEHAVIOR (CRITICAL FOR SECURITY)
        # ==================================================

        if event_type == "auth_failure":

            user = parsed.get("user", "unknown")
            ip = parsed.get("ip", "unknown")

            self.user_login_history[user].append(timestamp)
            self.ip_activity[ip].append(timestamp)

            window = timestamp - timedelta(minutes=5)

            # Clean old entries
            self.user_login_history[user] = [
                t for t in self.user_login_history[user] if t > window
            ]

            self.ip_activity[ip] = [
                t for t in self.ip_activity[ip] if t > window
            ]

            features["failed_login_count_user_5min"] = len(self.user_login_history[user])
            features["failed_login_count_ip_5min"] = len(self.ip_activity[ip])

        else:
            features["failed_login_count_user_5min"] = 0
            features["failed_login_count_ip_5min"] = 0

        # ==================================================
        # 2. SESSION TRACKING (VERY IMPORTANT FOR LSTM)
        # ==================================================

        if event_type == "session_open":
            user = parsed.get("user")

            self.active_sessions[user] = timestamp

            features["session_active"] = 1

        elif event_type == "session_close":
            user = parsed.get("user")

            if user in self.active_sessions:
                duration = (timestamp - self.active_sessions[user]).total_seconds()

                features["session_duration"] = duration

                del self.active_sessions[user]
            else:
                features["session_duration"] = 0

            features["session_active"] = 0

        else:
            features["session_active"] = 0
            features["session_duration"] = 0

        # ==================================================
        # 3. FTP / NETWORK ACTIVITY
        # ==================================================

        if event_type == "ftp_connection":

            ip = parsed.get("ip", "unknown")
            self.ip_activity[ip].append(timestamp)

            window = timestamp - timedelta(minutes=5)

            self.ip_activity[ip] = [
                t for t in self.ip_activity[ip] if t > window
            ]

            features["ftp_connection_count_5min"] = len(self.ip_activity[ip])

        else:
            features["ftp_connection_count_5min"] = 0

        # ==================================================
        # 4. SYSTEM ANOMALIES
        # ==================================================

        if event_type == "system_alert":
            self.system_events.append(timestamp)

        window = timestamp - timedelta(minutes=10)

        self.system_events = [
            t for t in self.system_events if t > window
        ]

        features["system_alert_count_10min"] = len(self.system_events)

        # ==================================================
        # 5. EVENT TYPE ENCODING (IMPORTANT FOR LSTM)
        # ==================================================

        event_encoding = {
            "auth_failure": 1,
            "invalid_user": 2,
            "session_open": 3,
            "session_close": 4,
            "ftp_connection": 5,
            "system_alert": 6,
            "other": 0
        }

        features["event_type_code"] = event_encoding.get(event_type, 0)

        # ==================================================
        # 6. RISK SCORE (VERY USEFUL FOR DASHBOARD)
        # ==================================================

        risk_score = 0

        if features["failed_login_count_user_5min"] > 5:
            risk_score += 2

        if features["failed_login_count_ip_5min"] > 10:
            risk_score += 3

        if features["system_alert_count_10min"] > 2:
            risk_score += 2

        features["risk_score"] = risk_score

        return features
