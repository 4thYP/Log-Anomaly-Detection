#!/usr/bin/env python3
"""
SID Generator - Creates unique Server IDs
Format: <random_string>_<SERVER_TYPE>_<instance_number>
"""

import uuid
import hashlib
import base64
import os
import json
from datetime import datetime

class SIDGenerator:
    def __init__(self, sid_file="server_sids.json"):
        self.sid_file = sid_file
        self.sid_registry = self.load_registry()
    
    def load_registry(self):
        """Load existing SID registry - handles empty file gracefully"""
        if os.path.exists(self.sid_file):
            try:
                # Check if file is empty
                if os.path.getsize(self.sid_file) == 0:
                    print("⚠️  SID registry file is empty, creating new registry")
                    return {}
                
                with open(self.sid_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # File exists but contains invalid JSON
                print("⚠️  SID registry file is corrupted, creating new registry")
                return {}
            except Exception as e:
                print(f"⚠️  Error loading SID registry: {e}")
                return {}
        return {}
    
    def save_registry(self):
        """Save SID registry"""
        try:
            with open(self.sid_file, 'w') as f:
                json.dump(self.sid_registry, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving SID registry: {e}")
    
    def generate_random_string(self):
        """Generate a unique random string"""
        # Use UUID4 + timestamp for uniqueness
        unique_str = str(uuid.uuid4()) + str(datetime.now().timestamp())
        hashed = hashlib.sha256(unique_str.encode()).digest()
        # Convert to base64 and take first 30 chars
        random_str = base64.b64encode(hashed).decode('utf-8')[:30]
        # Replace non-alphanumeric chars
        random_str = ''.join(c for c in random_str if c.isalnum())
        return random_str
    
    def get_next_instance_number(self, server_type):
        """Get next instance number for server type"""
        key = f"{server_type}_counter"
        if key not in self.sid_registry:
            self.sid_registry[key] = 1
        else:
            self.sid_registry[key] += 1
        return self.sid_registry[key]
    
    def generate_sid(self, server_type):
        """Generate a complete SID"""
        random_part = self.generate_random_string()
        instance_num = self.get_next_instance_number(server_type)
        sid = f"{random_part}_{server_type.upper()}_{instance_num}"
        
        # Store the mapping
        self.sid_registry[sid] = {
            "server_type": server_type,
            "instance": instance_num,
            "created": str(datetime.now())
        }
        
        self.save_registry()
        return sid
    
    def get_sid_for_server(self, server_type, instance_num=None):
        """Get existing SID or create new one"""
        if instance_num:
            # Look for existing SID with this instance number
            for sid, info in self.sid_registry.items():
                if isinstance(info, dict) and info.get("server_type") == server_type and info.get("instance") == instance_num:
                    return sid
        return self.generate_sid(server_type)

# Singleton instance
_generator = None

def get_sid_generator():
    global _generator
    if _generator is None:
        _generator = SIDGenerator()
    return _generator

def generate_sid(server_type):
    """Public function to generate SID"""
    return get_sid_generator().generate_sid(server_type)

def get_sid(server_type, instance_num=None):
    """Public function to get or create SID"""
    return get_sid_generator().get_sid_for_server(server_type, instance_num)

# For testing
if __name__ == "__main__":
    # Test the generator
    for server in ['HEALTHCARE', 'LINUX', 'WINDOWS', 'ZOOKEEPER', 'HPC']:
        sid = generate_sid(server)
        print(f"{server}: {sid}")
