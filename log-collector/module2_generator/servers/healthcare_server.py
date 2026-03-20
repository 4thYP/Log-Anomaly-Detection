# #!/usr/bin/env python3
# """
# Healthcare Server
# Generates realistic healthcare logs with inner stories
# """
#
# import sys
# import os
# import random
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#
# from core.base_server import BaseServer
#
# class HealthcareServer(BaseServer):
#     def __init__(self):
#         # Initialize with healthcare-specific patterns
#         super().__init__(
#             server_type="healthcare",
#             log_file="healthcare_server.log",
#             patterns_file="healthcare_patterns.json"
#         )
#         
#         # Healthcare-specific state (from your real logs)
#         self.state.update({
#             'step_count': 3579,  # Starting from your logs
#             'total_calories': 126775,
#             'altitude': 240,
#             'patient_id': 30002312,
#             'screen_on': True
#         })
#         
#         # Causal chain probabilities
#         self.chain_probabilities = {
#             'step_update': 0.4,  # 40% chance to trigger step update chain
#             'screen_toggle': 0.1,  # 10% chance to toggle screen
#             'report': 0.3  # 30% chance to generate report
#         }
#         
#         print(f"   🏥 Healthcare state: steps={self.state['step_count']}, calories={self.state['total_calories']}")
#     
#     def generate_log_line(self):
#         """Generate healthcare-specific log with inner story"""
#         
#         # Randomly trigger different behaviors
#         rand = random.random()
#         
#         if rand < self.chain_probabilities['step_update']:
#             # Trigger step update chain - this writes multiple logs internally
#             self.generate_step_chain()
#             # Return a dummy value that won't be written again
#             return {"skip": True}
#         elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle']:
#             # Toggle screen
#             return self.generate_screen_event()
#         elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle'] + self.chain_probabilities['report']:
#             # Generate report
#             return self.generate_report()
#         else:
#             # Regular log
#             return super().generate_log_line()
#     
#     def generate_step_chain(self):
#         """Generate a chain of related step events"""
#         
#         # Increment step count realistically
#         step_increment = random.randint(1, 3)
#         self.state['step_count'] += step_increment
#         
#         # Update calories (approx 17 calories per step from your data)
#         self.state['total_calories'] += step_increment * 17
#         
#         # Log 1: Step changed
#         log1 = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_LSC',
#             'user_id': str(self.state['patient_id']),
#             'message': f"onStandStepChanged {self.state['step_count']}"
#         }
#         self.write_log(log1)
#         print(f"   🔗 Chain 1/4: {log1['message']}")
#         
#         # Log 2: Update storage
#         log2 = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_SPUtils',
#             'user_id': str(self.state['patient_id']),
#             'message': f"setTodayTotalDetailSteps={self.state['step_count']}"
#         }
#         self.write_log(log2)
#         print(f"   🔗 Chain 2/4: {log2['message']}")
#         
#         # Log 3: Recalculate calories
#         log3 = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_ExtSDM',
#             'user_id': str(self.state['patient_id']),
#             'message': f"calculateCaloriesWithCache totalCalories={self.state['total_calories']}"
#         }
#         self.write_log(log3)
#         print(f"   🔗 Chain 3/4: {log3['message']}")
#         
#         # Log 4: Generate report
#         log4 = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_StandReportReceiver',
#             'user_id': str(self.state['patient_id']),
#             'message': f"REPORT : {self.state['step_count']} {random.randint(5000,6000)} {self.state['total_calories']} {self.state['altitude']}"
#         }
#         self.write_log(log4)
#         print(f"   🔗 Chain 4/4: {log4['message']}")
#     
#     def generate_screen_event(self):
#         """Generate screen on/off event"""
#         self.state['screen_on'] = not self.state['screen_on']
#         action = "SCREEN_ON" if self.state['screen_on'] else "SCREEN_OFF"
#         
#         log_data = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_StandReportReceiver',
#             'user_id': str(self.state['patient_id']),
#             'message': f"onReceive action: android.intent.action.{action}"
#         }
#         print(f"   📱 Screen: {action}")
#         return log_data
#     
#     def generate_report(self):
#         """Generate a report log"""
#         log_data = {
#             'timestamp': self.generate_timestamp(),
#             'component': 'Step_StandReportReceiver',
#             'user_id': str(self.state['patient_id']),
#             'message': f"REPORT : {self.state['step_count']} {random.randint(5000,6000)} {self.state['total_calories']} {self.state['altitude']}"
#         }
#         print(f"   📊 Report: {log_data['message'][:50]}...")
#         return log_data
#     
#     def generate_regular_log(self):
#         """Generate a regular log using templates"""
#         component = self.get_random_component()
#         template = self.get_random_template()
#         message = self.fill_template(template)
#         
#         log_data = {
#             'timestamp': self.generate_timestamp(),
#             'component': component,
#             'user_id': str(self.state['patient_id']),
#             'message': message
#         }
#         print(f"   📝 Regular: {message[:50]}...")
#         return log_data
#
# if __name__ == "__main__":
#     server = HealthcareServer()
#     server.max_logs = 20  # Generate 20 logs for testing
#     server.run()



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
            'screen_on': True,
            'sync_counter': 0
        })
        
        # Causal chain probabilities
        self.chain_probabilities = {
            'step_update': 0.4,      # 40% chance to trigger step update chain
            'screen_toggle': 0.1,    # 10% chance to toggle screen
            'report': 0.3,           # 30% chance to generate report
            'sync_event': 0.05,      # 5% chance for sync event
            'db_error': 0.02         # 2% chance for database error
        }
        
        # Templates that should NOT be used as regular logs (reserved for chains)
        self.chain_templates = [
            'onStandStepChanged', 'setTodayTotalDetailSteps',
            'calculateCaloriesWithCache', 'REPORT', 'onExtend'
        ]
        
        print(f"   🏥 Healthcare state: steps={self.state['step_count']}, calories={self.state['total_calories']}")
    
    def generate_log_line(self):
        """Generate healthcare-specific log with inner story"""
        
        # Randomly trigger different behaviors
        rand = random.random()
        
        if rand < self.chain_probabilities['step_update']:
            # Trigger step update chain - this writes multiple logs internally
            self.generate_step_chain()
            return {"skip": True}
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle']:
            # Toggle screen
            return self.generate_screen_event()
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle'] + self.chain_probabilities['report']:
            # Generate report
            return self.generate_report()
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle'] + self.chain_probabilities['report'] + self.chain_probabilities['sync_event']:
            # Generate sync event
            return self.generate_sync_event()
        elif rand < self.chain_probabilities['step_update'] + self.chain_probabilities['screen_toggle'] + self.chain_probabilities['report'] + self.chain_probabilities['sync_event'] + self.chain_probabilities['db_error']:
            # Generate database error
            return self.generate_db_error()
        else:
            # Regular log using real templates
            return self.generate_regular_log()
    
    def generate_step_chain(self):
        """Generate a chain of related step events"""
        
        # Increment step count realistically
        step_increment = random.randint(1, 3)
        self.state['step_count'] += step_increment
        
        # Update calories (approx 17 calories per step from your data)
        self.state['total_calories'] += step_increment * 17
        
        # Generate timestamp once for chain consistency
        base_timestamp = self.generate_timestamp()
        
        # Log 1: Step changed
        log1 = {
            'timestamp': base_timestamp,
            'component': 'Step_LSC',
            'user_id': str(self.state['patient_id']),
            'message': f"onStandStepChanged {self.state['step_count']}"
        }
        self.write_log(log1)
        
        # Log 2: Update storage (increment timestamp slightly)
        log2 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_SPUtils',
            'user_id': str(self.state['patient_id']),
            'message': f"setTodayTotalDetailSteps={self.state['step_count']}"
        }
        self.write_log(log2)
        
        # Log 3: Recalculate calories
        log3 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_ExtSDM',
            'user_id': str(self.state['patient_id']),
            'message': f"calculateCaloriesWithCache totalCalories={self.state['total_calories']}"
        }
        self.write_log(log3)
        
        # Log 4: Generate report
        distance = random.randint(5000, 6000)
        log4 = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_StandReportReceiver',
            'user_id': str(self.state['patient_id']),
            'message': f"REPORT : {self.state['step_count']} {distance} {self.state['total_calories']} {self.state['altitude']}"
        }
        self.write_log(log4)
    
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
        return log_data
    
    def generate_report(self):
        """Generate a report log"""
        distance = random.randint(5000, 6000)
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': 'Step_StandReportReceiver',
            'user_id': str(self.state['patient_id']),
            'message': f"REPORT : {self.state['step_count']} {distance} {self.state['total_calories']} {self.state['altitude']}"
        }
        return log_data
    
    def generate_sync_event(self):
        """Generate sync-related events"""
        self.state['sync_counter'] += 1
        
        sync_messages = [
            f"startTimer start autoSync",
            f"startSync hiSyncOption = HiSyncOption{{syncAction=1, syncMethod=2, syncScope=0, syncDataType=20000, syncModel=2, pushAction=0}},app = 1 who = 1",
            f"needAutoSync autoSyncSwitch is open",
            f"initDataPrivacy the dataPrivacy switch is open, start push health data!",
            f"initDataPrivacy the dataPrivacy is true",
            f"initUserPrivacy the userPrivacy switch is open, start push user data!",
            f"initUserPrivacy the userPrivacy is true",
            f"ifCanSync not! no cloud version",
            f"sendSyncFailedBroadcast"
        ]
        
        message = random.choice(sync_messages)
        
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': 'HiH_HiSyncControl',
            'user_id': str(self.state['patient_id']),
            'message': message
        }
        return log_data
    
    def generate_db_error(self):
        """Generate database error events"""
        error_messages = [
            f"saveHealthDetailData() saveOneDetailData fail hiHealthData = 1513958400000,type = 40003",
            f"insertHiHealthData() bulkSaveDetailHiHealthData fail errorCode = 4,errorMessage = ERR_DATA_INSERT",
            f"step count inconsistency detected: expected {self.state['step_count']} got {self.state['step_count'] + random.randint(1, 3)}",
            f"slow database query detected: took {random.randint(5000, 15000)}ms"
        ]
        
        message = random.choice(error_messages)
        
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': random.choice(['HiH_HiHealthDataInsertStore', 'HiH_HiHealthBinder', 'HiH_HiSyncControl']),
            'user_id': str(self.state['patient_id']),
            'message': message
        }
        return log_data
    
    def generate_regular_log(self):
        """Generate a regular log using real templates from patterns"""
        # Get templates from patterns
        templates = self.patterns.get('templates', {}).get('by_frequency', {})
        
        # Filter out chain templates
        available_templates = []
        for template in templates.keys():
            # Skip chain templates
            skip = False
            for chain_template in self.chain_templates:
                if chain_template in template:
                    skip = True
                    break
            if not skip:
                available_templates.append(template)
        
        if available_templates:
            # Use a real template from patterns
            template = random.choice(available_templates)
            message = self.fill_template(template)
        else:
            # Fallback to realistic messages
            real_messages = [
                f"getTodayTotalDetailSteps = 1514038440000##{self.state['step_count']}##548365##8661##{random.randint(12000, 16000)}##{random.randint(27100000, 27150000)}",
                f"saveStatData() type =40002,time = 1513958400000,statClient = 2,who is 1",
                f"new date =20171223, type=40002,{self.state['step_count']}.0,old={self.state['step_count'] - random.randint(10, 30)}.0",
                f"getBinderPackageName packageName = com.huawei.health",
                f"getAppContext() isAppValid health or wear, packageName = com.huawei.health",
                f"checkInsertStatus stepSum or calorieSum is enough",
                f"startListenerChange subscribeList = [1]",
                f"flush sensor data",
                f"timeStamp back,extendReportTimeStamp={random.randint(1514039575000, 1514042265000)}",
                f"upLoadOneMinuteDataToEngine time={random.randint(25233975, 25233979)},0,{random.randint(1, 100)},0,20002"
            ]
            message = random.choice(real_messages)
        
        log_data = {
            'timestamp': self.generate_timestamp(),
            'component': self.get_random_component(),
            'user_id': str(self.state['patient_id']),
            'message': message
        }
        return log_data

if __name__ == "__main__":
    server = HealthcareServer()
    server.max_logs = 20  # Generate 20 logs for testing
    server.run()
