"""
Production-grade Zookeeper event log parser for Loghub dataset.
Handles distributed consensus logs from Zookeeper quorum members.
Uses unified ParsedLogEvent schema for consistent processing.
"""

import re
from typing import Dict, Optional, Any, Tuple
from datetime import datetime

from app.parsers.base_parser import BaseParser
from app.parsers.log_event_schema import (
    ParsedLogEvent,
    EventGroup,
    ZookeeperEventType,
    template_id_from_csv,
)

class ZookeeperParser(BaseParser):
    """
    Parser for Zookeeper distributed consensus logs from Loghub dataset.

    Handles:
    - Connection management (listened/received/broken connections)
    - Leader election (notifications, state transitions, voting)
    - Session lifecycle (established, expired, revalidated)
    - Worker control (SendWorker, RecvWorker, interruption)
    - Quorum operations (consensus, follower info)
    - Data operations (snapshots, transaction logs)
    - Error events (exceptions, timeouts, connection failures)
    """

    # ============================================================================
    # REGEX PATTERNS - Production-grade with extensive coverage
    # ============================================================================

    # Header pattern: "YYYY-MM-DD HH:MM:SS,mmm - LEVEL [Node:Component@LineNum] - Message"
    HEADER_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2},\d{3})\s+-\s+(\w+)\s+\[(.*?)\]\s+-\s+(.+)$"
    )

    # Component extraction: Different formats for different workers
    # Format 1: QuorumPeer[myid=N]/IP:Port:Component@LineNum
    # Format 2: /IP:Port:Component@LineNum
    # Format 3: WorkerType:ID:Component@LineNum
    COMPONENT_DETAIL_PATTERN = re.compile(
        r"(?:QuorumPeer\[myid=(\d+)\])?/?(?:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+):)?(.+?)(?::(\d+))?:([^@]+)@(\d+)"
    )

    # IP:Port patterns
    IP_PORT_PATTERN = re.compile(r"/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)")

    # ============================================================================
    # CONNECTION EVENTS
    # ============================================================================

    # E40: Received connection request /10.10.34.11:45307
    RECEIVED_CONNECTION_PATTERN = re.compile(
        r"Received connection request\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E1: GOODBYE
    GOODBYE_PATTERN = re.compile(r"\*+\s+GOODBYE\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)")

    # E2: Accepted socket connection
    ACCEPTED_SOCKET_PATTERN = re.compile(
        r"Accepted socket connection from\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E5: Cannot open channel to remote
    CANNOT_OPEN_CHANNEL_PATTERN = re.compile(
        r"Cannot open channel to\s+(\d+)\s+at election address\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E11: Connection broken for id <id>, my id = <myid>, error =
    CONNECTION_BROKEN_PATTERN = re.compile(
        r"Connection broken for id\s+(\d+),\s+my id\s+=\s+(\d+),\s+error\s+="
    )

    # E9: Closed socket connection for client (no session)
    CLOSED_SOCKET_NO_SESSION_PATTERN = re.compile(
        r"Closed socket connection for client\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)\s+\(no session established"
    )

    # E10: Closed socket connection for client (with session)
    CLOSED_SOCKET_WITH_SESSION_PATTERN = re.compile(
        r"Closed socket connection for client\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)\s+which had sessionid\s+(\w+)"
    )

    # ============================================================================
    # LEADER ELECTION
    # ============================================================================

    # E31: Notification time out: 3200
    NOTIFICATION_TIMEOUT_PATTERN = re.compile(r"Notification time out:\s+(\d+)")

    # E32-E37: Notification patterns with full state
    NOTIFICATION_PATTERN = re.compile(
        r"Notification:\s+(\d+)\s+\(n\.leader\),\s+(\d+)\s+\(n\.zxid\),\s+(\d+)\s+\(n\.round\),\s+(\w+)\s+\(n\.state\),\s+(\d+)\s+\(n\.sid\),\s+(\d+)\s+\(n\.peerEpoch\),\s+(\w+)\s+\(my state\)"
    )

    # E30: New election. My id = <N>, proposed zxid=<Z>
    NEW_ELECTION_PATTERN = re.compile(
        r"New election\.\s+My id\s+=\s+(\d+),\s+proposed zxid=(\d+)"
    )

    # State transitions: LOOKING, FOLLOWING, LEADING
    LOOKING_PATTERN = re.compile(r"\bLOOKING\b")
    FOLLOWING_PATTERN = re.compile(r"\bFOLLOWING\b")
    LEADING_PATTERN = re.compile(r"\bLEADING\b")

    # E18: FOLLOWING
    FOLLOWING_LITERAL_PATTERN = re.compile(r"^FOLLOWING$")

    # E26: LOOKING
    LOOKING_LITERAL_PATTERN = re.compile(r"^LOOKING$")

    # E19: FOLLOWING - LEADER ELECTION TOOK - <time>
    LEADER_ELECTION_TOOK_PATTERN = re.compile(
        r"FOLLOWING\s*-\s*LEADER ELECTION TOOK\s*-\s+(\d+)"
    )

    # ============================================================================
    # SESSION MANAGEMENT
    # ============================================================================

    # E13: Established session <sid> with negotiated timeout <ms> for client <ip>:<port>
    ESTABLISHED_SESSION_PATTERN = re.compile(
        r"Established session\s+(\w+)\s+with negotiated timeout\s+(\d+)\s+for client\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E8: Client attempting to renew session
    RENEW_SESSION_PATTERN = re.compile(
        r"Client attempting to renew session\s+(\w+)\s+at\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E7: Client attempting to establish new session
    NEW_SESSION_PATTERN = re.compile(
        r"Client attempting to establish new session at\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"
    )

    # E15: Expiring session <sid>, timeout of <ms>ms exceeded
    EXPIRING_SESSION_PATTERN = re.compile(
        r"Expiring session\s+(\w+),\s+timeout of\s+(\d+)ms exceeded"
    )

    # E41: Revalidating client
    REVALIDATING_CLIENT_PATTERN = re.compile(r"Revalidating client:\s+(\w+)")

    # ============================================================================
    # WORKER CONTROL
    # ============================================================================

    # E24: Interrupted while waiting for message on queue
    INTERRUPTED_WAITING_PATTERN = re.compile(
        r"Interrupted while waiting for message on queue"
    )

    # E25: Interrupting SendWorker
    INTERRUPTING_SENDWORKER_PATTERN = re.compile(r"Interrupting SendWorker")

    # E42: Send worker leaving thread
    SEND_WORKER_LEAVING_PATTERN = re.compile(r"Send worker leaving thread")

    # ============================================================================
    # QUORUM OPERATIONS
    # ============================================================================

    # E22: Have quorum of supporters; starting up and setting last processed zxid
    HAVE_QUORUM_PATTERN = re.compile(
        r"Have quorum of supporters;\s+starting up and setting last processed zxid:\s+(\d+)"
    )

    # E23: Have smaller server identifier, so dropping the connection
    SMALLER_SERVER_ID_PATTERN = re.compile(
        r"Have smaller server identifier,\s+so dropping the connection:\s+\((\d+),\s+(\d+)\)"
    )

    # E17: Follower sid: <id> : info : <class>@<addr>
    FOLLOWER_INFO_PATTERN = re.compile(
        r"Follower sid:\s+(\d+)\s+:\s+info\s+:\s+org\.apache\.zookeeper\.server\.quorum\.QuorumPeer"
    )

    # E20: Getting a snapshot from leader
    GETTING_SNAPSHOT_PATTERN = re.compile(r"Getting a snapshot from leader")

    # E22 variant: Have quorum
    QUORUM_ACHIEVED_PATTERN = re.compile(
        r"Have quorum of supporters"
    )

    # ============================================================================
    # SNAPSHOT/DATA
    # ============================================================================

    # E39: Reading snapshot
    READING_SNAPSHOT_PATTERN = re.compile(r"Reading snapshot\s+(\d+)")

    # E46: Snapshotting
    SNAPSHOTTING_PATTERN = re.compile(r"Snapshotting:\s+(\d+)\s+to\s+(.+)")

    # ============================================================================
    # ERROR/EXCEPTION
    # ============================================================================

    # E6: caught end of stream exception
    END_OF_STREAM_PATTERN = re.compile(r"caught end of stream exception")

    # E14: Exception causing close of session
    SESSION_EXCEPTION_PATTERN = re.compile(
        r"Exception causing close of session\s+(\w+)\s+due to (.+)"
    )

    # E49: Unexpected exception causing shutdown
    UNEXPECTED_EXCEPTION_SHUTDOWN_PATTERN = re.compile(
        r"Unexpected exception causing shutdown while sock still open"
    )

    # E50: Unexpected Exception
    UNEXPECTED_EXCEPTION_PATTERN = re.compile(r"Unexpected Exception:")

    # E21: KeeperException
    KEEPER_EXCEPTION_PATTERN = re.compile(
        r"Got user-level KeeperException when processing sessionid:(\w+)"
    )

    # ============================================================================
    # CONFIGURATION
    # ============================================================================

    # E3: autopurge.purgeInterval
    AUTOPURGE_INTERVAL_PATTERN = re.compile(r"autopurge\.purgeInterval set to\s+(\d+)")

    # E4: autopurge.snapRetainCount
    AUTOPURGE_RETAIN_PATTERN = re.compile(r"autopurge\.snapRetainCount set to\s+(\d+)")

    # E27: maxSessionTimeout
    MAX_SESSION_TIMEOUT_PATTERN = re.compile(r"maxSessionTimeout set to\s+(\d+)")

    # E28: minSessionTimeout
    MIN_SESSION_TIMEOUT_PATTERN = re.compile(r"minSessionTimeout set to\s+(\d+)")

    # E48: tickTime
    TICK_TIME_PATTERN = re.compile(r"tickTime set to\s+(\d+)")

    # ============================================================================
    # OTHER
    # ============================================================================

    # E44: Server environment
    SERVER_ENVIRONMENT_PATTERN = re.compile(r"Server environment:(.+)")

    # E45: shutdown of request processor complete
    SHUTDOWN_COMPLETE_PATTERN = re.compile(r"shutdown of request processor complete")

    # E47: Starting quorum peer
    STARTING_QUORUM_PEER_PATTERN = re.compile(r"Starting quorum peer")

    # E29: My election bind port
    ELECTION_BIND_PORT_PATTERN = re.compile(
        r"My election bind port:\s+/?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+):(\d+)"
    )

    # ============================================================================
    # PARSER IMPLEMENTATION
    # ============================================================================

    def parse(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a single Zookeeper event log line into ParsedLogEvent format.

        Args:
            log_line: Raw event log line

        Returns:
            Dictionary representation of ParsedLogEvent (via .to_dict())
        """
        try:
            # Parse header
            header_match = self.HEADER_PATTERN.match(log_line)
            if not header_match:
                return self._unknown_log(log_line)

            date_str, time_str, level, node_component, message = header_match.groups()
            
            # Extract and normalize timestamp to ISO 8601
            timestamp = self._parse_timestamp(date_str, time_str)

            # Extract component details
            node_details = self._parse_node_component(node_component)

            # Route to appropriate parser based on message type
            if self.RECEIVED_CONNECTION_PATTERN.search(message):
                return self._parse_received_connection(
                    message, level, node_details, timestamp, log_line
                )
            elif self.GOODBYE_PATTERN.search(message):
                return self._parse_goodbye(message, level, node_details, timestamp, log_line)
            elif self.ACCEPTED_SOCKET_PATTERN.search(message):
                return self._parse_accepted_socket(
                    message, level, node_details, timestamp, log_line
                )
            elif self.CANNOT_OPEN_CHANNEL_PATTERN.search(message):
                return self._parse_cannot_open_channel(
                    message, level, node_details, timestamp, log_line
                )
            elif self.CONNECTION_BROKEN_PATTERN.search(message):
                return self._parse_connection_broken(
                    message, level, node_details, timestamp, log_line
                )
            elif self.CLOSED_SOCKET_WITH_SESSION_PATTERN.search(message):
                return self._parse_closed_socket_with_session(
                    message, level, node_details, timestamp, log_line
                )
            elif self.CLOSED_SOCKET_NO_SESSION_PATTERN.search(message):
                return self._parse_closed_socket_no_session(
                    message, level, node_details, timestamp, log_line
                )
            elif self.NOTIFICATION_PATTERN.search(message):
                return self._parse_notification(message, level, node_details, timestamp, log_line)
            elif self.NOTIFICATION_TIMEOUT_PATTERN.search(message):
                return self._parse_notification_timeout(
                    message, level, node_details, timestamp, log_line
                )
            elif self.NEW_ELECTION_PATTERN.search(message):
                return self._parse_new_election(message, level, node_details, timestamp, log_line)
            elif self.LEADER_ELECTION_TOOK_PATTERN.search(message):
                return self._parse_leader_election_took(
                    message, level, node_details, timestamp, log_line
                )
            elif self.FOLLOWING_LITERAL_PATTERN.search(message):
                return self._parse_following(message, level, node_details, timestamp, log_line)
            elif self.LOOKING_LITERAL_PATTERN.search(message):
                return self._parse_looking(message, level, node_details, timestamp, log_line)
            elif self.ESTABLISHED_SESSION_PATTERN.search(message):
                return self._parse_established_session(
                    message, level, node_details, timestamp, log_line
                )
            elif self.RENEW_SESSION_PATTERN.search(message):
                return self._parse_renew_session(
                    message, level, node_details, timestamp, log_line
                )
            elif self.NEW_SESSION_PATTERN.search(message):
                return self._parse_new_session(message, level, node_details, timestamp, log_line)
            elif self.EXPIRING_SESSION_PATTERN.search(message):
                return self._parse_expiring_session(
                    message, level, node_details, timestamp, log_line
                )
            elif self.REVALIDATING_CLIENT_PATTERN.search(message):
                return self._parse_revalidating_client(
                    message, level, node_details, timestamp, log_line
                )
            elif self.INTERRUPTED_WAITING_PATTERN.search(message):
                return self._parse_interrupted_waiting(
                    message, level, node_details, timestamp, log_line
                )
            elif self.INTERRUPTING_SENDWORKER_PATTERN.search(message):
                return self._parse_interrupting_sendworker(
                    message, level, node_details, timestamp, log_line
                )
            elif self.SEND_WORKER_LEAVING_PATTERN.search(message):
                return self._parse_send_worker_leaving(
                    message, level, node_details, timestamp, log_line
                )
            elif self.HAVE_QUORUM_PATTERN.search(message):
                return self._parse_have_quorum(message, level, node_details, timestamp, log_line)
            elif self.SMALLER_SERVER_ID_PATTERN.search(message):
                return self._parse_smaller_server_id(
                    message, level, node_details, timestamp, log_line
                )
            elif self.FOLLOWER_INFO_PATTERN.search(message):
                return self._parse_follower_info(message, level, node_details, timestamp, log_line)
            elif self.GETTING_SNAPSHOT_PATTERN.search(message):
                return self._parse_getting_snapshot(
                    message, level, node_details, timestamp, log_line
                )
            elif self.READING_SNAPSHOT_PATTERN.search(message):
                return self._parse_reading_snapshot(
                    message, level, node_details, timestamp, log_line
                )
            elif self.SNAPSHOTTING_PATTERN.search(message):
                return self._parse_snapshotting(
                    message, level, node_details, timestamp, log_line
                )
            elif self.END_OF_STREAM_PATTERN.search(message):
                return self._parse_end_of_stream(
                    message, level, node_details, timestamp, log_line
                )
            elif self.SESSION_EXCEPTION_PATTERN.search(message):
                return self._parse_session_exception(
                    message, level, node_details, timestamp, log_line
                )
            elif self.UNEXPECTED_EXCEPTION_SHUTDOWN_PATTERN.search(message):
                return self._parse_unexpected_exception_shutdown(
                    message, level, node_details, timestamp, log_line
                )
            elif self.UNEXPECTED_EXCEPTION_PATTERN.search(message):
                return self._parse_unexpected_exception(
                    message, level, node_details, timestamp, log_line
                )
            elif self.KEEPER_EXCEPTION_PATTERN.search(message):
                return self._parse_keeper_exception(
                    message, level, node_details, timestamp, log_line
                )
            elif self.AUTOPURGE_INTERVAL_PATTERN.search(message):
                return self._parse_config_param(
                    message, level, node_details, timestamp, log_line, "autopurge_interval", "E3"
                )
            elif self.AUTOPURGE_RETAIN_PATTERN.search(message):
                return self._parse_config_param(
                    message, level, node_details, timestamp, log_line, "autopurge_retain", "E4"
                )
            elif self.MAX_SESSION_TIMEOUT_PATTERN.search(message):
                return self._parse_config_param(
                    message, level, node_details, timestamp, log_line, "max_session_timeout", "E27"
                )
            elif self.MIN_SESSION_TIMEOUT_PATTERN.search(message):
                return self._parse_config_param(
                    message, level, node_details, timestamp, log_line, "min_session_timeout", "E28"
                )
            elif self.TICK_TIME_PATTERN.search(message):
                return self._parse_config_param(
                    message, level, node_details, timestamp, log_line, "tick_time", "E48"
                )
            elif self.SERVER_ENVIRONMENT_PATTERN.search(message):
                return self._parse_server_environment(
                    message, level, node_details, timestamp, log_line
                )
            elif self.SHUTDOWN_COMPLETE_PATTERN.search(message):
                return self._parse_shutdown_complete(
                    message, level, node_details, timestamp, log_line
                )
            elif self.STARTING_QUORUM_PEER_PATTERN.search(message):
                return self._parse_starting_quorum_peer(
                    message, level, node_details, timestamp, log_line
                )
            elif self.ELECTION_BIND_PORT_PATTERN.search(message):
                return self._parse_election_bind_port(
                    message, level, node_details, timestamp, log_line
                )
            else:
                # Generic system info
                return self._parse_generic(message, level, node_details, timestamp, log_line)

        except Exception as e:
            return self._unknown_log(log_line, str(e))

    # ============================================================================
    # COMPONENT PARSING
    # ============================================================================

    def _parse_node_component(self, node_component: str) -> Dict[str, Any]:
        """Extract node, component, and worker details from component field"""
        details = {
            "local_node_id": None,
            "local_ip": None,
            "local_port": None,
            "component": "",
            "worker_type": None,
            "socket_id": None,
            "line_num": None,
        }

        # Try format: QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:FastLeaderElection@774
        if "QuorumPeer" in node_component and "[myid=" in node_component:
            match = re.search(r"\[myid=(\d+)\]", node_component)
            if match:
                details["local_node_id"] = int(match.group(1))
            # Extract component name
            match = re.search(r":(\w+)@(\d+)", node_component)
            if match:
                details["component"] = match.group(1)
                details["line_num"] = int(match.group(2))

        # Try format: /10.10.34.11:3888:QuorumCnxManager$Listener@493
        elif node_component.startswith("/"):
            match = re.match(
                r"/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+):([^@]+)@(\d+)",
                node_component,
            )
            if match:
                details["local_ip"] = match.group(1)
                details["local_port"] = int(match.group(2))
                details["component"] = match.group(3)
                details["line_num"] = int(match.group(4))

        # Try format: SendWorker:188978561024:QuorumCnxManager$SendWorker@688
        elif ":" in node_component and "@" in node_component:
            parts = node_component.split(":")
            if len(parts) >= 2:
                details["worker_type"] = parts[0]
                details["socket_id"] = parts[1]
                if len(parts) >= 3:
                    match = re.search(r"([^@]+)@(\d+)", ":".join(parts[2:]))
                    if match:
                        details["component"] = match.group(1)
                        details["line_num"] = int(match.group(2))

        # Default: extract component from string
        if not details["component"]:
            match = re.search(r"([^\[@:]+)@", node_component)
            if match:
                details["component"] = match.group(1)

        return details

    # ============================================================================
    # EVENT PARSERS
    # ============================================================================

    def _parse_received_connection(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E40: Received connection request"""
        match = self.RECEIVED_CONNECTION_PATTERN.search(message)
        if match:
            remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="connection_received",
                component=node_details.get("component"),
                template_id="E40",
                template="Received connection request /<*>:<*>",
                timestamp=timestamp,
                level=level,
                local_ip=node_details.get("local_ip"),
                local_port=node_details.get("local_port"),
                remote_ip=remote_ip,
                remote_port=int(remote_port) if remote_port else None,
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_goodbye(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E1: GOODBYE"""
        match = self.GOODBYE_PATTERN.search(message)
        if match:
            remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="connection_goodbye",
                component=node_details.get("component"),
                template_id="E1",
                template="******* GOODBYE /<*>:<*> ********",
                timestamp=timestamp,
                level=level,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_accepted_socket(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E2: Accepted socket connection"""
        match = self.ACCEPTED_SOCKET_PATTERN.search(message)
        if match:
            remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="connection_accepted",
                component=node_details.get("component"),
                template_id="E2",
                template="Accepted socket connection from /<*>:<*>",
                timestamp=timestamp,
                level=level,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_cannot_open_channel(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E5: Cannot open channel to remote peer"""
        match = self.CANNOT_OPEN_CHANNEL_PATTERN.search(message)
        if match:
            peer_id, remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="channel_error",
                component=node_details.get("component"),
                template_id="E5",
                template="Cannot open channel to <*> at election address /<*>:<*>",
                timestamp=timestamp,
                level=level,
                peer_id=int(peer_id),
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="failure",
                error_reason="Cannot open channel",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_connection_broken(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E11: Connection broken for id <id>, my id = <myid>"""
        match = self.CONNECTION_BROKEN_PATTERN.search(message)
        if match:
            peer_id, my_id = match.groups()
            return self._build_event(
                event_type="connection_broken",
                component=node_details.get("component"),
                template_id="E11",
                template="Connection broken for id <*>, my id = <*>, error =",
                timestamp=timestamp,
                level=level,
                peer_id=int(peer_id),
                my_id=int(my_id),
                status="failure",
                error_reason="Connection broken",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_closed_socket_with_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E10: Closed socket connection for client (with session)"""
        match = self.CLOSED_SOCKET_WITH_SESSION_PATTERN.search(message)
        if match:
            remote_ip, remote_port, session_id = match.groups()
            return self._build_event(
                event_type="session_closed",
                component=node_details.get("component"),
                template_id="E10",
                template="Closed socket connection for client /<*>:<*> which had sessionid <*>",
                timestamp=timestamp,
                level=level,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                session_id=session_id,
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_closed_socket_no_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E9: Closed socket connection for client (no session)"""
        match = self.CLOSED_SOCKET_NO_SESSION_PATTERN.search(message)
        if match:
            remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="session_closed",
                component=node_details.get("component"),
                template_id="E9",
                template="Closed socket connection for client /<*>:<*> (no session established for client)",
                timestamp=timestamp,
                level=level,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_notification(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E32-E37: Notification with full election state"""
        match = self.NOTIFICATION_PATTERN.search(message)
        if match:
            (
                leader,
                zxid,
                round_,
                state,
                sid,
                epoch,
                my_state,
            ) = match.groups()
            return self._build_event(
                event_type="election_notification",
                component=node_details.get("component"),
                template_id="E32-E37",
                template="Notification: <*> (n.leader), <*> (n.zxid), <*> (n.round), <*> (n.state), <*> (n.sid), <*> (n.peerEpoch), <*> (my state)",
                timestamp=timestamp,
                level=level,
                proposed_leader=int(leader),
                proposed_zxid=zxid,
                election_round=int(round_),
                election_state=my_state,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_notification_timeout(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E31: Notification time out"""
        match = self.NOTIFICATION_TIMEOUT_PATTERN.search(message)
        if match:
            timeout = int(match.group(1))
            return self._build_event(
                event_type="election_notification_timeout",
                component=node_details.get("component"),
                template_id="E31",
                template="Notification time out: <*>",
                timestamp=timestamp,
                level=level,
                notification_timeout=timeout,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_new_election(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E30: New election"""
        match = self.NEW_ELECTION_PATTERN.search(message)
        if match:
            my_id, proposed_zxid = match.groups()
            return self._build_event(
                event_type="election_start",
                component=node_details.get("component"),
                template_id="E30",
                template="New election. My id =  <*>, proposed zxid=<*>",
                timestamp=timestamp,
                level=level,
                my_id=int(my_id),
                proposed_zxid=proposed_zxid,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_leader_election_took(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E19: Leader election took <time>"""
        match = self.LEADER_ELECTION_TOOK_PATTERN.search(message)
        if match:
            time_ms = int(match.group(1))
            return self._build_event(
                event_type="election_took",
                component=node_details.get("component"),
                template_id="E19",
                template="FOLLOWING - LEADER ELECTION TOOK - <*>",
                timestamp=timestamp,
                level=level,
                timeout_ms=time_ms,
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_following(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E18: FOLLOWING state"""
        return self._build_event(
            event_type="election_state_change",
            component=node_details.get("component"),
            template_id="E18",
            template="FOLLOWING",
            timestamp=timestamp,
            level=level,
            election_state="FOLLOWING",
            status="success",
            raw_message=message,
        )

    def _parse_looking(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E26: LOOKING state"""
        return self._build_event(
            event_type="election_state_change",
            component=node_details.get("component"),
            template_id="E26",
            template="LOOKING",
            timestamp=timestamp,
            level=level,
            election_state="LOOKING",
            status="info",
            raw_message=message,
        )

    def _parse_established_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E13: Established session"""
        match = self.ESTABLISHED_SESSION_PATTERN.search(message)
        if match:
            session_id, timeout, remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="session_established",
                component=node_details.get("component"),
                template_id="E13",
                template="Established session <*> with negotiated timeout <*> for client /<*>:<*>",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                timeout_ms=int(timeout),
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_renew_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E8: Client attempting to renew session"""
        match = self.RENEW_SESSION_PATTERN.search(message)
        if match:
            session_id, remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="session_renew",
                component=node_details.get("component"),
                template_id="E8",
                template="Client attempting to renew session <*> at /<*>:<*>",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_new_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E7: Client attempting to establish new session"""
        match = self.NEW_SESSION_PATTERN.search(message)
        if match:
            remote_ip, remote_port = match.groups()
            return self._build_event(
                event_type="session_new",
                component=node_details.get("component"),
                template_id="E7",
                template="Client attempting to establish new session at /<*>:<*>",
                timestamp=timestamp,
                level=level,
                remote_ip=remote_ip,
                remote_port=int(remote_port),
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_expiring_session(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E15: Expiring session"""
        match = self.EXPIRING_SESSION_PATTERN.search(message)
        if match:
            session_id, timeout_ms = match.groups()
            return self._build_event(
                event_type="session_expired",
                component=node_details.get("component"),
                template_id="E15",
                template="Expiring session <*>, timeout of <*>ms exceeded",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                timeout_ms=int(timeout_ms),
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_revalidating_client(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E41: Revalidating client"""
        match = self.REVALIDATING_CLIENT_PATTERN.search(message)
        if match:
            session_id = match.group(1)
            return self._build_event(
                event_type="session_revalidation",
                component=node_details.get("component"),
                template_id="E41",
                template="Revalidating client: <*>",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_interrupted_waiting(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E24: Interrupted while waiting for message on queue"""
        return self._build_event(
            event_type="worker_interrupted",
            component=node_details.get("component"),
            template_id="E24",
            template="Interrupted while waiting for message on queue",
            timestamp=timestamp,
            level=level,
            worker_type=node_details.get("worker_type"),
            socket_id=node_details.get("socket_id"),
            status="warning",
            raw_message=message,
        )

    def _parse_interrupting_sendworker(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E25: Interrupting SendWorker"""
        return self._build_event(
            event_type="worker_interrupt_send",
            component=node_details.get("component"),
            template_id="E25",
            template="Interrupting SendWorker",
            timestamp=timestamp,
            level=level,
            worker_type=node_details.get("worker_type"),
            socket_id=node_details.get("socket_id"),
            status="warning",
            raw_message=message,
        )

    def _parse_send_worker_leaving(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E42: Send worker leaving thread"""
        return self._build_event(
            event_type="worker_send_leaving",
            component=node_details.get("component"),
            template_id="E42",
            template="Send worker leaving thread",
            timestamp=timestamp,
            level=level,
            worker_type="SendWorker",
            socket_id=node_details.get("socket_id"),
            status="warning",
            raw_message=message,
        )

    def _parse_have_quorum(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E22: Have quorum of supporters"""
        match = self.HAVE_QUORUM_PATTERN.search(message)
        if match:
            zxid = match.group(1)
            return self._build_event(
                event_type="quorum_achieved",
                component=node_details.get("component"),
                template_id="E22",
                template="Have quorum of supporters; starting up and setting last processed zxid: <*>",
                timestamp=timestamp,
                level=level,
                proposed_zxid=zxid,
                have_quorum=True,
                status="success",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_smaller_server_id(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E23: Have smaller server identifier"""
        match = self.SMALLER_SERVER_ID_PATTERN.search(message)
        if match:
            id1, id2 = match.groups()
            return self._build_event(
                event_type="connection_dropped",
                component=node_details.get("component"),
                template_id="E23",
                template="Have smaller server identifier, so dropping the connection: (<*>, <*>)",
                timestamp=timestamp,
                level=level,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_follower_info(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E17: Follower sid info"""
        match = self.FOLLOWER_INFO_PATTERN.search(message)
        if match:
            sid = int(match.group(1))
            return self._build_event(
                event_type="follower_info",
                component=node_details.get("component"),
                template_id="E17",
                template="Follower sid: <*> : info : org.apache.zookeeper.server.quorum.QuorumPeer$QuorumServer@<*>",
                timestamp=timestamp,
                level=level,
                peer_id=sid,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_getting_snapshot(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E20: Getting snapshot from leader"""
        return self._build_event(
            event_type="getting_snapshot",
            component=node_details.get("component"),
            template_id="E20",
            template="Getting a snapshot from leader",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    def _parse_reading_snapshot(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E39: Reading snapshot"""
        match = self.READING_SNAPSHOT_PATTERN.search(message)
        if match:
            snapshot_id = match.group(1)
            return self._build_event(
                event_type="snapshot_reading",
                component=node_details.get("component"),
                template_id="E39",
                template="Reading snapshot <*>",
                timestamp=timestamp,
                level=level,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_snapshotting(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E46: Snapshotting"""
        match = self.SNAPSHOTTING_PATTERN.search(message)
        if match:
            from_val, to_val = match.groups()
            return self._build_event(
                event_type="snapshot_writing",
                component=node_details.get("component"),
                template_id="E46",
                template="Snapshotting: <*> to <*>",
                timestamp=timestamp,
                level=level,
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_end_of_stream(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E6: End of stream exception"""
        return self._build_event(
            event_type="end_of_stream",
            component=node_details.get("component"),
            template_id="E6",
            template="caught end of stream exception",
            timestamp=timestamp,
            level=level,
            status="failure",
            error_reason="End of stream",
            raw_message=message,
        )

    def _parse_session_exception(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E14: Session exception"""
        match = self.SESSION_EXCEPTION_PATTERN.search(message)
        if match:
            session_id, error = match.groups()
            return self._build_event(
                event_type="server_not_running",
                component=node_details.get("component"),
                template_id="E14",
                template="Exception causing close of session <*> due to java.io.IOException: <*>",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                status="failure",
                error_reason=error,
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_unexpected_exception_shutdown(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E49: Unexpected exception shutdown"""
        return self._build_event(
            event_type="exception_error",
            component=node_details.get("component"),
            template_id="E49",
            template="Unexpected exception causing shutdown while sock still open",
            timestamp=timestamp,
            level=level,
            status="failure",
            error_reason="Unexpected exception",
            raw_message=message,
        )

    def _parse_unexpected_exception(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E50: Unexpected Exception"""
        return self._build_event(
            event_type="exception_error",
            component=node_details.get("component"),
            template_id="E50",
            template="Unexpected Exception:",
            timestamp=timestamp,
            level=level,
            status="failure",
            error_reason="Unexpected exception",
            raw_message=message,
        )

    def _parse_keeper_exception(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E21: KeeperException"""
        match = self.KEEPER_EXCEPTION_PATTERN.search(message)
        if match:
            session_id = match.group(1)
            return self._build_event(
                event_type="keeper_exception",
                component=node_details.get("component"),
                template_id="E21",
                template="Got user-level KeeperException when processing sessionid:<*> type:<*> cxid:<*> zxid:<*> txntype:<*> reqpath:<*> Error Path:<*> Error:<*>",
                timestamp=timestamp,
                level=level,
                session_id=session_id,
                status="failure",
                error_reason="KeeperException",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_config_param(
        self,
        message: str,
        level: str,
        node_details: Dict,
        timestamp: str,
        raw_log: str,
        param_name: str,
        template_id: str,
    ) -> Dict[str, Any]:
        """Configuration parameter set"""
        return self._build_event(
            event_type="config_set",
            component=node_details.get("component"),
            template_id=template_id,
            template=f"{param_name} set to <*>",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    def _parse_server_environment(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E44: Server environment"""
        return self._build_event(
            event_type="server_environment",
            component=node_details.get("component"),
            template_id="E44",
            template="Server environment:<*>",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    def _parse_shutdown_complete(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E45: Shutdown complete"""
        return self._build_event(
            event_type="shutdown_complete",
            component=node_details.get("component"),
            template_id="E45",
            template="shutdown of request processor complete",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    def _parse_starting_quorum_peer(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E47: Starting quorum peer"""
        return self._build_event(
            event_type="service_start",
            component=node_details.get("component"),
            template_id="E47",
            template="Starting quorum peer",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    def _parse_election_bind_port(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """E29: Election bind port"""
        match = self.ELECTION_BIND_PORT_PATTERN.search(message)
        if match:
            ip, port1, port2 = match.groups()
            return self._build_event(
                event_type="config_set",
                component=node_details.get("component"),
                template_id="E29",
                template="My election bind port: /<*>:<*>:<*>",
                timestamp=timestamp,
                level=level,
                local_ip=ip,
                local_port=int(port1),
                status="info",
                raw_message=message,
            )
        return self._unknown_log(raw_log)

    def _parse_generic(
        self, message: str, level: str, node_details: Dict, timestamp: str, raw_log: str
    ) -> Dict[str, Any]:
        """Generic fallback parser for unmatched logs"""
        return self._build_event(
            event_type="system_info",
            component=node_details.get("component"),
            template_id="",
            timestamp=timestamp,
            level=level,
            status="info",
            raw_message=message,
        )

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    @staticmethod
    def _parse_timestamp(date_str: str, time_str: str) -> str:
        """
        Parse timestamp from Zookeeper log header and convert to ISO 8601 format.
        
        Args:
            date_str: Date in "YYYY-MM-DD" format
            time_str: Time in "HH:MM:SS,mmm" format
            
        Returns:
            ISO 8601 timestamp string (YYYY-MM-DDTHH:MM:SS)
        """
        try:
            # Remove milliseconds from time_str: "HH:MM:SS,mmm" -> "HH:MM:SS"
            time_without_ms = time_str.split(',')[0]
            dt = datetime.strptime(f"{date_str} {time_without_ms}", "%Y-%m-%d %H:%M:%S")
            return dt.isoformat()
        except (ValueError, TypeError, IndexError):
            return ""

    @staticmethod
    def _get_event_group(event_type: str) -> str:
        """Map Zookeeper event types to standard event groups"""
        event_group_map = {
            # Connection events
            "connection_received": EventGroup.CONNECTION.value,
            "connection_broken": EventGroup.CONNECTION.value,
            "accepted_socket": EventGroup.CONNECTION.value,
            "cannot_open_channel": EventGroup.CONNECTION.value,
            "closed_socket_with_session": EventGroup.SESSION.value,
            "closed_socket_no_session": EventGroup.CONNECTION.value,
            "goodbye": EventGroup.CONNECTION.value,
            
            # Election events
            "election_notification": EventGroup.ELECTION.value,
            "election_state_change": EventGroup.ELECTION.value,
            "new_election": EventGroup.ELECTION.value,
            "leader_election_took": EventGroup.ELECTION.value,
            "following": EventGroup.ELECTION.value,
            "looking": EventGroup.ELECTION.value,
            "election_bind_port": EventGroup.ELECTION.value,
            
            # Session events
            "established_session": EventGroup.SESSION.value,
            "renew_session": EventGroup.SESSION.value,
            "new_session": EventGroup.SESSION.value,
            "expiring_session": EventGroup.SESSION.value,
            "revalidating_client": EventGroup.SESSION.value,
            
            # Worker events
            "interrupted_waiting": EventGroup.WORKER.value,
            "interrupting_sendworker": EventGroup.WORKER.value,
            "send_worker_leaving": EventGroup.WORKER.value,
            
            # Quorum events
            "have_quorum": EventGroup.QUORUM.value,
            "smaller_server_id": EventGroup.QUORUM.value,
            "follower_info": EventGroup.QUORUM.value,
            
            # Data/snapshot events
            "getting_snapshot": EventGroup.SYSTEM_INFO.value,
            "reading_snapshot": EventGroup.SYSTEM_INFO.value,
            "snapshotting": EventGroup.SYSTEM_INFO.value,
            "end_of_stream": EventGroup.SYSTEM_INFO.value,
            
            # Error events
            "session_exception": EventGroup.ERROR.value,
            "unexpected_exception_shutdown": EventGroup.ERROR.value,
            "unexpected_exception": EventGroup.ERROR.value,
            "keeper_exception": EventGroup.ERROR.value,
            
            # Configuration/system events
            "config_param": EventGroup.SYSTEM_INFO.value,
            "server_environment": EventGroup.SYSTEM_INFO.value,
            "shutdown_complete": EventGroup.SYSTEM_INFO.value,
            "starting_quorum_peer": EventGroup.SYSTEM_INFO.value,
            "generic": EventGroup.SYSTEM_INFO.value,
        }
        return event_group_map.get(event_type, EventGroup.UNKNOWN.value)

    def _build_event(
        self,
        event_type: str,
        component: str,
        template_id: Optional[str] = None,
        template: str = "",
        timestamp: str = "",
        level: str = "INFO",
        local_node_id: Optional[int] = None,
        local_ip: Optional[str] = None,
        local_port: Optional[int] = None,
        remote_ip: Optional[str] = None,
        remote_port: Optional[int] = None,
        peer_id: Optional[int] = None,
        worker_type: Optional[str] = None,
        socket_id: Optional[str] = None,
        election_state: Optional[str] = None,
        notification_timeout: Optional[int] = None,
        proposed_leader: Optional[int] = None,
        proposed_zxid: Optional[str] = None,
        election_round: Optional[int] = None,
        session_id: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        status: Optional[str] = None,
        error_reason: Optional[str] = None,
        my_id: Optional[int] = None,
        have_quorum: Optional[bool] = None,
        raw_message: str = "",
    ) -> Dict[str, Any]:
        """
        Build a ParsedLogEvent from Zookeeper components.
        
        Converts Zookeeper-specific data into unified ParsedLogEvent format.
        """
        # Convert template_id from string ("E40") to integer (40)
        template_id_int = 0
        if template_id:
            try:
                template_id_int = template_id_from_csv(template_id)
            except (ValueError, TypeError):
                template_id_int = 0
        
        # Get the event group for this event type
        event_group = self._get_event_group(event_type)
        
        # Build metadata dict with all optional/context-specific fields
        metadata = {}
        if local_node_id is not None:
            metadata["local_node_id"] = local_node_id
        if local_ip:
            metadata["local_ip"] = local_ip
        if local_port is not None:
            metadata["local_port"] = local_port
        if remote_ip:
            metadata["remote_ip"] = remote_ip
        if remote_port is not None:
            metadata["remote_port"] = remote_port
        if peer_id is not None:
            metadata["peer_id"] = peer_id
        if worker_type:
            metadata["worker_type"] = worker_type
        if socket_id:
            metadata["socket_id"] = socket_id
        if election_state:
            metadata["election_state"] = election_state
        if notification_timeout is not None:
            metadata["notification_timeout"] = notification_timeout
        if proposed_leader is not None:
            metadata["proposed_leader"] = proposed_leader
        if proposed_zxid:
            metadata["proposed_zxid"] = proposed_zxid
        if election_round is not None:
            metadata["election_round"] = election_round
        if session_id:
            metadata["session_id"] = session_id
        if timeout_ms is not None:
            metadata["timeout_ms"] = timeout_ms
        if my_id is not None:
            metadata["my_id"] = my_id
        if have_quorum is not None:
            metadata["have_quorum"] = have_quorum
        if raw_message:
            metadata["raw_message"] = raw_message
        if error_reason:
            metadata["error_reason"] = error_reason
        if level and level != "INFO":
            metadata["log_level"] = level
        
        # Create ParsedLogEvent with unified schema
        event = ParsedLogEvent(
            event_type=event_type,
            event_group=event_group,
            component=component,
            template=template if template else "",
            template_id=template_id_int,
            timestamp=timestamp,
            status=status if status else "info",
            metadata=metadata
        )
        
        return event.to_dict()

    def _unknown_log(self, log_line: str, error: str = "") -> Dict[str, Any]:
        """Handle unparseable logs using unified ParsedLogEvent schema"""
        return ParsedLogEvent.unknown_event(
            log_line=log_line[:200] if log_line else "",
            component="unknown",
            error=error if error else "Could not match header pattern"
        ).to_dict()
