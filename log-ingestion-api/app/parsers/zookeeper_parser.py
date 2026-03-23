import re
from typing import Dict
from app.parsers.base_parser import BaseParser


class ZookeeperParser(BaseParser):
    """
    Zookeeper Log Parser
    Handles various Zookeeper log formats including:
    - QuorumPeer logs
    - Leader election logs
    - Client connection logs
    - Session management logs
    - Network communication logs
    - And more
    """
    
    # ===== HEADER PATTERNS =====
    # Standard Zookeeper log format: YYYY-MM-DD HH:MM:SS,ms - LEVEL [COMPONENT:LINE] - Message
    header_pattern = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s+-\s+(?P<level>\w+)\s+\[(?P<component>[^\]]+)\]\s+-\s+(?P<message>.*)$"
    )
    
    # Alternative format without line numbers
    header_pattern_alt = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s+-\s+(?P<level>\w+)\s+\[(?P<component>[^:]+)[:\d+]*\]\s+-\s+(?P<message>.*)$"
    )
    
    # Simple format for some logs
    header_pattern_simple = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s+-\s+(?P<level>\w+)\s+(?P<component>\S+)\s+-\s+(?P<message>.*)$"
    )
    
    # ===== COMMON PATTERNS =====
    ip_pattern = re.compile(r'(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)')
    session_pattern = re.compile(r'(?:sessionid|session) (?P<session>0x[0-9a-fA-F]+)')
    port_pattern = re.compile(r':(?P<port>\d{4,5})')
    
    # ===== QUORUM PEER PATTERNS =====
    
    # Notification time out
    notification_timeout = re.compile(
        r'Notification time out: (?P<timeout>\d+)'
    )
    
    # New election
    new_election = re.compile(
        r'New election\. My id =  (?P<my_id>\d+), proposed zxid=(?P<zxid>0x[0-9a-fA-F]+)'
    )
    
    # FOLLOWING message
    following = re.compile(
        r'FOLLOWING(?: - LEADER ELECTION TOOK - (?P<duration>\d+))?'
    )
    
    # LOOKING state
    looking = re.compile(r'LOOKING')
    
    # LEADER ELECTION TOOK
    leader_election_took = re.compile(
        r'FOLLOWING - LEADER ELECTION TOOK - (?P<duration>\d+)'
    )
    
    # Getting a snapshot from leader
    getting_snapshot = re.compile(r'Getting a snapshot from leader')
    
    # Sending DIFF
    sending_diff = re.compile(r'Sending DIFF')
    
    # Snapshotting
    snapshotting = re.compile(
        r'Snapshotting: (?P<zxid>0x[0-9a-fA-F]+) to (?P<path>[^\s]+)'
    )
    
    # Reading snapshot
    reading_snapshot = re.compile(
        r'Reading snapshot (?P<path>[^\s]+)'
    )
    
    # Have quorum of supporters
    have_quorum = re.compile(
        r'Have quorum of supporters; starting up and setting last processed zxid: (?P<zxid>0x[0-9a-fA-F]+)'
    )
    
    # First is
    first_is = re.compile(r'First is (?P<value>0x[0-9a-fA-F]+)')
    
    # ===== QUORUM CONNECTION MANAGER PATTERNS =====
    
    # Received connection request
    received_connection = re.compile(
        r'Received connection request /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Cannot open channel
    cannot_open_channel = re.compile(
        r'Cannot open channel to (?P<peer_id>\d+) at election address /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Have smaller server identifier
    smaller_server_id = re.compile(
        r'Have smaller server identifier, so dropping the connection: \((?P<peer1>\d+), (?P<peer2>\d+)\)'
    )
    
    # My election bind port
    election_bind_port = re.compile(
        r'My election bind port: (?P<ip>[^:]+):(?P<port>\d+)'
    )
    
    # Send worker leaving thread
    send_worker_leaving = re.compile(r'Send worker leaving thread')
    
    # Interrupted while waiting for message on queue
    interrupted_waiting = re.compile(r'Interrupted while waiting for message on queue')
    
    # Interrupting SendWorker
    interrupting_send_worker = re.compile(r'Interrupting SendWorker')
    
    # Connection broken
    connection_broken = re.compile(
        r'Connection broken for id (?P<peer_id>\d+), my id = (?P<my_id>\d+), error ='
    )
    
    # ===== LEADER/FLLOWER/LEARNER PATTERNS =====
    
    # GOODBYE message
    goodbye = re.compile(
        r'\*\*\*\*\*\*\* GOODBYE /(?P<ip>[\d\.]+):(?P<port>\d+) \*\*\*\*\*\*\*'
    )
    
    # Unexpected exception causing shutdown
    unexpected_exception = re.compile(
        r'Unexpected exception causing shutdown while sock still open'
    )
    
    # Follower sid info
    follower_sid = re.compile(
        r'Follower sid: (?P<sid>\d+) : info : org\.apache\.zookeeper\.server\.quorum\.QuorumPeer\$QuorumServer@(?P<address>[0-9a-fA-F]+)'
    )
    
    # ===== NIOSERVER CONNECTION PATTERNS =====
    
    # Accepted socket connection
    accepted_connection = re.compile(
        r'Accepted socket connection from /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Closed socket connection (with session)
    closed_connection_with_session = re.compile(
        r'Closed socket connection for client /(?P<ip>[\d\.]+):(?P<port>\d+) which had sessionid (?P<session>0x[0-9a-fA-F]+)'
    )
    
    # Closed socket connection (no session)
    closed_connection_no_session = re.compile(
        r'Closed socket connection for client /(?P<ip>[\d\.]+):(?P<port>\d+) \(no session established for client\)'
    )
    
    # caught end of stream exception
    caught_end_of_stream = re.compile(r'caught end of stream exception')
    
    # Exception causing close of session
    exception_close_session = re.compile(
        r'Exception causing close of session (?P<session>0x[0-9a-fA-F]+) due to java\.io\.IOException: ZooKeeperServer not running'
    )
    
    # ===== ZOOKEEPER SERVER PATTERNS =====
    
    # Client attempting to establish new session
    client_new_session = re.compile(
        r'Client attempting to establish new session at /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Client attempting to renew session
    client_renew_session = re.compile(
        r'Client attempting to renew session (?P<session>0x[0-9a-fA-F]+) at /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Established session
    established_session = re.compile(
        r'Established session (?P<session>0x[0-9a-fA-F]+) with negotiated timeout (?P<timeout>\d+) for client /(?P<ip>[\d\.]+):(?P<port>\d+)'
    )
    
    # Expiring session
    expiring_session = re.compile(
        r'Expiring session (?P<session>0x[0-9a-fA-F]+), timeout of (?P<timeout>\d+)ms exceeded'
    )
    
    # Processed session termination
    session_termination = re.compile(
        r'Processed session termination for sessionid: (?P<session>0x[0-9a-fA-F]+)'
    )
    
    # Revalidating client
    revalidating_client = re.compile(
        r'Revalidating client: (?P<session>0x[0-9a-fA-F]+)'
    )
    
    # Connection request from old client
    old_client_connection = re.compile(
        r'Connection request from old client /(?P<ip>[\d\.]+):(?P<port>\d+); will be dropped if server is in r-o mode'
    )
    
    # ===== FAST LEADER ELECTION PATTERNS =====
    
    # Notification message
    notification = re.compile(
        r'Notification: (?P<leader>\d+) \(n\.leader\), (?P<zxid>0x[0-9a-fA-F]+) \(n\.zxid\), (?P<round>0x[0-9a-fA-F]+) \(n\.round\), (?P<state>\w+) \(n\.state\), (?P<sid>\d+) \(n\.sid\), (?P<epoch>0x[0-9a-fA-F]+) \(n\.peerEPoch\), (?P<my_state>\w+) \(my state\)'
    )
    
    # ===== ENVIRONMENT PATTERNS =====
    
    # Server environment
    server_environment = re.compile(
        r'Server environment:(?P<env_key>[^=]+)=(?P<env_value>.*)$'
    )
    
    # ===== TIMEOUT/SETTING PATTERNS =====
    
    # tickTime set
    tick_time = re.compile(r'tickTime set to (?P<tick_time>\d+)')
    
    # minSessionTimeout set
    min_session_timeout = re.compile(r'minSessionTimeout set to (?P<timeout>-?\d+)')
    
    # maxSessionTimeout set
    max_session_timeout = re.compile(r'maxSessionTimeout set to (?P<timeout>-?\d+)')
    
    # ===== AUTO PURGE PATTERNS =====
    
    # autopurge.snapRetainCount set
    autopurge_snap = re.compile(r'autopurge\.snapRetainCount set to (?P<count>\d+)')
    
    # autopurge.purgeInterval set
    autopurge_interval = re.compile(r'autopurge\.purgeInterval set to (?P<interval>\d+)')
    
    # ===== KEEPER EXCEPTION PATTERNS =====
    
    # Got user-level KeeperException
    keeper_exception = re.compile(
        r'Got user-level KeeperException when processing sessionid:(?P<session>0x[0-9a-fA-F]+) type:create cxid:(?P<cxid>0x[0-9a-fA-F]+) zxid:(?P<zxid>0x[0-9a-fA-F]+) txntype:(?P<txntype>-?\d+) reqpath:(?P<reqpath>[^ ]*) Error Path:(?P<error_path>[^ ]*) Error:KeeperErrorCode = NodeExists for (?P<node_path>[^\s]+)'
    )
    
    # ===== SHUTDOWN PATTERNS =====
    
    # shutdown of request processor complete
    shutdown_complete = re.compile(r'shutdown of request processor complete')
    
    # Starting quorum peer
    starting_quorum_peer = re.compile(r'Starting quorum peer')
    
    # ===== HELPER METHODS =====
    
    def _extract_component_details(self, component: str) -> Dict:
        """Extract component name and line number"""
        result = {"component_name": component, "line_number": None}
        
        # Extract line number if present
        line_match = re.search(r':(\d+)\]', component)
        if line_match:
            result["line_number"] = line_match.group(1)
            result["component_name"] = component[:line_match.start()]
        
        return result
    
    def parse(self, message: str) -> Dict:
        """
        Parse a Zookeeper log message and return structured data
        """
        
        # Parse header
        header_match = self.header_pattern.match(message)
        if not header_match:
            header_match = self.header_pattern_alt.match(message)
        if not header_match:
            header_match = self.header_pattern_simple.match(message)
        
        if not header_match:
            return {
                "event_type": "unknown",
                "template_id": None,
                "raw_message": message[:200]
            }
        
        header = header_match.groupdict()
        msg = header.get("message", "")
        level = header.get("level", "INFO")
        component = header.get("component", "Unknown")
        date_str = header.get("date")
        time_str = header.get("time")
        
        timestamp = f"{date_str} {time_str}"
        
        # Parse component details
        comp_details = self._extract_component_details(component)
        
        result = {
            "timestamp": timestamp,
            "level": level,
            "component": comp_details["component_name"],
            "line_number": comp_details["line_number"],
            "message": msg,
        }
        
        # ===== QUORUM PEER EVENTS =====
        
        # Notification time out
        if "Notification time out:" in msg:
            match = self.notification_timeout.search(msg)
            if match:
                result["event_type"] = "quorum_notification_timeout"
                result["template_id"] = "E31"
                result["timeout"] = match.group("timeout")
                return result
        
        # New election
        if "New election" in msg:
            match = self.new_election.search(msg)
            if match:
                result["event_type"] = "quorum_new_election"
                result["template_id"] = "E30"
                result["my_id"] = match.group("my_id")
                result["zxid"] = match.group("zxid")
                return result
        
        # FOLLOWING
        if "FOLLOWING" in msg and "LEADER ELECTION TOOK" not in msg:
            match = self.following.search(msg)
            if match:
                result["event_type"] = "quorum_following"
                result["template_id"] = "E18"
                if match.group("duration"):
                    result["duration"] = match.group("duration")
                return result
        
        # FOLLOWING with election took
        if "FOLLOWING - LEADER ELECTION TOOK" in msg:
            match = self.leader_election_took.search(msg)
            if match:
                result["event_type"] = "quorum_following_election"
                result["template_id"] = "E19"
                result["duration"] = match.group("duration")
                return result
        
        # LOOKING
        if "LOOKING" in msg and "Notification" not in msg:
            match = self.looking.search(msg)
            if match:
                result["event_type"] = "quorum_looking"
                result["template_id"] = "E26"
                return result
        
        # Getting a snapshot from leader
        if "Getting a snapshot from leader" in msg:
            result["event_type"] = "quorum_getting_snapshot"
            result["template_id"] = "E20"
            return result
        
        # Sending DIFF
        if "Sending DIFF" in msg:
            result["event_type"] = "quorum_sending_diff"
            result["template_id"] = "E43"
            return result
        
        # Snapshotting
        if "Snapshotting:" in msg:
            match = self.snapshotting.search(msg)
            if match:
                result["event_type"] = "quorum_snapshotting"
                result["template_id"] = "E46"
                result["zxid"] = match.group("zxid")
                result["snapshot_path"] = match.group("path")
                return result
        
        # Reading snapshot
        if "Reading snapshot" in msg:
            match = self.reading_snapshot.search(msg)
            if match:
                result["event_type"] = "quorum_reading_snapshot"
                result["template_id"] = "E39"
                result["snapshot_path"] = match.group("path")
                return result
        
        # Have quorum of supporters
        if "Have quorum of supporters" in msg:
            match = self.have_quorum.search(msg)
            if match:
                result["event_type"] = "quorum_have_supporters"
                result["template_id"] = "E22"
                result["zxid"] = match.group("zxid")
                return result
        
        # First is
        if "First is" in msg:
            match = self.first_is.search(msg)
            if match:
                result["event_type"] = "quorum_first_is"
                result["template_id"] = "E16"
                result["value"] = match.group("value")
                return result
        
        # ===== QUORUM CONNECTION MANAGER EVENTS =====
        
        # Received connection request
        if "Received connection request" in msg:
            match = self.received_connection.search(msg)
            if match:
                result["event_type"] = "quorum_received_connection"
                result["template_id"] = "E40"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Cannot open channel
        if "Cannot open channel" in msg:
            match = self.cannot_open_channel.search(msg)
            if match:
                result["event_type"] = "quorum_cannot_open_channel"
                result["template_id"] = "E5"
                result["peer_id"] = match.group("peer_id")
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Have smaller server identifier
        if "Have smaller server identifier" in msg:
            match = self.smaller_server_id.search(msg)
            if match:
                result["event_type"] = "quorum_smaller_server_id"
                result["template_id"] = "E23"
                result["peer1"] = match.group("peer1")
                result["peer2"] = match.group("peer2")
                return result
        
        # My election bind port
        if "My election bind port" in msg:
            match = self.election_bind_port.search(msg)
            if match:
                result["event_type"] = "quorum_election_bind_port"
                result["template_id"] = "E29"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Send worker leaving thread
        if "Send worker leaving thread" in msg:
            result["event_type"] = "quorum_send_worker_leaving"
            result["template_id"] = "E42"
            return result
        
        # Interrupted while waiting for message on queue
        if "Interrupted while waiting for message on queue" in msg:
            result["event_type"] = "quorum_interrupted_waiting"
            result["template_id"] = "E24"
            return result
        
        # Interrupting SendWorker
        if "Interrupting SendWorker" in msg:
            result["event_type"] = "quorum_interrupting_send_worker"
            result["template_id"] = "E25"
            return result
        
        # Connection broken
        if "Connection broken for id" in msg:
            match = self.connection_broken.search(msg)
            if match:
                result["event_type"] = "quorum_connection_broken"
                result["template_id"] = "E11"
                result["peer_id"] = match.group("peer_id")
                result["my_id"] = match.group("my_id")
                return result
        
        # ===== LEADER/FOLLOWER/LEARNER EVENTS =====
        
        # GOODBYE
        if "GOODBYE" in msg:
            match = self.goodbye.search(msg)
            if match:
                result["event_type"] = "learner_goodbye"
                result["template_id"] = "E1"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Unexpected exception causing shutdown
        if "Unexpected exception causing shutdown" in msg:
            result["event_type"] = "learner_unexpected_exception"
            result["template_id"] = "E49"
            return result
        
        # Follower sid
        if "Follower sid:" in msg:
            match = self.follower_sid.search(msg)
            if match:
                result["event_type"] = "learner_follower_sid"
                result["template_id"] = "E17"
                result["sid"] = match.group("sid")
                result["address"] = match.group("address")
                return result
        
        # ===== NIOSERVER CONNECTION EVENTS =====
        
        # Accepted socket connection
        if "Accepted socket connection" in msg:
            match = self.accepted_connection.search(msg)
            if match:
                result["event_type"] = "nioserver_accepted_connection"
                result["template_id"] = "E2"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Closed socket connection with session
        if "Closed socket connection for client" in msg and "which had sessionid" in msg:
            match = self.closed_connection_with_session.search(msg)
            if match:
                result["event_type"] = "nioserver_closed_connection_session"
                result["template_id"] = "E10"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                result["session"] = match.group("session")
                return result
        
        # Closed socket connection no session
        if "Closed socket connection for client" in msg and "no session established" in msg:
            match = self.closed_connection_no_session.search(msg)
            if match:
                result["event_type"] = "nioserver_closed_connection_no_session"
                result["template_id"] = "E9"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # caught end of stream exception
        if "caught end of stream exception" in msg:
            result["event_type"] = "nioserver_end_of_stream"
            result["template_id"] = "E6"
            return result
        
        # Exception causing close of session
        if "Exception causing close of session" in msg:
            match = self.exception_close_session.search(msg)
            if match:
                result["event_type"] = "nioserver_exception_close"
                result["template_id"] = "E14"
                result["session"] = match.group("session")
                return result
        
        # ===== ZOOKEEPER SERVER EVENTS =====
        
        # Client attempting to establish new session
        if "Client attempting to establish new session" in msg:
            match = self.client_new_session.search(msg)
            if match:
                result["event_type"] = "zkserver_new_session_attempt"
                result["template_id"] = "E7"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Client attempting to renew session
        if "Client attempting to renew session" in msg:
            match = self.client_renew_session.search(msg)
            if match:
                result["event_type"] = "zkserver_renew_session_attempt"
                result["template_id"] = "E8"
                result["session"] = match.group("session")
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Established session
        if "Established session" in msg:
            match = self.established_session.search(msg)
            if match:
                result["event_type"] = "zkserver_established_session"
                result["template_id"] = "E13"
                result["session"] = match.group("session")
                result["timeout"] = match.group("timeout")
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # Expiring session
        if "Expiring session" in msg:
            match = self.expiring_session.search(msg)
            if match:
                result["event_type"] = "zkserver_expiring_session"
                result["template_id"] = "E15"
                result["session"] = match.group("session")
                result["timeout"] = match.group("timeout")
                return result
        
        # Processed session termination
        if "Processed session termination" in msg:
            match = self.session_termination.search(msg)
            if match:
                result["event_type"] = "zkserver_session_termination"
                result["template_id"] = "E38"
                result["session"] = match.group("session")
                return result
        
        # Revalidating client
        if "Revalidating client:" in msg:
            match = self.revalidating_client.search(msg)
            if match:
                result["event_type"] = "zkserver_revalidating_client"
                result["template_id"] = "E41"
                result["session"] = match.group("session")
                return result
        
        # Connection request from old client
        if "Connection request from old client" in msg:
            match = self.old_client_connection.search(msg)
            if match:
                result["event_type"] = "zkserver_old_client_connection"
                result["template_id"] = "E12"
                result["ip"] = match.group("ip")
                result["port"] = match.group("port")
                return result
        
        # ===== FAST LEADER ELECTION EVENTS =====
        
        # Notification
        if "Notification:" in msg:
            match = self.notification.search(msg)
            if match:
                result["event_type"] = "fle_notification"
                result["leader"] = match.group("leader")
                result["zxid"] = match.group("zxid")
                result["round"] = match.group("round")
                result["n_state"] = match.group("state")
                result["sid"] = match.group("sid")
                result["epoch"] = match.group("epoch")
                result["my_state"] = match.group("my_state")
                
                # Determine template ID based on states
                if match.group("state") == "LEADING" and match.group("my_state") == "LOOKING":
                    result["template_id"] = "E34"
                elif match.group("state") == "LOOKING" and match.group("my_state") == "LEADING":
                    result["template_id"] = "E36"
                elif match.group("state") == "LOOKING" and match.group("my_state") == "LOOKING":
                    result["template_id"] = "E37"
                elif match.group("state") == "LOOKING" and match.group("my_state") == "FOLLOWING":
                    result["template_id"] = "E35"
                elif match.group("state") == "FOLLOWING" and match.group("my_state") == "LEADING":
                    result["template_id"] = "E33"
                elif match.group("state") == "FOLLOWING" and match.group("my_state") == "FOLLOWING":
                    result["template_id"] = "E32"
                else:
                    result["template_id"] = "E32"
                return result
        
        # ===== ENVIRONMENT EVENTS =====
        
        if "Server environment:" in msg:
            match = self.server_environment.search(msg)
            if match:
                result["event_type"] = "environment_info"
                result["template_id"] = "E44"
                result["env_key"] = match.group("env_key").strip()
                result["env_value"] = match.group("env_value").strip()
                return result
        
        # ===== TIMEOUT/SETTING EVENTS =====
        
        if "tickTime set to" in msg:
            match = self.tick_time.search(msg)
            if match:
                result["event_type"] = "config_tick_time"
                result["template_id"] = "E48"
                result["tick_time"] = match.group("tick_time")
                return result
        
        if "minSessionTimeout set to" in msg:
            match = self.min_session_timeout.search(msg)
            if match:
                result["event_type"] = "config_min_session_timeout"
                result["template_id"] = "E28"
                result["timeout"] = match.group("timeout")
                return result
        
        if "maxSessionTimeout set to" in msg:
            match = self.max_session_timeout.search(msg)
            if match:
                result["event_type"] = "config_max_session_timeout"
                result["template_id"] = "E27"
                result["timeout"] = match.group("timeout")
                return result
        
        # ===== AUTO PURGE EVENTS =====
        
        if "autopurge.snapRetainCount set to" in msg:
            match = self.autopurge_snap.search(msg)
            if match:
                result["event_type"] = "config_autopurge_snap"
                result["template_id"] = "E4"
                result["snap_retain_count"] = match.group("count")
                return result
        
        if "autopurge.purgeInterval set to" in msg:
            match = self.autopurge_interval.search(msg)
            if match:
                result["event_type"] = "config_autopurge_interval"
                result["template_id"] = "E3"
                result["purge_interval"] = match.group("interval")
                return result
        
        # ===== KEEPER EXCEPTION EVENTS =====
        
        if "Got user-level KeeperException" in msg:
            match = self.keeper_exception.search(msg)
            if match:
                result["event_type"] = "keeper_exception"
                result["template_id"] = "E21"
                result["session"] = match.group("session")
                result["error_path"] = match.group("error_path")
                result["node_path"] = match.group("node_path")
                return result
        
        # ===== SHUTDOWN EVENTS =====
        
        if "shutdown of request processor complete" in msg:
            result["event_type"] = "shutdown_complete"
            result["template_id"] = "E45"
            return result
        
        if "Starting quorum peer" in msg:
            result["event_type"] = "starting_quorum_peer"
            result["template_id"] = "E47"
            return result
        
        # ===== DEFAULT =====
        result["event_type"] = "other"
        result["template_id"] = None
        
        # Try to extract session ID if present
        session_match = self.session_pattern.search(msg)
        if session_match:
            result["session"] = session_match.group("session")
        
        # Try to extract IP if present
        ip_match = self.ip_pattern.search(msg)
        if ip_match:
            result["ip"] = ip_match.group("ip")
        
        return result
