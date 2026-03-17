#!/usr/bin/env python3
"""
Master Generator Script
Run individual servers or all at once
"""

import argparse
import subprocess
import os
import sys

def run_server(server_name):
    """Run a single server generator"""
    server_script = f"servers/{server_name}_server.py"
    
    if not os.path.exists(server_script):
        print(f"❌ Server script not found: {server_script}")
        return False
    
    print(f"\n🚀 Starting {server_name} server...")
    result = subprocess.run([sys.executable, server_script])
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description='Generate realistic server logs')
    parser.add_argument('--server', choices=['healthcare', 'db', 'api', 'auth', 'infra', 'all'],
                       default='healthcare', help='Server to generate logs for')
    
    args = parser.parse_args()
    
    if args.server == 'all':
        servers = ['healthcare', 'db', 'api', 'auth', 'infra']
        for server in servers:
            print(f"\n{'='*60}")
            run_server(server)
            print(f"{'='*60}")
    else:
        run_server(args.server)
    
    print(f"\n✅ Generation complete!")

if __name__ == "__main__":
    main()

