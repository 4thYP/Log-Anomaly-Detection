# #!/usr/bin/env python3
# """
# Zookeeper Server
# Generates realistic Zookeeper distributed coordination service logs
# """
#
# import sys
# import os
# import random
# import time
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#
# from core.base_server import BaseServer
#
# class ZookeeperServer(BaseServer):
#     def __init__(self):
#         super().__init__(
#             server_type="zookeeper",
#             log_file="zookeeper_server.log",
#             patterns_file="zookeeper_patterns.json"
#         )
#
#         # Zookeeper-specific state
#         self.state.update({
#             'myid': 1,
#             'zxid': 0x100000000,
#             'session_id': 0x14ed93111f20000,
#             'epoch': 1,
#             'connection_counter': 10000,
#             'leader': True,
#             'peers': [1, 2, 3]
#         })
#
#         # Event probabilities based on Zookeeper logs
#         self.event_probabilities = {
#             'quorum_event': 0.25,      # QuorumPeer events (election, leader/follower)
#             'connection_event': 0.30,    # Connection events (accepted, closed)
#             'session_event': 0.20,       # Session events (established, expired)
#             'worker_event': 0.15,        # Worker/SendWorker/RecvWorker events
#             'notification': 0.10          # FastLeaderElection notifications
#         }
#
#         print(f"   🦓 Zookeeper server initialized with {len(self.patterns.get('templates', {}).get('by_frequency', {}))} patterns")
#
#     def generate_timestamp(self):
#         """Generate Zookeeper-style timestamp (2015-07-29 17:41:44,747)"""
#         year = random.randint(2015, 2024)
#         month = random.randint(1, 12)
#         day = random.randint(1, 28)
#         hour = random.randint(0, 23)
#         minute = random.randint(0, 59)
#         second = random.randint(0, 59)
#         millis = random.randint(0, 999)
#         return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d},{millis:03d}"
#
#     def generate_log_line(self):
#         """Generate Zookeeper-specific log with inner story"""
#         rand = random.random()
#         
#         if rand < self.event_probabilities['quorum_event']:
#             return self.generate_quorum_event()
#         elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event']:
#             return self.generate_connection_event()
#         elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event'] + self.event_probabilities['session_event']:
#             return self.generate_session_event()
#         elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event'] + self.event_probabilities['session_event'] + self.event_probabilities['worker_event']:
#             return self.generate_worker_event()
#         else:
#             return self.generate_notification_event()
#
#     def generate_quorum_event(self):
#         """Generate QuorumPeer events (leader/follower/election)"""
#         event_type = random.choice(['looking', 'leading', 'following', 'election'])
#         
#         if event_type == 'looking':
#             self.state['epoch'] += 1
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'QuorumPeer',
#                 'level': random.choice(['INFO', 'WARN']),
#                 'message': f"LOOKING"
#             }
#         elif event_type == 'leading':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'QuorumPeer',
#                 'level': 'INFO',
#                 'message': f"LEADING"
#             }
#         elif event_type == 'following':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'QuorumPeer',
#                 'level': 'INFO',
#                 'message': f"FOLLOWING - LEADER ELECTION TOOK - {random.randint(10, 500)}"
#             }
#         else:  # election
#             self.state['zxid'] += random.randint(1, 100)
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'FastLeaderElection',
#                 'level': 'INFO',
#                 'message': f"New election. My id = {self.state['myid']}, proposed zxid=0x{self.state['zxid']:x}"
#             }
#
#     def generate_connection_event(self):
#         """Generate connection events (accepted, closed, broken)"""
#         self.state['connection_counter'] += 1
#         peer = random.choice(self.state['peers'])
#         ip = f"10.10.34.{random.randint(11, 50)}"
#         port = random.randint(32000, 60000)
#         
#         event_type = random.choice(['accepted', 'closed', 'broken', 'received'])
#         
#         if event_type == 'accepted':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'NIOServerCxn.Factory',
#                 'level': 'INFO',
#                 'message': f"Accepted socket connection from /{ip}:{port}"
#             }
#         elif event_type == 'closed':
#             session = f"0x{self.state['session_id']:x}"
#             self.state['session_id'] += random.randint(1, 10)
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'NIOServerCxn.Factory',
#                 'level': 'INFO',
#                 'message': f"Closed socket connection for client /{ip}:{port} which had sessionid {session}"
#             }
#         elif event_type == 'broken':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'NIOServerCxn.Factory',
#                 'level': 'WARN',
#                 'message': f"caught end of stream exception"
#             }
#         else:  # received
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': f"/10.10.34.{peer}:3888",
#                 'level': 'INFO',
#                 'message': f"Received connection request /10.10.34.{peer}:{port}"
#             }
#
#     def generate_session_event(self):
#         """Generate session events (established, expired, terminated)"""
#         session = f"0x{self.state['session_id']:x}"
#         self.state['session_id'] += random.randint(1, 5)
#         timeout = random.choice([10000, 20000])
#         ip = f"10.10.34.{random.randint(11, 50)}"
#         port = random.randint(32000, 60000)
#         
#         event_type = random.choice(['established', 'expiring', 'terminated', 'renew'])
#         
#         if event_type == 'established':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CommitProcessor',
#                 'level': 'INFO',
#                 'message': f"Established session {session} with negotiated timeout {timeout} for client /{ip}:{port}"
#             }
#         elif event_type == 'expiring':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'SessionTracker',
#                 'level': 'INFO',
#                 'message': f"Expiring session {session}, timeout of {timeout}ms exceeded"
#             }
#         elif event_type == 'terminated':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'ProcessThread',
#                 'level': 'INFO',
#                 'message': f"Processed session termination for sessionid: {session}"
#             }
#         else:  # renew
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'NIOServerCxn.Factory',
#                 'level': 'INFO',
#                 'message': f"Client attempting to renew session {session} at /{ip}:{port}"
#             }
#
#     def generate_worker_event(self):
#         """Generate SendWorker/RecvWorker events"""
#         peer = random.choice(self.state['peers'])
#         event_type = random.choice(['send_leave', 'recv_interrupt', 'send_interrupt', 'connection_broken'])
#         
#         if event_type == 'send_leave':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': f'SendWorker:{peer}',
#                 'level': 'WARN',
#                 'message': f"Send worker leaving thread"
#             }
#         elif event_type == 'recv_interrupt':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': f'RecvWorker:{peer}',
#                 'level': 'WARN',
#                 'message': f"Interrupting SendWorker"
#             }
#         elif event_type == 'send_interrupt':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': f'SendWorker:{peer}',
#                 'level': 'WARN',
#                 'message': f"Interrupted while waiting for message on queue"
#             }
#         else:  # connection_broken
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': f'RecvWorker:{peer}',
#                 'level': 'WARN',
#                 'message': f"Connection broken for id {peer}, my id = {self.state['myid']}, error = "
#             }
#
#     def generate_notification_event(self):
#         """Generate FastLeaderElection notifications"""
#         self.state['zxid'] += random.randint(1, 50)
#         leader = random.choice(self.state['peers'])
#         state = random.choice(['LOOKING', 'FOLLOWING', 'LEADING'])
#         
#         return {
#             'timestamp': self.generate_timestamp(),
#             'component': 'WorkerReceiver',
#             'level': 'INFO',
#             'message': f"Notification: {leader} (n.leader), 0x{self.state['zxid']:x} (n.zxid), 0x{self.state['epoch']:x} (n.round), {state} (n.state), {leader} (n.sid), 0x{self.state['epoch']:x} (n.peerEPoch), {state} (my state)"
#         }
#
# if __name__ == "__main__":
#     server = ZookeeperServer()
#     server.max_logs = 20
#     print("\n" + "="*50)
#     print("🦓 ZOOKEEPER SERVER TEST")
#     print("="*50)
#     server.run()
#     
#     print("\n📄 First 5 generated logs:")
#     print("-"*50)
#     try:
#         with open(server.log_file, 'r') as f:
#             lines = f.readlines()
#             for i, line in enumerate(lines[:5]):
#                 print(f"{i+1}: {line.strip()}")
#     except Exception as e:
#         print(f"Could not read log file: {e}")




#!/usr/bin/env python3
"""
Zookeeper Server
Generates realistic Zookeeper distributed coordination service logs
"""

import sys
import os
import random
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_server import BaseServer

class ZookeeperServer(BaseServer):
    def __init__(self):
        super().__init__(
            server_type="zookeeper",
            log_file="zookeeper_server.log",
            patterns_file="zookeeper_patterns.json"
        )

        # Zookeeper-specific state
        self.state.update({
            'myid': random.randint(1, 3),
            'zxid': 0x100000000,
            'session_id': 0x14ed93111f20000,
            'epoch': 1,
            'connection_counter': 10000,
            'leader': random.choice([True, False]),
            'peers': [1, 2, 3]
        })

        # Event probabilities based on Zookeeper logs
        self.event_probabilities = {
            'quorum_event': 0.25,
            'connection_event': 0.30,
            'session_event': 0.20,
            'worker_event': 0.15,
            'notification': 0.10
        }

        print(f"   🦓 Zookeeper server initialized with myid={self.state['myid']}")

    def generate_timestamp(self):
        """Generate Zookeeper-style timestamp (2015-07-29 17:41:44,747)"""
        year = random.randint(2015, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        millis = random.randint(0, 999)
        ts = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d},{millis:03d}"
        
        # Ensure monotonic (base class handles this)
        return ts

    def generate_log_line(self):
        """Generate Zookeeper-specific log with inner story"""
        # Generate timestamp once for this log (ensures it's never "unknown")
        current_timestamp = self.generate_timestamp()
        
        rand = random.random()
        
        if rand < self.event_probabilities['quorum_event']:
            return self.generate_quorum_event(current_timestamp)
        elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event']:
            return self.generate_connection_event(current_timestamp)
        elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event'] + self.event_probabilities['session_event']:
            return self.generate_session_event(current_timestamp)
        elif rand < self.event_probabilities['quorum_event'] + self.event_probabilities['connection_event'] + self.event_probabilities['session_event'] + self.event_probabilities['worker_event']:
            return self.generate_worker_event(current_timestamp)
        else:
            return self.generate_notification_event(current_timestamp)

    def generate_quorum_event(self, timestamp):
        """Generate QuorumPeer events (leader/follower/election)"""
        event_type = random.choice(['looking', 'leading', 'following', 'election'])
        
        if event_type == 'looking':
            self.state['epoch'] += 1
            return {
                'timestamp': timestamp,
                'component': 'QuorumPeer',
                'level': 'INFO',
                'message': f"LOOKING"
            }
        elif event_type == 'leading':
            return {
                'timestamp': timestamp,
                'component': 'QuorumPeer',
                'level': 'INFO',
                'message': f"LEADING"
            }
        elif event_type == 'following':
            return {
                'timestamp': timestamp,
                'component': 'QuorumPeer',
                'level': 'INFO',
                'message': f"FOLLOWING - LEADER ELECTION TOOK - {random.randint(10, 500)}"
            }
        else:  # election
            self.state['zxid'] += random.randint(1, 100)
            return {
                'timestamp': timestamp,
                'component': 'FastLeaderElection',
                'level': 'INFO',
                'message': f"New election. My id = {self.state['myid']}, proposed zxid=0x{self.state['zxid']:x}"
            }

    def generate_connection_event(self, timestamp):
        """Generate connection events (accepted, closed, broken)"""
        self.state['connection_counter'] += 1
        peer = random.choice(self.state['peers'])
        ip = f"10.10.34.{random.randint(11, 50)}"
        port = random.randint(32000, 60000)
        
        event_type = random.choice(['accepted', 'closed', 'broken', 'received'])
        
        if event_type == 'accepted':
            return {
                'timestamp': timestamp,
                'component': 'NIOServerCxn.Factory',
                'level': 'INFO',
                'message': f"Accepted socket connection from /{ip}:{port}"
            }
        elif event_type == 'closed':
            session = f"0x{self.state['session_id']:x}"
            self.state['session_id'] += random.randint(1, 10)
            return {
                'timestamp': timestamp,
                'component': 'NIOServerCxn.Factory',
                'level': 'INFO',
                'message': f"Closed socket connection for client /{ip}:{port} which had sessionid {session}"
            }
        elif event_type == 'broken':
            return {
                'timestamp': timestamp,
                'component': 'NIOServerCxn.Factory',
                'level': 'WARN',
                'message': f"caught end of stream exception"
            }
        else:  # received
            return {
                'timestamp': timestamp,
                'component': f"/10.10.34.{peer}:3888",
                'level': 'INFO',
                'message': f"Received connection request /10.10.34.{peer}:{port}"
            }

    def generate_session_event(self, timestamp):
        """Generate session events (established, expired, terminated)"""
        session = f"0x{self.state['session_id']:x}"
        self.state['session_id'] += random.randint(1, 5)
        timeout = random.choice([10000, 20000])
        ip = f"10.10.34.{random.randint(11, 50)}"
        port = random.randint(32000, 60000)
        
        event_type = random.choice(['established', 'expiring', 'terminated', 'renew'])
        
        if event_type == 'established':
            return {
                'timestamp': timestamp,
                'component': 'CommitProcessor',
                'level': 'INFO',
                'message': f"Established session {session} with negotiated timeout {timeout} for client /{ip}:{port}"
            }
        elif event_type == 'expiring':
            return {
                'timestamp': timestamp,
                'component': 'SessionTracker',
                'level': 'INFO',
                'message': f"Expiring session {session}, timeout of {timeout}ms exceeded"
            }
        elif event_type == 'terminated':
            return {
                'timestamp': timestamp,
                'component': 'ProcessThread',
                'level': 'INFO',
                'message': f"Processed session termination for sessionid: {session}"
            }
        else:  # renew
            return {
                'timestamp': timestamp,
                'component': 'NIOServerCxn.Factory',
                'level': 'INFO',
                'message': f"Client attempting to renew session {session} at /{ip}:{port}"
            }

    def generate_worker_event(self, timestamp):
        """Generate SendWorker/RecvWorker events"""
        peer = random.choice(self.state['peers'])
        event_type = random.choice(['send_leave', 'recv_interrupt', 'send_interrupt', 'connection_broken'])
        
        if event_type == 'send_leave':
            return {
                'timestamp': timestamp,
                'component': f'SendWorker:{peer}',
                'level': 'WARN',
                'message': f"Send worker leaving thread"
            }
        elif event_type == 'recv_interrupt':
            return {
                'timestamp': timestamp,
                'component': f'RecvWorker:{peer}',
                'level': 'WARN',
                'message': f"Interrupting SendWorker"
            }
        elif event_type == 'send_interrupt':
            return {
                'timestamp': timestamp,
                'component': f'SendWorker:{peer}',
                'level': 'WARN',
                'message': f"Interrupted while waiting for message on queue"
            }
        else:  # connection_broken
            return {
                'timestamp': timestamp,
                'component': f'RecvWorker:{peer}',
                'level': 'WARN',
                'message': f"Connection broken for id {peer}, my id = {self.state['myid']}, error = "
            }

    def generate_notification_event(self, timestamp):
        """Generate FastLeaderElection notifications"""
        self.state['zxid'] += random.randint(1, 50)
        leader = random.choice(self.state['peers'])
        state = random.choice(['LOOKING', 'FOLLOWING', 'LEADING'])
        
        return {
            'timestamp': timestamp,
            'component': 'WorkerReceiver',
            'level': 'INFO',
            'message': f"Notification: {leader} (n.leader), 0x{self.state['zxid']:x} (n.zxid), 0x{self.state['epoch']:x} (n.round), {state} (n.state), {leader} (n.sid), 0x{self.state['epoch']:x} (n.peerEPoch), {state} (my state)"
        }

if __name__ == "__main__":
    server = ZookeeperServer()
    server.max_logs = 20
    print("\n" + "="*50)
    print("🦓 ZOOKEEPER SERVER TEST")
    print("="*50)
    server.run()
    
    print("\n📄 First 5 generated logs:")
    print("-"*50)
    try:
        with open(server.log_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"{i+1}: {line.strip()}")
    except Exception as e:
        print(f"Could not read log file: {e}")
