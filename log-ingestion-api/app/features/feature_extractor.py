from collections import defaultdict
from datetime import timedelta
from typing import Dict

class FeatureExtractor:
    """
    Converts parsed logs into ML-ready numerical features.
    """
    def __init__(self):
        # Store simple temporal state
        self.user_login_history = defaultdict(list)
        self.error_history = []

    def extract(self, log) -> Dict:
        """
        Extract numerical features from parsed log.
        """
        features = {}
        parsed = log.metadata.get("parsed", {})
        event_type = parsed.get("event_type", "unknown")
        now = log.timestamp

        # Feature 1: login frequency
        if event_type == "login":
            user = parsed.get("user")
            self.user_login_history[user].append(now)

            # remove old entries
            window = now - timedelta(minutes=5)

            self.user_login_history[user] = [t for t in self.user_login_history[user] if t > window]

            features["login_count_last_5min"] = len(self.user_login_history[user])

        else:
            features["login_count_last_5min"] = 0

        # Feature 2: error frequency
        if event_type == "service_error": 
            self.error_history.append(now)

        window = now - timedelta(minutes=5)
        self.error_history = [t for t in self.error_history if t > window]
        features["error_count_last_5min"] = len(self.error_history)

        # Feature 3: event type encoding
        event_encoding = {
            "login": 1,
            "service_error": 2,
            "unknown": 0
        }

        features["event_type_code"] = event_encoding.get(event_type, 0)

        return features
