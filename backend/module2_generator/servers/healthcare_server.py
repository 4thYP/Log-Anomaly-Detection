#!/usr/bin/env python3
"""
Healthcare Server
Generates realistic healthcare logs with inner stories
"""

import sys
import os
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_server import BaseServer

class HealthcareServer(BaseServer):
    def __init__(self):
        # Initialize with healthcare-specific patterns
        super().__init__(
            server_type="healthcare",
            log_file="healthcare_server.log",
            patterns_file="healthcare_patterns.json"
        )
        
        # Healthcare-specific state (from your real logs)
        self.state.update({
            'step_count': 3579,  # Starting from your logs
            'total_calories': 126775,
            'altitude': 240,
            'patient_id': 30002312,
            'screen_on': True
        })
        
        # Causal chain probabilities
        self.chain_probabilities = {
            'step_update': 0.4,  # 40% chance to trigger step update chain
            'screen_toggle': 0.1,  # 10% chance to toggle screen
            'report': 0.3  # 30% chance to generate report
        }
        
        print(f"   🏥 Healthcare state: steps={self.state['step_count']}, calories={self.state['total_calories']}")
    
    def generate_log_line(self):
        """Generate healthcare-specific log with inner story"""
        
        # Randomly trigger different behaviors
        rand = random.random()
        
        if rand < self.chain_probabilities['step_update']:
            # Trigger step update chain - this writes multiple logs internally
            self.generate_step_chain()
            # Return a dummy value that won't be written again
            return {"skip": True}
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle']:
            # Toggle screen
            return self.generate_screen_event()
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle'] + self.chain_probabilities['report']:
            # Generate report
            return self.generate_report()
        else:
            # Regular log
            return super().generate_log_line()
    
    def generate_step_chain(self):
        """Generate a chain of related step events"""
        
        # Increment step count realistically
        step_increment = random.randint(1, 3)
        self.state['step_count'] += step_increment
        
        # Update calories (approx 17 calories per step from your data)
        self.state['total_calories'] += step_increment * 17
        
        # Log 1: Step changed
        log1 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_LSC',
            'user_id': str(self.state['patient_id']),
            'message': f"onStandStepChanged {self.state['step_count']}"
        }
        self.write_log(log1)
        print(f"   🔗 Chain 1/4: {log1['message']}")
        
        # Log 2: Update storage
        log2 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_SPUtils',
            'user_id': str(self.state['patient_id']),
            'message': f"setTodayTotalDetailSteps={self.state['step_count']}"
        }
        self.write_log(log2)
        print(f"   🔗 Chain 2/4: {log2['message']}")
        
        # Log 3: Recalculate calories
        log3 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_ExtSDM',
            'user_id': str(self.state['patient_id']),
            'message': f"calculateCaloriesWithCache totalCalories={self.state['total_calories']}"
        }
        self.write_log(log3)
        print(f"   🔗 Chain 3/4: {log3['message']}")
        
        # Log 4: Generate report
        log4 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_StandReportReceiver',
            'user_id': str(self.state['patient_id']),
            'message': f"REPORT : {self.state['step_count']} {random.randint(5000,6000)} {self.state['total_calories']} {self.state['altitude']}"
        }
        self.write_log(log4)
        print(f"   🔗 Chain 4/4: {log4['message']}")
    
    def generate_screen_event(self):
        """Generate screen on/off event"""
        self.state['screen_on'] = not self.state['screen_on']
        action = "SCREEN_ON" if self.state['screen_on'] else "SCREEN_OFF"
        
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_StandReportReceiver',
            'user_id': str(self.state['patient_id']),
            'message': f"onReceive action: android.intent.action.{action}"
        }
        print(f"   📱 Screen: {action}")
        return log_data
    
    def generate_report(self):
        """Generate a report log"""
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_StandReportReceiver',
            'user_id': str(self.state['patient_id']),
            'message': f"REPORT : {self.state['step_count']} {random.randint(5000,6000)} {self.state['total_calories']} {self.state['altitude']}"
        }
        print(f"   📊 Report: {log_data['message'][:50]}...")
        return log_data
    
    def generate_regular_log(self):
        """Generate a regular log using templates"""
        component = self.get_random_component()
        template = self.get_random_template()
        message = self.fill_template(template)
        
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': component,
            'user_id': str(self.state['patient_id']),
            'message': message
        }
        print(f"   📝 Regular: {message[:50]}...")
        return log_data

if __name__ == "__main__":
    server = HealthcareServer()
    server.max_logs = 20  # Generate 20 logs for testing
    server.run()
