#!/usr/bin/env python3
"""
Linux Server
Generates realistic Linux system logs with inner stories
"""

import sys
import os
import random
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_server import BaseServer

class LinuxServer(BaseServer):
    def __init__(self):
        # Initialize with linux-specific patterns
        super().__init__(
            server_type="linux",
            log_file="linux_server.log",  # CHANGED: added ../logs/
            patterns_file="linux_patterns.json"
        )

        # Linux-specific state (learned from your logs)
        self.state.update({
            'pid': 1000,
            'sshd_pid': 19900,
            'ftpd_pid': 29000,
            'klogind_pid': 19200,
            'su_pid': 21000,
            'users': ['root', 'test', 'guest', 'cyrus', 'news', 'unknown'],
            'current_user': 'root',
            'auth_attempts': 0,
            'failed_logins': 0,
            'ips': [
                '218.188.2.4',
                '220-135-151-1.hinet-ip.hinet.net',
                '061092085098.ctinets.com',
                'd211-116-254-214.rev.krline.net',
                'adsl-70-242-75-179.dsl.ksc2mo.swbell.net',
                'massive.merukuru.org',
                'zummit.com',
                'c9063558.virtua.com.br'
            ]
        })

        # Event probabilities based on your logs
        self.event_probabilities = {
            'sshd_check_pass': 0.25,      # "check pass; user unknown"
            'sshd_auth_fail': 0.35,        # "authentication failure"
            'sshd_session': 0.10,           # "session opened/closed"
            'ftp_connection': 0.15,          # "connection from"
            'su_session': 0.08,               # "su session"
            'system_event': 0.05,              # cups, syslog, kernel
            'service_event': 0.02               # portmap, nfslock, etc
        }

        print(f"   🐧 Linux server initialized with {len(self.patterns.get('templates', {}).get('by_frequency', {}))} patterns")

    def generate_timestamp(self):
        """Generate Linux-style timestamp (Jun 14 15:16:01)"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month = random.choice(months)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return f"{month} {day:02d} {hour:02d}:{minute:02d}:{second:02d}"

    def generate_log_line(self):
        """Generate Linux-specific log with inner story"""

        rand = random.random()

        if rand < self.event_probabilities['sshd_check_pass']:
            return self.generate_sshd_check_pass()
        elif rand < self.event_probabilities['sshd_check_pass'] + self.event_probabilities['sshd_auth_fail']:
            return self.generate_sshd_auth_fail()
        elif rand < self.event_probabilities['sshd_check_pass'] + self.event_probabilities['sshd_auth_fail'] + self.event_probabilities['sshd_session']:
            return self.generate_sshd_session()
        elif rand < self.event_probabilities['sshd_check_pass'] + self.event_probabilities['sshd_auth_fail'] + self.event_probabilities['sshd_session'] + self.event_probabilities['ftp_connection']:
            return self.generate_ftp_connection()
        elif rand < self.event_probabilities['sshd_check_pass'] + self.event_probabilities['sshd_auth_fail'] + self.event_probabilities['sshd_session'] + self.event_probabilities['ftp_connection'] + self.event_probabilities['su_session']:
            return self.generate_su_session()
        elif rand < self.event_probabilities['sshd_check_pass'] + self.event_probabilities['sshd_auth_fail'] + self.event_probabilities['sshd_session'] + self.event_probabilities['ftp_connection'] + self.event_probabilities['su_session'] + self.event_probabilities['system_event']:
            return self.generate_system_event()
        else:
            return self.generate_service_event()

    def generate_sshd_check_pass(self):
        self.state['pid'] += 1
        self.state['sshd_pid'] += 1

        return {
        'timestamp': self.generate_timestamp(),
        'component': 'combo',
        'process': f'sshd(pam_unix)[{self.state["sshd_pid"]}]',
        'message': 'check pass; user unknown'
        }

    def generate_sshd_auth_fail(self):
        """Generate authentication failure events"""
        self.state['pid'] += 1
        self.state['sshd_pid'] += 1
        self.state['failed_logins'] += 1

        # Different types of auth failures from your logs
        auth_type = random.choice(['generic', 'with_user'])
        ip = random.choice(self.state['ips'])

        if auth_type == 'generic':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'sshd(pam_unix)[{self.state["sshd_pid"]}]',
                'message': f'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost={ip}'
            }
        else:
            user = random.choice(['root', 'guest', 'test'])
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'sshd(pam_unix)[{self.state["sshd_pid"]}]',
                'message': f'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost={ip}  user={user}'
            }

    def generate_sshd_session(self):
        """Generate session opened/closed events"""
        self.state['pid'] += 1
        self.state['sshd_pid'] += 1

        user = random.choice(['test', 'root'])
        uid = '509' if user == 'test' else '0'

        if random.random() < 0.5:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'sshd(pam_unix)[{self.state["sshd_pid"]}]',
                'message': f'session opened for user {user} by (uid={uid})'
            }
        else:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'sshd(pam_unix)[{self.state["sshd_pid"]}]',
                'message': f'session closed for user {user}'
            }

    def generate_ftp_connection(self):
        """Generate FTP connection events"""
        self.state['pid'] += 1
        self.state['ftpd_pid'] += 1

        ip = random.choice(self.state['ips'])

        return {
            'timestamp': self.generate_timestamp(),
            'component': 'combo',
            'process': f'ftpd[{self.state["ftpd_pid"]}]',
            'message': f'connection from {ip} () at some time'
        }

    def generate_su_session(self):
        """Generate su (switch user) events"""
        self.state['pid'] += 1
        self.state['su_pid'] += 1

        users = ['cyrus', 'news', 'root']
        target_user = random.choice(users)

        if random.random() < 0.5:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'su(pam_unix)[{self.state["su_pid"]}]',
                'message': f'session opened for user {target_user} by (uid=0)'
            }
        else:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': f'su(pam_unix)[{self.state["su_pid"]}]',
                'message': f'session closed for user {target_user}'
            }

    def generate_system_event(self):
        """Generate system events (cups, syslog, logrotate, kernel)"""
        self.state['pid'] += 1

        event_type = random.choice(['cups', 'syslog', 'logrotate', 'kernel'])

        if event_type == 'cups':
            if random.random() < 0.5:
                return {
                    'timestamp': self.generate_timestamp(),
                    'component': 'combo',
                    'process': 'cups',
                    'message': 'cupsd shutdown succeeded'
                }
            else:
                return {
                    'timestamp': self.generate_timestamp(),
                    'component': 'combo',
                    'process': 'cups',
                    'message': 'cupsd startup succeeded'
                }
        elif event_type == 'syslog':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': 'syslogd 1.4.1',
                'message': 'restart.'
            }
        elif event_type == 'logrotate':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': 'logrotate',
                'message': 'ALERT exited abnormally with [1]'
            }
        else:  # kernel
            kernel_msgs = [
                'Linux version 2.6.5-1.358',
                'BIOS-provided physical RAM map:',
                'BIOS-e820: 0000000000000000 - 00000000000a0000 (usable)',
                'Detected 731.219 MHz processor.',
                'CPU: Intel Pentium III (Coppermine) stepping 06',
                'Checking \'hlt\' instruction... OK.'
            ]
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'combo',
                'process': 'kernel',
                'message': random.choice(kernel_msgs)
            }

    def generate_service_event(self):
        """Generate service start/stop events"""
        self.state['pid'] += 1

        services = ['portmap', 'nfslock', 'rpcidmapd', 'bluetooth', 'irqbalance', 'random']
        service = random.choice(services)

        return {
            'timestamp': self.generate_timestamp(),
            'component': service,
            'process': '',
            'message': f'{service} startup succeeded'
        }

if __name__ == "__main__":
    server = LinuxServer()
    server.max_logs = 20
    print("\n" + "="*50)
    print("🐧 LINUX SERVER TEST")
    print("="*50)
    server.run()

    # Show the generated logs
    print("\n📄 First 5 generated logs:")
    print("-"*50)
    try:
        with open(server.log_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"{i+1}: {line.strip()}")
    except:
        pass
