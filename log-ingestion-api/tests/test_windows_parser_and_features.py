"""
Test suite for Windows log parser and feature extractor.
Tests cover all 6 major event categories and anomaly detection.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from app.models.log_models import LogInternal, ServerType
from app.parsers.windows_parser import WindowsParser, ParsedWindowsLogEvent
from app.features.windows_feature_extractor import (
    WindowsFeatureExtractor,
    get_windows_feature_extractor,
)


# ============================================================================
# TEST DATA - Real Windows event log samples from Loghub dataset
# ============================================================================

class WindowsLogSamples:
    """Collection of real Windows event log samples"""

    @staticmethod
    def service_start() -> str:
        """E48: Service startup event"""
        return "2016-09-28 04:30:30, Info       CBS    TrustedInstaller service starts successfully."

    @staticmethod
    def service_stop() -> str:
        """E15: Service shutdown event"""
        return "2016-09-28 04:33:15, Info       CBS    Ending the TrustedInstaller main loop."

    @staticmethod
    def service_init_start() -> str:
        """E46: Service initialization start"""
        return "2016-09-28 04:30:30, Info       CBS    Starting TrustedInstaller initialization."

    @staticmethod
    def service_init_end() -> str:
        """E17: Service initialization end"""
        return "2016-09-28 04:30:35, Info       CBS    Ending TrustedInstaller initialization."

    @staticmethod
    def transaction_create_success() -> str:
        """E1: Transaction creation success"""
        return "2016-09-28 04:31:05, Info       CSI    0x6a8 Created NT transaction (seq 1) result 0x00000000, handle @0x158."

    @staticmethod
    def transaction_create_failure() -> str:
        """E1 variant: Transaction creation failure"""
        return "2016-09-28 04:31:10, Info       CSI    0x6a8 Created NT transaction (seq 2) result 0x80004005, handle @0x160."

    @staticmethod
    def package_applicability() -> str:
        """E29: Package applicability check"""
        return "2016-09-28 04:31:15, Info       CBS    Read out cached package applicability for package: Package_for_KB2919355, ApplicableState: 1, CurrentState:0."

    @staticmethod
    def session_initialized() -> str:
        """E36: Session initialization"""
        return "2016-09-28 04:31:20, Info       CBS    Session: 305_1 initialized by client WindowsUpdateAgent."

    @staticmethod
    def manifest_error() -> str:
        """E18: Manifest parsing error - error cascade indicator"""
        return "2016-09-28 04:31:25, Info       CBS    Expecting attribute name [HRESULT = 0x800f080d - CBS_E_MANIFEST_INVALID_ITEM]."

    @staticmethod
    def parse_error_cascade_1() -> str:
        """E20: Parse error (part of error cascade)"""
        return "2016-09-28 04:31:26, Info       CBS    Failed to get next element [HRESULT = 0x800f080d - CBS_E_MANIFEST_INVALID_ITEM]."

    @staticmethod
    def parse_error_cascade_2() -> str:
        """E20: Parse error (continuation of cascade)"""
        return "2016-09-28 04:31:27, Info       CBS    Failed to get next element [HRESULT = 0x800f080d - CBS_E_MANIFEST_INVALID_ITEM]."

    @staticmethod
    def parse_error_cascade_3() -> str:
        """E20: Parse error (continuation of cascade)"""
        return "2016-09-28 04:31:28, Info       CBS    Failed to get next element [HRESULT = 0x800f080d - CBS_E_MANIFEST_INVALID_ITEM]."

    @staticmethod
    def package_error() -> str:
        """E21: Package operation error"""
        return "2016-09-28 04:31:30, Info       CBS    Failed to internally open package. [HRESULT = 0x80073cf9 - CBS_E_INVALID_PACKAGE]."

    @staticmethod
    def sqm_upload_failed() -> str:
        """E39: SQM upload failure"""
        return "2016-09-28 04:32:00, Info       CBS    SQM: Failed to start upload with file pattern: C:\\\\Windows\\\\Temp\\\\qmgr.log, flags: 0x00000000 [HRESULT = 0x80070005 - E_FAIL]."

    @staticmethod
    def sqm_upload_failed_alt() -> str:
        """E38: Alternative SQM upload failure"""
        return "2016-09-28 04:32:05, Info       CBS    SQM: Failed to start standard sample upload. [HRESULT = 0x80070005 - E_FAIL]."

    @staticmethod
    def warning_unrecognized() -> str:
        """E50: Unrecognized attribute warning"""
        return "2016-09-28 04:32:10, Info       CBS    Warning: Unrecognized packageExtended attribute."

    @staticmethod
    def csi_perf_trace() -> str:
        """E3: CSI performance trace (system info)"""
        return "2016-09-28 04:32:15, Info       CSI    0x8a8 CSI perf trace:"

    @staticmethod
    def unknown_format() -> str:
        """Unparseable format (error handling test)"""
        return "This is not a valid Windows event log format."


# ============================================================================
# PARSER TESTS
# ============================================================================

class TestWindowsParser:
    """Test suite for Windows log parser"""

    @pytest.fixture
    def parser(self) -> WindowsParser:
        """Create parser instance"""
        return WindowsParser()

    def test_service_start_parsing(self, parser: WindowsParser):
        """Test service startup event parsing"""
        log_line = WindowsLogSamples.service_start()
        result = parser.parse(log_line)

        assert result["event_type"] == "service_start"
        assert result["component"] == "CBS"
        assert result["status"] == "success"
        assert result["template_id"] == "E48"
        assert result["parsed_successfully"] is True
        assert result["confidence"] == 1.0

    def test_service_stop_parsing(self, parser: WindowsParser):
        """Test service shutdown event parsing"""
        log_line = WindowsLogSamples.service_stop()
        result = parser.parse(log_line)

        assert result["event_type"] == "service_stop"
        assert result["component"] == "CBS"
        assert result["status"] == "success"
        assert result["template_id"] == "E15"

    def test_transaction_create_success(self, parser: WindowsParser):
        """Test successful transaction creation"""
        log_line = WindowsLogSamples.transaction_create_success()
        result = parser.parse(log_line)

        assert result["event_type"] == "transaction_create"
        assert result["component"] == "CSI"
        assert result["status"] == "success"
        assert result["hresult"] == "0x00000000"
        assert result["sequence_number"] == 1
        assert result["handle"] == "@0x158"

    def test_transaction_create_failure(self, parser: WindowsParser):
        """Test failed transaction creation"""
        log_line = WindowsLogSamples.transaction_create_failure()
        result = parser.parse(log_line)

        assert result["event_type"] == "transaction_create"
        assert result["status"] == "failure"
        assert result["hresult"] == "0x80004005"

    def test_package_applicability_parsing(self, parser: WindowsParser):
        """Test package applicability event"""
        log_line = WindowsLogSamples.package_applicability()
        result = parser.parse(log_line)

        assert result["event_type"] == "package_applicability"
        assert result["component"] == "CBS"
        assert result["status"] == "success"
        assert result["template_id"] == "E29"
        assert "Package_for_KB2919355" in result["package_name"]

    def test_session_initialization_parsing(self, parser: WindowsParser):
        """Test session initialization event"""
        log_line = WindowsLogSamples.session_initialized()
        result = parser.parse(log_line)

        assert result["event_type"] == "session_initialized"
        assert result["component"] == "CBS"
        assert result["status"] == "success"
        assert result["session_id"] == "305_1"
        assert result["client"] == "WindowsUpdateAgent"

    def test_manifest_error_parsing(self, parser: WindowsParser):
        """Test manifest parsing error"""
        log_line = WindowsLogSamples.manifest_error()
        result = parser.parse(log_line)

        assert result["event_type"] == "manifest_error"
        assert result["component"] == "CBS"
        assert result["status"] == "failure"
        assert result["hresult"] == "0x800f080d"
        assert result["error_name"] == "CBS_E_MANIFEST_INVALID_ITEM"

    def test_parse_error_parsing(self, parser: WindowsParser):
        """Test parse error event"""
        log_line = WindowsLogSamples.parse_error_cascade_1()
        result = parser.parse(log_line)

        assert result["event_type"] == "parse_error"
        assert result["component"] == "CBS"
        assert result["status"] == "failure"
        assert result["hresult"] == "0x800f080d"

    def test_package_error_parsing(self, parser: WindowsParser):
        """Test package operation error"""
        log_line = WindowsLogSamples.package_error()
        result = parser.parse(log_line)

        assert result["event_type"] == "package_error"
        assert result["component"] == "CBS"
        assert result["status"] == "failure"
        assert result["hresult"] == "0x80073cf9"
        assert result["error_name"] == "CBS_E_INVALID_PACKAGE"

    def test_sqm_upload_error_parsing(self, parser: WindowsParser):
        """Test SQM upload failure"""
        log_line = WindowsLogSamples.sqm_upload_failed()
        result = parser.parse(log_line)

        assert result["event_type"] == "upload_error"
        assert result["component"] == "CBS"
        assert result["status"] == "failure"
        assert result["hresult"] == "0x80070005"
        assert result["error_name"] == "E_FAIL"
        assert result["template_id"] == "E39"

    def test_sqm_upload_error_alt_parsing(self, parser: WindowsParser):
        """Test alternative SQM upload failure"""
        log_line = WindowsLogSamples.sqm_upload_failed_alt()
        result = parser.parse(log_line)

        assert result["event_type"] == "upload_error"
        assert result["status"] == "failure"
        assert result["template_id"] == "E38"

    def test_warning_parsing(self, parser: WindowsParser):
        """Test unrecognized attribute warning"""
        log_line = WindowsLogSamples.warning_unrecognized()
        result = parser.parse(log_line)

        assert result["event_type"] == "parse_error"
        assert result["status"] == "warning"

    def test_csi_perf_trace_parsing(self, parser: WindowsParser):
        """Test CSI performance trace event"""
        log_line = WindowsLogSamples.csi_perf_trace()
        result = parser.parse(log_line)

        assert result["component"] == "CSI"
        assert result["status"] == "info"

    def test_unknown_format_handling(self, parser: WindowsParser):
        """Test handling of unparseable logs"""
        log_line = WindowsLogSamples.unknown_format()
        result = parser.parse(log_line)

        assert result["event_type"] == "unknown"
        assert result["parsed_successfully"] is False
        assert result["confidence"] == 0.0


# ============================================================================
# FEATURE EXTRACTOR TESTS
# ============================================================================

class TestWindowsFeatureExtractor:
    """Test suite for Windows feature extractor"""

    @pytest.fixture
    def extractor(self) -> WindowsFeatureExtractor:
        """Create fresh extractor instance"""
        ext = WindowsFeatureExtractor()
        ext.reset_state()
        return ext

    @staticmethod
    def create_log_internal(event_dict: Dict[str, Any]) -> LogInternal:
        """Helper to create LogInternal with parsed event"""
        log = LogInternal(
            message=event_dict.get("raw_message", ""),
            server_type=ServerType.WINDOWS,
            timestamp=datetime.now().isoformat(),
        )
        log.metadata = {"parsed": event_dict}
        return log

    def test_feature_extraction_single_event(self, extractor: WindowsFeatureExtractor):
        """Test feature extraction from a single event"""
        log = self.create_log_internal(
            WindowsParser().parse(WindowsLogSamples.service_start())
        )
        features = extractor.extract(log)

        assert isinstance(features, dict)
        assert "event_count_total" in features
        assert "error_count_total" in features
        assert "anomaly_score" in features
        assert features["event_count_total"] == 1.0
        assert features["error_count_total"] == 0.0

    def test_error_tracking(self, extractor: WindowsFeatureExtractor):
        """Test error counting and tracking"""
        # Add success event
        log1 = self.create_log_internal(
            WindowsParser().parse(WindowsLogSamples.service_start())
        )
        features1 = extractor.extract(log1)

        # Add error event
        log2 = self.create_log_internal(
            WindowsParser().parse(WindowsLogSamples.manifest_error())
        )
        features2 = extractor.extract(log2)

        assert features1["error_count_total"] == 0.0
        assert features2["error_count_total"] == 1.0
        assert features2["error_rate"] == 0.5  # 1 error out of 2 events

    def test_error_cascade_detection(self, extractor: WindowsFeatureExtractor):
        """Test detection of error cascades (5+ consecutive errors)"""
        parser = WindowsParser()

        # Add 5 consecutive errors
        for i in range(5):
            log = self.create_log_internal(
                parser.parse(WindowsLogSamples.parse_error_cascade_1())
            )
            features = extractor.extract(log)

        # Should detect cascade anomaly
        assert features["error_consecutive_max"] == 5.0
        assert features["anomaly_error_cascade"] == 1.0

    def test_transaction_tracking(self, extractor: WindowsFeatureExtractor):
        """Test transaction creation tracking"""
        parser = WindowsParser()

        # Add success transaction
        log1 = self.create_log_internal(
            parser.parse(WindowsLogSamples.transaction_create_success())
        )
        features1 = extractor.extract(log1)

        # Add failure transaction
        log2 = self.create_log_internal(
            parser.parse(WindowsLogSamples.transaction_create_failure())
        )
        features2 = extractor.extract(log2)

        assert features1["transaction_count_success"] == 1.0
        assert features2["transaction_count_failure"] == 1.0
        assert features2["transaction_success_rate"] == 0.5  # 1 success, 1 failure

    def test_package_error_tracking(self, extractor: WindowsFeatureExtractor):
        """Test package error detection"""
        parser = WindowsParser()

        # Add package success
        log1 = self.create_log_internal(
            parser.parse(WindowsLogSamples.package_applicability())
        )
        extractor.extract(log1)

        # Add package error
        log2 = self.create_log_internal(
            parser.parse(WindowsLogSamples.package_error())
        )
        features2 = extractor.extract(log2)

        assert features2["package_count_unique"] > 0.0
        assert features2["package_count_errors"] == 1.0

    def test_service_state_tracking(self, extractor: WindowsFeatureExtractor):
        """Test service lifecycle state tracking"""
        parser = WindowsParser()
        
        # Service init
        log1 = self.create_log_internal(
            parser.parse(WindowsLogSamples.service_init_start())
        )
        features1 = extractor.extract(log1)
        assert features1["service_state"] == 0.5  # initializing

        # Service start
        log2 = self.create_log_internal(
            parser.parse(WindowsLogSamples.service_start())
        )
        features2 = extractor.extract(log2)
        assert features2["service_state"] == 1.0  # running

        # Service stop
        log3 = self.create_log_internal(
            parser.parse(WindowsLogSamples.service_stop())
        )
        features3 = extractor.extract(log3)
        assert features3["service_state"] == 0.0  # stopped

    def test_session_tracking(self, extractor: WindowsFeatureExtractor):
        """Test session tracking across events"""
        parser = WindowsParser()

        log = self.create_log_internal(
            parser.parse(WindowsLogSamples.session_initialized())
        )
        features = extractor.extract(log)

        assert features["session_count_created"] == 1.0
        assert features["session_count_active"] == 1.0
        assert features["session_count_unique"] == 1.0

    def test_hresult_code_analysis(self, extractor: WindowsFeatureExtractor):
        """Test HRESULT code tracking and analysis"""
        parser = WindowsParser()

        # Add multiple errors with same HRESULT
        for _ in range(3):
            log = self.create_log_internal(
                parser.parse(WindowsLogSamples.manifest_error())
            )
            features = extractor.extract(log)

        assert features["hresult_unique_count"] == 1.0
        assert features["error_name_unique_count"] == 1.0
        assert features["hresult_concentration"] > 0.8  # High concentration

    def test_anomaly_score_calculation(self, extractor: WindowsFeatureExtractor):
        """Test composite anomaly score"""
        parser = WindowsParser()

        # Add errors to trigger anomaly detection
        for _ in range(6):
            log = self.create_log_internal(
                parser.parse(WindowsLogSamples.parse_error_cascade_1())
            )
            features = extractor.extract(log)

        # Should have anomaly indicators
        assert features["anomaly_score"] > 0.0
        assert features["anomaly_error_cascade"] == 1.0

    def test_feature_vector_completeness(self, extractor: WindowsFeatureExtractor):
        """Test that feature vector contains expected keys"""
        log = self.create_log_internal(
            WindowsParser().parse(WindowsLogSamples.service_start())
        )
        features = extractor.extract(log)

        # Check major feature categories
        assert "event_count_total" in features
        assert "error_count_total" in features
        assert "error_rate" in features
        assert "transaction_count_total" in features
        assert "package_count_unique" in features
        assert "service_state" in features
        assert "session_count_active" in features
        assert "anomaly_score" in features

    def test_singleton_state_preservation(self):
        """Test that extractor singleton preserves state"""
        ext1 = get_windows_feature_extractor()
        ext2 = get_windows_feature_extractor()

        # Both should be same instance
        assert ext1 is ext2

        # State should be preserved
        parser = WindowsParser()
        log = self.create_log_internal(
            parser.parse(WindowsLogSamples.service_start())
        )
        features1 = ext1.extract(log)
        features2 = ext2.extract(log)

        # State should accumulate
        assert features2["event_count_total"] == 2.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestParserFeatureIntegration:
    """Test integration between parser and feature extractor"""

    def test_end_to_end_pipeline(self):
        """Test complete parsing and feature extraction pipeline"""
        parser = WindowsParser()
        extractor = WindowsFeatureExtractor()
        extractor.reset_state()

        log_lines = [
            WindowsLogSamples.service_start(),
            WindowsLogSamples.transaction_create_success(),
            WindowsLogSamples.package_applicability(),
            WindowsLogSamples.session_initialized(),
        ]

        for log_line in log_lines:
            # Parse
            parsed = parser.parse(log_line)
            assert parsed["parsed_successfully"] is True

            # Create log internal
            log = LogInternal(
                message=log_line,
                server_type=ServerType.WINDOWS,
                timestamp=datetime.now().isoformat(),
            )
            log.metadata = {"parsed": parsed}

            # Extract features
            features = extractor.extract(log)
            assert isinstance(features, dict)
            assert "anomaly_score" in features

    def test_error_cascade_detection_integration(self):
        """Test error cascade detection in full pipeline"""
        parser = WindowsParser()
        extractor = WindowsFeatureExtractor()
        extractor.reset_state()

        # Simulate error cascade
        error_logs = [
            WindowsLogSamples.manifest_error(),
            WindowsLogSamples.parse_error_cascade_1(),
            WindowsLogSamples.parse_error_cascade_2(),
            WindowsLogSamples.parse_error_cascade_3(),
            WindowsLogSamples.package_error(),
        ]

        for log_line in error_logs:
            parsed = parser.parse(log_line)
            log = LogInternal(
                message=log_line,
                server_type=ServerType.WINDOWS,
                timestamp=datetime.now().isoformat(),
            )
            log.metadata = {"parsed": parsed}
            features = extractor.extract(log)

        # Final features should show anomaly
        assert features["error_count_total"] == 5.0
        assert features["anomaly_error_cascade"] == 1.0
        assert features["anomaly_score"] > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
