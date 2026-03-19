# #!/usr/bin/env python3
# """
# Base Server Class
# All servers inherit from this to get pattern-based generation
# """
#
# import json
# import random
# import time
# from datetime import datetime
# import os
# import sys
# import threading
#
# # Add path to import sid_generator
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# from sid_generator import generate_sid
#
# class BaseServer:
#     def __init__(self, server_type, log_file, patterns_file):
#         print(f"🔍 DEBUG - Initializing {server_type} server")
#         print(f"🔍 DEBUG - Current working directory: {os.getcwd()}")
#         
#         self.server_type = server_type
#         # Always put logs in logs/ directory
#         self.log_file = os.path.join("logs", log_file)
#         self.patterns_file = patterns_file
#         
#         # Generate unique SID for this server instance with retry logic
#         print(f"🔍 DEBUG - About to generate SID for {server_type}")
#         self.sid = self.generate_sid_with_retry(server_type)
#         print(f"🔑 Server SID: {self.sid}")
#         
#         self.patterns = self.load_patterns()
#         self.state = {}  # Internal state variables
#         self.log_count = 0
#         self.max_logs = 20  # Generate 20 logs by default
#         self.lock = threading.Lock()  # Add lock for thread safety
#         
#         # Ensure the directory for the log file exists
#         log_dir = os.path.dirname(self.log_file)
#         if log_dir and not os.path.exists(log_dir):
#             os.makedirs(log_dir, exist_ok=True)
#         
#         # Write SID as first line in log file
#         self.write_sid_to_log()
#         
#         print(f"✅ {server_type} server initialized")
#         print(f"📁 Log file: {self.log_file}")
#     
#     def write_sid_to_log(self):
#         """Write the SID as the first line of the log file"""
#         try:
#             # Create file with SID as first line
#             with open(self.log_file, 'w') as f:
#                 f.write(f"# SID: {self.sid}\n")
#                 f.flush()
#             print(f"📝 SID written to {self.log_file}")
#         except Exception as e:
#             print(f"⚠️  Could not write SID to log: {e}")
#     
#     def generate_sid_with_retry(self, server_type, max_retries=3):
#         """Generate SID with retry logic to handle concurrent access"""
#         for attempt in range(max_retries):
#             try:
#                 return generate_sid(server_type)
#             except Exception as e:
#                 print(f"⚠️  SID generation attempt {attempt + 1} failed: {e}")
#                 if attempt < max_retries - 1:
#                     time.sleep(0.5)  # Wait half a second before retrying
#                 else:
#                     # Fallback to timestamp-based SID
#                     fallback_sid = f"FALLBACK_{server_type}_{int(time.time())}_{random.randint(1000,9999)}"
#                     print(f"⚠️  Using fallback SID: {fallback_sid}")
#                     return fallback_sid
#
#     def load_patterns(self):
#         """Load learned patterns from JSON file"""
#         try:
#             # Try multiple possible paths
#             possible_paths = [
#                 self.patterns_file,
#                 f"patterns/{self.patterns_file}",
#                 f"../patterns/{self.patterns_file}",
#                 f"module2_generator/patterns/{self.patterns_file}"
#             ]
#             
#             for path in possible_paths:
#                 if os.path.exists(path):
#                     print(f"   📂 Loaded patterns from: {path}")
#                     with open(path, 'r') as f:
#                         return json.load(f)
#             
#             print(f"⚠️  Patterns file not found. Using fallback patterns.")
#             return self.get_fallback_patterns()
#             
#         except Exception as e:
#             print(f"⚠️  Error loading patterns: {e}")
#             return self.get_fallback_patterns()
#
#     def get_fallback_patterns(self):
#         """Provide basic patterns if file not found"""
#         return {
#             "templates": {
#                 "by_frequency": {
#                     "sample log <*>": 10
#                 }
#             },
#             "components": {
#                 "by_frequency": {
#                     "Component": 10
#                 }
#             }
#         }
#
#     def generate_timestamp(self):
#         """Generate realistic timestamp"""
#         now = datetime.now()
#         return now.strftime("%Y%m%d-%H:%M:%S") + f":{random.randint(100,999)}"
#
#     def get_random_component(self):
#         """Get random component based on learned frequencies"""
#         components = self.patterns.get('components', {}).get('by_frequency', {})
#         if components:
#             return random.choice(list(components.keys()))
#         return f"{self.server_type}_component"
#
#     def get_random_template(self):
#         """Get random log template based on frequencies"""
#         templates = self.patterns.get('templates', {}).get('by_frequency', {})
#         if templates:
#             return random.choice(list(templates.keys()))
#         return f"{self.server_type} log message <*>"
#
#     def fill_template(self, template):
#         """Replace <*> with realistic values"""
#         # Replace each <*> with a random number
#         while '<*>' in template:
#             # Generate number based on context
#             if 'step' in template.lower() or 'count' in template.lower():
#                 # Incrementing counters
#                 value = self.get_next_counter('step', 3000, 4000)
#             elif 'calorie' in template.lower():
#                 # Larger numbers
#                 value = random.randint(100000, 500000)
#             elif 'altitude' in template.lower():
#                 # Constant-like values
#                 value = 240  # From your data
#             else:
#                 # Generic numbers
#                 value = random.randint(1, 9999)
#             
#             template = template.replace('<*>', str(value), 1)
#         
#         return template
#
#     def get_next_counter(self, name, min_val, max_val):
#         """Get next value for a counter (increments realistically)"""
#         key = f"counter_{name}"
#         if key not in self.state:
#             self.state[key] = random.randint(min_val, min_val + 100)
#         else:
#             # Increment by 1-3 steps
#             self.state[key] += random.randint(1, 3)
#             if self.state[key] > max_val:
#                 self.state[key] = min_val
#         return self.state[key]
#
#     def apply_causal_chain(self):
#         """Apply learned causal chains to generate related logs"""
#         chains = self.patterns.get('causal_chains', {}).get('chains', [])
#         if chains and random.random() < 0.3:  # 30% chance to trigger a chain
#             # Pick a random chain and generate its events
#             chain = random.choice(chains[:5])  # Top 5 chains
#             return chain.get('pattern', [])
#         return None
#
#     def generate_log_line(self):
#         """Generate a single log line - to be overridden by child classes"""
#         component = self.get_random_component()
#         template = self.get_random_template()
#         message = self.fill_template(template)
#         
#         return {
#             'timestamp': self.generate_timestamp(),
#             'component': component,
#             'user_id': str(random.randint(10000000, 99999999)),
#             'message': message
#         }
#
#     def write_log(self, log_data):
#         """Write log to file - handles different log formats"""
#         # Skip if log_data has skip flag (for chain events that already wrote themselves)
#         if log_data.get('skip'):
#             return
#         
#         # Different servers have different log formats
#         if self.server_type == 'healthcare':
#             # Healthcare format: timestamp|component|user_id|message
#             log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['user_id']}|{log_data['message']}"
#         elif self.server_type == 'linux':
#             # Linux format: timestamp component process: message
#             process = log_data.get('process', '')
#             if process:
#                 log_line = f"{log_data['timestamp']} {log_data['component']} {process}: {log_data['message']}"
#             else:
#                 log_line = f"{log_data['timestamp']} {log_data['component']}: {log_data['message']}"
#         elif self.server_type == 'windows':
#             # Windows format: timestamp|component|message
#             log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
#         elif self.server_type == 'zookeeper':
#             # Zookeeper format: timestamp|component|message
#             log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
#         elif self.server_type == 'hpc':
#             # HPC format (will be designed later)
#             log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
#         else:
#             # Default format for other servers
#             log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
#         
#         # Ensure logs directory exists
#         os.makedirs("logs", exist_ok=True)
#         
#         with open(self.log_file, 'a') as f:
#             f.write(log_line + "\n")
#             f.flush()
#         
#         self.log_count += 1
#
#     def run(self):
#         """Main generation loop"""
#         print(f"\n🚀 Starting {self.server_type} server...")
#         print(f"📝 Writing logs to: {self.log_file}")
#         print(f"📊 Generating {self.max_logs} logs...\n")
#         
#         logs_generated = 0
#         while logs_generated < self.max_logs:
#             log_data = self.generate_log_line()
#             
#             # Check if this log should be counted
#             if not log_data.get('skip'):
#                 logs_generated += 1
#                 # Only print for non-chain events (chain events print their own messages)
#                 if 'message' in log_data:
#                     # Truncate long messages for display
#                     msg = log_data['message'][:50] + "..." if len(log_data['message']) > 50 else log_data['message']
#                     print(f"   📝 Log {logs_generated}: {msg}")
#             
#             self.write_log(log_data)
#             time.sleep(random.uniform(0.5, 1.5))
#         
#         print(f"\n✅ {self.server_type} server finished. Generated {self.max_logs} logs.\n")





#!/usr/bin/env python3
"""
Base Server Class
All servers inherit from this to get pattern-based generation
"""

import json
import random
import time
from datetime import datetime
import os
import sys
import threading

# Add path to import sid_generator
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sid_generator import generate_sid

class BaseServer:
    def __init__(self, server_type, log_file, patterns_file):
        print(f"🔍 DEBUG - Initializing {server_type} server")
        print(f"🔍 DEBUG - Current working directory: {os.getcwd()}")
        
        self.server_type = server_type
        
        # Get instance number from environment variable (set by run.py)
        self.instance_num = os.environ.get('SERVER_INSTANCE', '1')
        self.sid = os.environ.get('SERVER_SID', None)
        
        # If no SID in environment, generate one (fallback)
        if not self.sid:
            print(f"🔍 DEBUG - About to generate SID for {server_type}")
            self.sid = self.generate_sid_with_retry(server_type)
        
        # Create instance-specific log file: type_instance.log
        # e.g., healthcare_1.log, healthcare_2.log, etc.
        base_name = log_file.replace('_server.log', '')  # Remove '_server' if present
        if base_name == log_file:  # If no '_server' pattern
            base_name = server_type.lower()
        
        self.log_file = os.path.join("logs", f"{base_name}_{self.instance_num}.log")
        
        print(f"🔑 Server SID: {self.sid}")
        print(f"📁 Log file: {self.log_file}")
        
        self.patterns = self.load_patterns()
        self.state = {}  # Internal state variables
        self.log_count = 0
        self.max_logs = 20  # Generate 20 logs by default
        self.lock = threading.Lock()  # Add lock for thread safety
        self.quiet_mode = True  # Suppress detailed output
        
        # Ensure the directory for the log file exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Write SID as first line in log file
        self.write_sid_to_log()
        
        print(f"✅ {server_type} server #{self.instance_num} initialized")
    
    def write_sid_to_log(self):
        """Write the SID as the first line of the log file"""
        try:
            # Create file with SID as first line (overwrites if exists)
            with open(self.log_file, 'w') as f:
                f.write(f"# SID: {self.sid}\n")
                f.flush()
            print(f"📝 SID written to {self.log_file}")
        except Exception as e:
            print(f"⚠️  Could not write SID to log: {e}")
    
    def generate_sid_with_retry(self, server_type, max_retries=3):
        """Generate SID with retry logic to handle concurrent access"""
        for attempt in range(max_retries):
            try:
                return generate_sid(server_type)
            except Exception as e:
                print(f"⚠️  SID generation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Wait half a second before retrying
                else:
                    # Fallback to timestamp-based SID
                    fallback_sid = f"FALLBACK_{server_type}_{int(time.time())}_{random.randint(1000,9999)}"
                    print(f"⚠️  Using fallback SID: {fallback_sid}")
                    return fallback_sid

    def load_patterns(self):
        """Load learned patterns from JSON file"""
        try:
            # Try multiple possible paths
            possible_paths = [
                self.patterns_file,
                f"patterns/{self.patterns_file}",
                f"../patterns/{self.patterns_file}",
                f"module2_generator/patterns/{self.patterns_file}"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"   📂 Loaded patterns from: {path}")
                    with open(path, 'r') as f:
                        return json.load(f)
            
            print(f"⚠️  Patterns file not found. Using fallback patterns.")
            return self.get_fallback_patterns()
            
        except Exception as e:
            print(f"⚠️  Error loading patterns: {e}")
            return self.get_fallback_patterns()

    def get_fallback_patterns(self):
        """Provide basic patterns if file not found"""
        return {
            "templates": {
                "by_frequency": {
                    "sample log <*>": 10
                }
            },
            "components": {
                "by_frequency": {
                    "Component": 10
                }
            }
        }

    def generate_timestamp(self):
        """Generate realistic timestamp"""
        now = datetime.now()
        return now.strftime("%Y%m%d-%H:%M:%S") + f":{random.randint(100,999)}"

    def get_random_component(self):
        """Get random component based on learned frequencies"""
        components = self.patterns.get('components', {}).get('by_frequency', {})
        if components:
            return random.choice(list(components.keys()))
        return f"{self.server_type}_component"

    def get_random_template(self):
        """Get random log template based on frequencies"""
        templates = self.patterns.get('templates', {}).get('by_frequency', {})
        if templates:
            return random.choice(list(templates.keys()))
        return f"{self.server_type} log message <*>"

    def fill_template(self, template):
        """Replace <*> with realistic values"""
        # Replace each <*> with a random number
        while '<*>' in template:
            # Generate number based on context
            if 'step' in template.lower() or 'count' in template.lower():
                # Incrementing counters
                value = self.get_next_counter('step', 3000, 4000)
            elif 'calorie' in template.lower():
                # Larger numbers
                value = random.randint(100000, 500000)
            elif 'altitude' in template.lower():
                # Constant-like values
                value = 240  # From your data
            else:
                # Generic numbers
                value = random.randint(1, 9999)
            
            template = template.replace('<*>', str(value), 1)
        
        return template

    def get_next_counter(self, name, min_val, max_val):
        """Get next value for a counter (increments realistically)"""
        key = f"counter_{name}"
        if key not in self.state:
            self.state[key] = random.randint(min_val, min_val + 100)
        else:
            # Increment by 1-3 steps
            self.state[key] += random.randint(1, 3)
            if self.state[key] > max_val:
                self.state[key] = min_val
        return self.state[key]

    def apply_causal_chain(self):
        """Apply learned causal chains to generate related logs"""
        chains = self.patterns.get('causal_chains', {}).get('chains', [])
        if chains and random.random() < 0.3:  # 30% chance to trigger a chain
            # Pick a random chain and generate its events
            chain = random.choice(chains[:5])  # Top 5 chains
            return chain.get('pattern', [])
        return None

    def generate_log_line(self):
        """Generate a single log line - to be overridden by child classes"""
        component = self.get_random_component()
        template = self.get_random_template()
        message = self.fill_template(template)
        
        return {
            'timestamp': self.generate_timestamp(),
            'component': component,
            'user_id': str(random.randint(10000000, 99999999)),
            'message': message
        }

    def write_log(self, log_data):
        """Write log to file - handles different log formats"""
        # Skip if log_data has skip flag (for chain events that already wrote themselves)
        if log_data.get('skip'):
            return
        
        # Different servers have different log formats
        if self.server_type == 'healthcare':
            # Healthcare format: timestamp|component|user_id|message
            log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['user_id']}|{log_data['message']}"
        elif self.server_type == 'linux':
            # Linux format: timestamp component process: message
            process = log_data.get('process', '')
            if process:
                log_line = f"{log_data['timestamp']} {log_data['component']} {process}: {log_data['message']}"
            else:
                log_line = f"{log_data['timestamp']} {log_data['component']}: {log_data['message']}"
        elif self.server_type == 'windows':
            # Windows format: timestamp|component|message
            log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
        elif self.server_type == 'zookeeper':
            # Zookeeper format: timestamp|component|message
            log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
        elif self.server_type == 'hpc':
            # HPC format (will be designed later)
            log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
        else:
            # Default format for other servers
            log_line = f"{log_data['timestamp']}|{log_data['component']}|{log_data['message']}"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        with open(self.log_file, 'a') as f:
            f.write(log_line + "\n")
            f.flush()
        
        self.log_count += 1

    def run(self):
        """Main generation loop"""
        if not self.quiet_mode:
            print(f"\n🚀 Starting {self.server_type} server #{self.instance_num}...")
            print(f"📝 Writing logs to: {self.log_file}")
            print(f"📊 Generating {self.max_logs} logs...\n")
        
        logs_generated = 0
        while logs_generated < self.max_logs:
            log_data = self.generate_log_line()
            
            # Check if this log should be counted
            if not log_data.get('skip'):
                logs_generated += 1
                # Only print for non-chain events (chain events print their own messages)
                if 'message' in log_data and not self.quiet_mode:
                    # Truncate long messages for display
                    msg = log_data['message'][:50] + "..." if len(log_data['message']) > 50 else log_data['message']
                    print(f"   📝 Log {logs_generated}: {msg}")
            
            self.write_log(log_data)
            time.sleep(random.uniform(0.5, 1.5))
        
        if not self.quiet_mode:
            print(f"\n✅ {self.server_type} server #{self.instance_num} finished. Generated {self.max_logs} logs.\n")
