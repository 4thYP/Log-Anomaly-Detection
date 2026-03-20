from collections import defaultdict, deque
from typing import List, Dict


class SequenceBuilder:
    """
    Builds sequences of feature vectors for LSTM training/inference.
    """

    def __init__(self, sequence_length: int = 5):

        self.sequence_length = sequence_length

        # Maintain sequences per server (important!)
        self.server_sequences = defaultdict(
            lambda: deque(maxlen=sequence_length)
        )

    def build_sequence(self, log) -> Dict:
        """
        Add log to sequence and return sequence if ready.
        """

        sid = log.sid

        features = log.metadata.get("features", {})

        # Convert features → vector
        feature_vector = self._to_vector(features)

        # Append to server-specific sequence
        self.server_sequences[sid].append(feature_vector)

        # If sequence not full yet → skip
        if len(self.server_sequences[sid]) < self.sequence_length:
            return {
                "ready": False,
                "sequence": None
            }

        # Return sequence
        sequence = list(self.server_sequences[sid])

        return {
            "ready": True,
            "sequence": sequence
        }

    def _to_vector(self, features: Dict) -> List[float]:
        """
        Convert feature dict into ordered numeric vector.
        """

        return [
            features.get("event_type_code", 0),
            features.get("failed_login_count_user_5min", 0),
            features.get("failed_login_count_ip_5min", 0),
            features.get("session_active", 0),
            features.get("session_duration", 0),
            features.get("ftp_connection_count_5min", 0),
            features.get("system_alert_count_10min", 0),
            features.get("risk_score", 0)
        ]
