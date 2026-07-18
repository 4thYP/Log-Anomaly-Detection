"""
HealthApp Parser and Feature Extractor Test Cases

This module demonstrates the complete pipeline:
Raw Log → Parsed Output → Feature Vector

Tests cover motion tracking, health metrics, persistence, lifecycle events.
"""

import pytest
from datetime import datetime
from app.models.log_models import LogCreate, ServerType
from app.parsers.healthapp_parser import HealthAppParser
from app.features.healthapp_feature_extractor import HealthAppFeatureExtractor


class TestHealthAppParserBasic:
    """Test HealthApp parser output format and schema compliance"""
    
    @pytest.fixture
    def parser(self):
        return HealthAppParser()
    
    def test_step_count_changed_event(self, parser):
        """Test E42: onStandStepChanged"""
        raw_log = "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "step_count_changed"
        assert parsed["component"] == "Step_LSC"
        assert parsed["template_id"] == 42
        assert parsed["timestamp"] == "2017-12-23T22:15:29.792"
        assert parsed["status"] == "success"
        assert parsed["metadata"]["step_count"] == 3580
        assert parsed["metadata"]["pid"] == "30002312"
    
    def test_motion_extended_event(self, parser):
        """Test E39: onExtend with acceleration parameters"""
        raw_log = "20171223-22:15:29:615|Step_LSC|30002312|onExtend:1514038530000 14 0 4"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "motion_extended"
        assert parsed["component"] == "Step_LSC"
        assert parsed["template_id"] == 39
        assert parsed["timestamp"] == "2017-12-23T22:15:29.615"
        assert parsed["metadata"]["event_timestamp"] == 1514038530000
        assert parsed["metadata"]["acceleration_x"] == 14
        assert parsed["metadata"]["acceleration_y"] == 0
        assert parsed["metadata"]["acceleration_z"] == 4
    
    def test_health_metrics_report_event(self, parser):
        """Test E47: REPORT with steps, stands, calories, altitude"""
        raw_log = "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 7007 5002 150089 240"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "health_metrics_report"
        assert parsed["component"] == "Step_StandReportReceiver"
        assert parsed["template_id"] == 47
        assert parsed["timestamp"] == "2017-12-23T22:15:29.649"
        assert parsed["metadata"]["steps"] == 7007
        assert parsed["metadata"]["stands"] == 5002
        assert parsed["metadata"]["calories"] == 150089
        assert parsed["metadata"]["altitude"] == 240
    
    def test_calories_calculated_event(self, parser):
        """Test E4: calculateCaloriesWithCache"""
        raw_log = "20171223-22:15:29:645|Step_ExtSDM|30002312|calculateCaloriesWithCache totalCalories=126775"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "calories_calculated"
        assert parsed["component"] == "Step_ExtSDM"
        assert parsed["template_id"] == 4
        assert parsed["timestamp"] == "2017-12-23T22:15:29.645"
        assert parsed["metadata"]["total_calories"] == 126775
    
    def test_altitude_calculated_event(self, parser):
        """Test E3: calculateAltitudeWithCache"""
        raw_log = "20171223-22:15:29:648|Step_ExtSDM|30002312|calculateAltitudeWithCache totalAltitude=240"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "altitude_calculated"
        assert parsed["component"] == "Step_ExtSDM"
        assert parsed["template_id"] == 3
        assert parsed["metadata"]["total_altitude"] == 240
    
    def test_step_data_updated_event(self, parser):
        """Test E58: setTodayTotalDetailSteps with multi-field data"""
        raw_log = "20171223-22:15:29:636|Step_SPUtils|30002312|setTodayTotalDetailSteps=1514038440000##7007##548365##8661##12361##27173954"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "step_data_updated"
        assert parsed["component"] == "Step_SPUtils"
        assert parsed["template_id"] == 58
        assert parsed["metadata"]["start_time"] == 1514038440000
        assert parsed["metadata"]["field1"] == 7007
        assert len(parsed["metadata"]["raw_data"].split("##")) == 6
    
    def test_screen_on_event(self, parser):
        """Test E41: onReceive SCREEN_ON"""
        raw_log = "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_ON"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "screen_on_received"
        assert parsed["component"] == "Step_StandReportReceiver"
        assert parsed["template_id"] == 41
    
    def test_screen_off_event(self, parser):
        """Test E40: onReceive SCREEN_OFF"""
        raw_log = "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_OFF"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "screen_off_received"
        assert parsed["component"] == "Step_StandReportReceiver"
        assert parsed["template_id"] == 40
    
    def test_sensor_flush_event(self, parser):
        """Test E12: flush sensor data"""
        raw_log = "20171223-22:15:29:635|Step_StandStepCounter|30002312|flush sensor data"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "sensor_data_flushed"
        assert parsed["component"] == "Step_StandStepCounter"
        assert parsed["template_id"] == 12
    
    def test_malformed_log_returns_unknown(self, parser):
        """Test malformed/unparseable log returns unknown event"""
        raw_log = "invalid log format no pipe separator at all"
        
        parsed = parser.parse(raw_log)
        
        # Malformed logs return unknown event type
        assert parsed["event_type"] == "unknown"


class TestHealthAppFeatureExtractor:
    """Test feature extraction and output format"""
    
    @pytest.fixture
    def extractor(self):
        return HealthAppFeatureExtractor()
    
    @pytest.fixture
    def parser(self):
        return HealthAppParser()
    
    def create_log_internal(self, sid, raw_log):
        """Helper to create LogInternal with parsed data"""
        from app.models.log_models import LogInternal
        
        parser = HealthAppParser()
        parsed_data = parser.parse(raw_log)
        
        log_internal = LogInternal(
            sid=sid,
            timestamp=datetime.now(),
            server_type=ServerType.HEALTHAPP,
            log_file="healthapp.log",
            message=raw_log,
            metadata={"parsed": parsed_data}
        )
        return log_internal
    
    def test_feature_vector_format(self, extractor):
        """Test feature output is List[float], not Dict"""
        log = self.create_log_internal(
            "device-001",
            "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        )
        
        features = extractor.extract(log)
        
        # Check type and length
        assert isinstance(features, list)
        assert len(features) == 15
        assert all(isinstance(f, float) for f in features)
    
    def test_all_features_normalized_01(self, extractor):
        """Test all features are normalized to [0, 1]"""
        log = self.create_log_internal(
            "device-001",
            "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        )
        
        features = extractor.extract(log)
        
        # All values should be in [0, 1]
        assert all(0.0 <= f <= 1.0 for f in features)
    
    def test_per_device_isolation(self, extractor):
        """Test feature extraction maintains state per device (sid)"""
        # Device 1: motion event
        log1a = self.create_log_internal(
            "device-1",
            "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        )
        features1a = extractor.extract(log1a)
        
        # Device 2: report event
        log2a = self.create_log_internal(
            "device-2",
            "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 7007 5002 150089 240"
        )
        features2a = extractor.extract(log2a)
        
        # Device 1: another motion
        log1b = self.create_log_internal(
            "device-1",
            "20171223-22:15:30:792|Step_LSC|30002312|onStandStepChanged 3581"
        )
        features1b = extractor.extract(log1b)
        
        # Device 1 should have accumulated state
        assert features1a != features1b
        assert len(extractor.server_states["device-1"].step_events) >= 2
        assert len(extractor.server_states["device-2"].metrics_events) >= 1
    
    def test_motion_event_density_calculation(self, extractor):
        """Test motion_event_density tracks step changes"""
        # Add multiple motion events
        for i in range(3):
            log = self.create_log_internal(
                "device-003",
                f"20171223-22:15:{29+i}:700|Step_LSC|30002312|onStandStepChanged {3580+i}"
            )
            features = extractor.extract(log)
        
        motion_density = features[1]  # Index 1 is motion_event_density
        assert motion_density > 0  # Should have motion events
    
    def test_report_frequency_increases(self, extractor):
        """Test report_frequency tracks health metrics reports"""
        # Add motion first
        log1 = self.create_log_internal(
            "device-004",
            "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        )
        features1 = extractor.extract(log1)
        
        # Add report
        log2 = self.create_log_internal(
            "device-004",
            "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 7007 5002 150089 240"
        )
        features2 = extractor.extract(log2)
        
        report_freq_1 = features1[2]
        report_freq_2 = features2[2]
        
        assert report_freq_2 >= report_freq_1  # Reports increased


class TestHealthAppPipelineIntegration:
    """Test end-to-end pipeline: LogCreate → Parse → Extract"""
    
    def test_full_pipeline_single_log(self):
        """Test complete pipeline for single log"""
        from app.models.log_models import LogInternal
        from app.parsers.parser_factory import ParserFactory
        from app.features.feature_extractor_factory import FeatureExtractorFactory
        
        # Create log
        raw_log = "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580"
        
        log_create = LogCreate(
            sid="device-fitness-001",
            timestamp=datetime.now(),
            server_type=ServerType.HEALTHAPP,
            log_file="healthapp_fitness.log",
            message=raw_log,
        )
        
        # Convert to internal
        log_internal = LogInternal(**log_create.model_dump())
        
        # Parse
        parser = ParserFactory.get_parser(ServerType.HEALTHAPP)
        parsed_data = parser.parse(raw_log)
        log_internal.metadata = {"parsed": parsed_data}
        
        # Extract features
        extractor = FeatureExtractorFactory.get_extractor(ServerType.HEALTHAPP)
        features = extractor.extract(log_internal)
        
        # Verify end-to-end
        assert len(features) == 15
        assert all(0.0 <= f <= 1.0 for f in features)
        assert log_internal.metadata["parsed"]["event_type"] == "step_count_changed"
    
    def test_multi_device_processing(self):
        """Test processing multiple devices concurrently"""
        from app.models.log_models import LogInternal
        from app.parsers.parser_factory import ParserFactory
        from app.features.feature_extractor_factory import FeatureExtractorFactory
        
        parser = ParserFactory.get_parser(ServerType.HEALTHAPP)
        extractor = FeatureExtractorFactory.get_extractor(ServerType.HEALTHAPP)
        
        # Device 1 logs: Mixed events
        device1_logs = [
            "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580",
            "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 7007 5002 150089 240",
            "20171223-22:15:29:645|Step_ExtSDM|30002312|calculateCaloriesWithCache totalCalories=126775",
        ]
        
        # Device 2 logs: Different pattern
        device2_logs = [
            "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_ON",
            "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_OFF",
        ]
        
        features_dev1 = []
        features_dev2 = []
        
        for raw_log in device1_logs:
            log_internal = LogInternal(
                sid="device-1",
                timestamp=datetime.now(),
                server_type=ServerType.HEALTHAPP,
                log_file="test.log",
                message=raw_log,
                metadata={"parsed": parser.parse(raw_log)}
            )
            features_dev1.append(extractor.extract(log_internal))
        
        for raw_log in device2_logs:
            log_internal = LogInternal(
                sid="device-2",
                timestamp=datetime.now(),
                server_type=ServerType.HEALTHAPP,
                log_file="test.log",
                message=raw_log,
                metadata={"parsed": parser.parse(raw_log)}
            )
            features_dev2.append(extractor.extract(log_internal))
        
        # Device 1 should have higher motion density
        motion_density_dev1 = features_dev1[-1][1]
        motion_density_dev2 = features_dev2[-1][1]
        
        assert motion_density_dev1 >= motion_density_dev2
        
        # Device 2 should have higher lifecycle intensity
        lifecycle_dev1 = features_dev1[-1][13]
        lifecycle_dev2 = features_dev2[-1][13]
        
        assert lifecycle_dev2 >= lifecycle_dev1


class TestHealthAppEdgeCases:
    """Test edge cases and robustness"""
    
    @pytest.fixture
    def parser(self):
        return HealthAppParser()
    
    def test_timestamp_parsing(self, parser):
        """Test HealthApp timestamp parsing (YYYYMMDDHHMMSSmmm format)"""
        raw_log = "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["timestamp"] == "2017-12-23T22:15:29.606"
    
    def test_malformed_timestamp(self, parser):
        """Test graceful handling of logs with missing pipe separators"""
        raw_log = "no pipes in this log at all just text"
        
        parsed = parser.parse(raw_log)
        
        # Should gracefully fall back to unknown
        assert parsed["event_type"] == "unknown"
    
    def test_large_metric_values(self, parser):
        """Test handling of large metric values (calories, steps)"""
        raw_log = "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 999999 50000 5000000 10000"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["metadata"]["steps"] == 999999
        assert parsed["metadata"]["calories"] == 5000000
    
    def test_multi_field_data_parsing(self, parser):
        """Test complex multi-field data with ## delimiters"""
        raw_log = "20171223-22:15:29:636|Step_SPUtils|30002312|setTodayTotalDetailSteps=1514038440000##7007##548365##8661##12361##27173954"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["metadata"]["start_time"] == 1514038440000
        assert len(parsed["metadata"]["raw_data"].split("##")) == 6
    
    def test_very_small_timestamp_values(self, parser):
        """Test handling of small millisecond values"""
        raw_log = "20171223-22:15:29:001|Step_LSC|30002312|onStandStepChanged 3579"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["timestamp"] == "2017-12-23T22:15:29.001"
    
    def test_zero_values_in_metrics(self, parser):
        """Test handling of zero values in motion/metrics"""
        raw_log = "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 0 0 0 0"
        
        parsed = parser.parse(raw_log)
        
        assert parsed["metadata"]["steps"] == 0
        assert parsed["metadata"]["stands"] == 0


# ============================================================================
# EXAMPLE TEST DATA - Complete Examples with Raw, Parsed, and Features
# ============================================================================

EXAMPLE_1 = {
    "name": "Step Count Changed",
    "raw_log": "20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580",
    "expected_parsed": {
        "event_type": "step_count_changed",
        "component": "Step_LSC",
        "template_id": 42,
        "timestamp": "2017-12-23T22:15:29.792",
        "status": "success",
    },
}

EXAMPLE_2 = {
    "name": "Health Metrics Report",
    "raw_log": "20171223-22:15:29:649|Step_StandReportReceiver|30002312|REPORT : 7007 5002 150089 240",
    "expected_parsed": {
        "event_type": "health_metrics_report",
        "component": "Step_StandReportReceiver",
        "template_id": 47,
        "metadata_keys": ["steps", "stands", "calories", "altitude"],
    },
}

EXAMPLE_3 = {
    "name": "Calories Calculated",
    "raw_log": "20171223-22:15:29:645|Step_ExtSDM|30002312|calculateCaloriesWithCache totalCalories=126775",
    "expected_parsed": {
        "event_type": "calories_calculated",
        "component": "Step_ExtSDM",
        "template_id": 4,
        "metadata_keys": ["total_calories"],
    },
}

EXAMPLE_4 = {
    "name": "Screen On Event",
    "raw_log": "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_ON",
    "expected_parsed": {
        "event_type": "screen_on_received",
        "component": "Step_StandReportReceiver",
        "template_id": 41,
    },
}

EXAMPLE_5 = {
    "name": "Step Data Updated",
    "raw_log": "20171223-22:15:29:636|Step_SPUtils|30002312|setTodayTotalDetailSteps=1514038440000##7007##548365##8661##12361##27173954",
    "expected_parsed": {
        "event_type": "step_data_updated",
        "component": "Step_SPUtils",
        "template_id": 58,
        "metadata_keys": ["start_time", "raw_data"],
    },
}


if __name__ == "__main__":
    # Example usage for manual testing
    print("=== HealthApp Test Examples ===\n")
    
    parser = HealthAppParser()
    extractor = HealthAppFeatureExtractor()
    
    for example in [EXAMPLE_1, EXAMPLE_2, EXAMPLE_3, EXAMPLE_4, EXAMPLE_5]:
        print(f"\n{example['name']}")
        print(f"Raw: {example['raw_log']}\n")
        
        parsed = parser.parse(example['raw_log'])
        print(f"Parsed event_type: {parsed['event_type']}, component: {parsed['component']}")
        print(f"Template ID: {parsed['template_id']}, Status: {parsed['status']}")
        
        # Create LogInternal for feature extraction
        from app.models.log_models import LogInternal
        
        log = LogInternal(
            sid="test-device",
            timestamp=datetime.now(),
            server_type=ServerType.HEALTHAPP,
            log_file="test.log",
            message=example['raw_log'],
            metadata={"parsed": parsed}
        )
        
        features = extractor.extract(log)
        print(f"Features: {[f'{f:.3f}' for f in features]}")
