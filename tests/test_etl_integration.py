"""
Tests for ETL pipeline integration and error handling.
Tests data pipeline triggers, error handling, and retry logic.
"""
import pytest
import asyncio
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
import json

from app.core.synapse_integration import (
    SynapseDataExporter, SynapsePipelineTrigger, ETLOrchestrator
)
from app.core.scheduler import ETLScheduler
from app.core.etl_error_handling import (
    ETLError, ETLErrorType, ETLErrorSeverity, ETLErrorHandler, RetryConfig
)


class TestSynapseDataExporter:
    """Test Azure Synapse data exporter."""
    
    @pytest.fixture
    def data_exporter(self):
        """Data exporter instance."""
        return SynapseDataExporter()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for export testing."""
        return {
            "appointments": [
                {
                    "appointment_id": str(uuid4()),
                    "patient_id": str(uuid4()),
                    "doctor_id": str(uuid4()),
                    "appointment_datetime": "2024-01-15T10:00:00",
                    "duration": 30,
                    "status": "Completed"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_export_to_json(self, data_exporter, sample_data):
        """Test JSON export functionality."""
        filename = "test_export.json"
        
        with patch('aiofiles.open', create=True) as mock_open, \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            
            mock_file = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file
            
            result = await data_exporter.export_to_json(sample_data, filename)
            
            assert result.endswith(filename)
            mock_file.write.assert_called_once()
            mock_mkdir.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_parquet(self, data_exporter):
        """Test Parquet export functionality."""
        sample_list_data = [
            {
                "id": str(uuid4()),
                "name": "Test Record",
                "created_at": "2024-01-15T10:00:00"
            }
        ]
        
        filename = "test_export.parquet"
        
        with patch('pandas.DataFrame') as mock_df, \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            
            mock_df_instance = Mock()
            mock_df.return_value = mock_df_instance
            
            result = await data_exporter.export_to_parquet(sample_list_data, filename)
            
            assert result.endswith(filename)
            mock_df.assert_called_once_with(sample_list_data)
            mock_df_instance.to_parquet.assert_called_once()
            mock_mkdir.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_to_blob_storage(self, data_exporter):
        """Test blob storage upload."""
        if not data_exporter.blob_service_client:
            # Skip test if blob client not configured
            pytest.skip("Blob storage client not configured")
        
        local_file_path = "/tmp/test_file.json"
        blob_name = "test_blob.json"
        
        with patch('builtins.open', create=True) as mock_open, \
             patch.object(data_exporter.blob_service_client, 'get_blob_client') as mock_get_client:
            
            mock_blob_client = Mock()
            mock_get_client.return_value = mock_blob_client
            mock_open.return_value.__enter__.return_value = Mock()
            
            result = await data_exporter.upload_to_blob_storage(local_file_path, blob_name)
            
            assert blob_name in result
            mock_blob_client.upload_blob.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_and_upload_data(self, data_exporter, sample_data):
        """Test complete export and upload process."""
        with patch.object(data_exporter, 'export_to_parquet') as mock_export, \
             patch.object(data_exporter, 'upload_to_blob_storage') as mock_upload:
            
            mock_export.return_value = "/tmp/test_file.parquet"
            mock_upload.return_value = "https://storage.blob.core.windows.net/container/test_file.parquet"
            
            result = await data_exporter.export_and_upload_data(
                sample_data, "test_data", "parquet"
            )
            
            assert "appointments" in result
            assert result["appointments"].startswith("https://")
            mock_export.assert_called_once()
            mock_upload.assert_called_once()
    
    def test_serialize_datetime_objects(self, data_exporter):
        """Test datetime serialization."""
        test_data = {
            "datetime_field": datetime(2024, 1, 15, 10, 0, 0),
            "date_field": date(2024, 1, 15),
            "string_field": "test",
            "nested": {
                "datetime_nested": datetime(2024, 1, 15, 12, 0, 0)
            },
            "list_field": [datetime(2024, 1, 15, 14, 0, 0), "string"]
        }
        
        result = data_exporter._serialize_datetime_objects(test_data)
        
        assert result["datetime_field"] == "2024-01-15T10:00:00"
        assert result["date_field"] == "2024-01-15"
        assert result["string_field"] == "test"
        assert result["nested"]["datetime_nested"] == "2024-01-15T12:00:00"
        assert result["list_field"][0] == "2024-01-15T14:00:00"
        assert result["list_field"][1] == "string"


class TestSynapsePipelineTrigger:
    """Test Azure Synapse pipeline trigger."""
    
    @pytest.fixture
    def pipeline_trigger(self):
        """Pipeline trigger instance."""
        return SynapsePipelineTrigger()
    
    @pytest.mark.asyncio
    async def test_trigger_pipeline_without_client(self, pipeline_trigger):
        """Test pipeline trigger without ADF client (simulation mode)."""
        pipeline_name = "test_pipeline"
        parameters = {"param1": "value1"}
        
        result = await pipeline_trigger.trigger_pipeline(pipeline_name, parameters)
        
        assert result["status"] == "simulated"
        assert result["pipeline_name"] == pipeline_name
        assert result["parameters"] == parameters
        assert "run_id" in result
    
    @pytest.mark.asyncio
    async def test_trigger_pipeline_with_client(self, pipeline_trigger):
        """Test pipeline trigger with ADF client."""
        if not pipeline_trigger.adf_client:
            # Mock ADF client for testing
            pipeline_trigger.adf_client = Mock()
            pipeline_trigger.resource_group_name = "test_rg"
            pipeline_trigger.data_factory_name = "test_df"
        
        mock_response = Mock()
        mock_response.run_id = "test_run_id_123"
        pipeline_trigger.adf_client.pipeline_runs.create_run.return_value = mock_response
        
        pipeline_name = "test_pipeline"
        parameters = {"param1": "value1"}
        
        result = await pipeline_trigger.trigger_pipeline(pipeline_name, parameters)
        
        assert result["status"] == "triggered"
        assert result["run_id"] == "test_run_id_123"
        assert result["pipeline_name"] == pipeline_name
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status_without_client(self, pipeline_trigger):
        """Test getting pipeline status without ADF client."""
        run_id = "test_run_id"
        
        result = await pipeline_trigger.get_pipeline_status(run_id)
        
        assert result["status"] == "simulated"
        assert result["run_id"] == run_id
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status_with_client(self, pipeline_trigger):
        """Test getting pipeline status with ADF client."""
        if not pipeline_trigger.adf_client:
            # Mock ADF client for testing
            pipeline_trigger.adf_client = Mock()
            pipeline_trigger.resource_group_name = "test_rg"
            pipeline_trigger.data_factory_name = "test_df"
        
        mock_run_status = Mock()
        mock_run_status.status = "Succeeded"
        mock_run_status.pipeline_name = "test_pipeline"
        mock_run_status.run_start = datetime(2024, 1, 15, 10, 0, 0)
        mock_run_status.run_end = datetime(2024, 1, 15, 10, 5, 0)
        mock_run_status.message = "Pipeline completed successfully"
        
        pipeline_trigger.adf_client.pipeline_runs.get.return_value = mock_run_status
        
        run_id = "test_run_id"
        result = await pipeline_trigger.get_pipeline_status(run_id)
        
        assert result["status"] == "Succeeded"
        assert result["pipeline_name"] == "test_pipeline"
        assert result["run_id"] == run_id


class TestETLOrchestrator:
    """Test ETL orchestrator."""
    
    @pytest.fixture
    def etl_orchestrator(self):
        """ETL orchestrator instance."""
        return ETLOrchestrator()
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Mock analytics service."""
        service = Mock()
        service.export_data_for_synapse.return_value = {
            "appointments": [{"id": "test"}]
        }
        return service
    
    @pytest.mark.asyncio
    async def test_run_full_etl(self, etl_orchestrator, mock_analytics_service):
        """Test full ETL process."""
        with patch.object(etl_orchestrator.data_exporter, 'export_and_upload_data') as mock_export, \
             patch.object(etl_orchestrator.pipeline_trigger, 'trigger_pipeline') as mock_trigger:
            
            mock_export.return_value = {"table1": "file1.parquet"}
            mock_trigger.return_value = {"status": "triggered", "run_id": "test_run"}
            
            result = await etl_orchestrator.run_full_etl(
                mock_analytics_service,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )
            
            assert result["status"] == "completed"
            assert "data_exports" in result
            assert "pipeline_runs" in result
            assert len(result["data_exports"]) == 3  # appointments, resources, doctors
    
    @pytest.mark.asyncio
    async def test_run_incremental_etl(self, etl_orchestrator, mock_analytics_service):
        """Test incremental ETL process."""
        with patch.object(etl_orchestrator.data_exporter, 'export_and_upload_data') as mock_export, \
             patch.object(etl_orchestrator.pipeline_trigger, 'trigger_pipeline') as mock_trigger:
            
            mock_export.return_value = {"table1": "file1.parquet"}
            mock_trigger.return_value = {"status": "triggered", "run_id": "test_run"}
            
            result = await etl_orchestrator.run_incremental_etl(
                mock_analytics_service,
                data_type="appointments",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )
            
            assert result["status"] == "completed"
            assert result["data_type"] == "appointments"
            assert "data_exports" in result
            assert "pipeline_run" in result


class TestETLScheduler:
    """Test ETL scheduler."""
    
    @pytest.fixture
    def etl_scheduler(self):
        """ETL scheduler instance."""
        return ETLScheduler()
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, etl_scheduler):
        """Test scheduler start and stop."""
        await etl_scheduler.start()
        assert etl_scheduler.scheduler.running
        
        await etl_scheduler.stop()
        assert not etl_scheduler.scheduler.running
    
    @pytest.mark.asyncio
    async def test_trigger_manual_etl(self, etl_scheduler):
        """Test manual ETL trigger."""
        with patch.object(etl_scheduler.etl_orchestrator, 'run_incremental_etl') as mock_etl, \
             patch.object(etl_scheduler, '_get_db_session'):
            
            mock_etl.return_value = {
                "status": "completed",
                "start_time": "2024-01-15T10:00:00",
                "end_time": "2024-01-15T10:05:00"
            }
            
            result = await etl_scheduler.trigger_manual_etl(
                data_type="appointments",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )
            
            assert result["status"] == "completed"
            assert len(etl_scheduler.job_history) > 0
    
    def test_get_scheduled_jobs(self, etl_scheduler):
        """Test getting scheduled jobs."""
        # Add a mock job
        etl_scheduler.scheduler.add_job(
            func=lambda: None,
            trigger='interval',
            seconds=60,
            id='test_job',
            name='Test Job'
        )
        
        jobs = etl_scheduler.get_scheduled_jobs()
        
        assert len(jobs) > 0
        assert any(job["id"] == "test_job" for job in jobs)
    
    def test_job_history_management(self, etl_scheduler):
        """Test job history management."""
        # Add multiple job entries
        for i in range(150):  # More than max_history_size
            etl_scheduler._add_job_to_history({
                "job_id": f"job_{i}",
                "status": "completed"
            })
        
        # History should be limited
        assert len(etl_scheduler.job_history) <= etl_scheduler.max_history_size


class TestETLErrorHandling:
    """Test ETL error handling and retry logic."""
    
    @pytest.fixture
    def error_handler(self):
        """Error handler instance."""
        return ETLErrorHandler()
    
    def test_classify_error(self, error_handler):
        """Test error classification."""
        # Test different error types
        test_cases = [
            (Exception("Database connection failed"), ETLErrorType.DATABASE_CONNECTION),
            (Exception("Azure service unavailable"), ETLErrorType.AZURE_SERVICE),
            (Exception("Request timed out"), ETLErrorType.NETWORK_TIMEOUT),
            (Exception("Pipeline execution failed"), ETLErrorType.PIPELINE_EXECUTION),
            (Exception("Data validation error"), ETLErrorType.DATA_VALIDATION),
            (Exception("Authentication failed"), ETLErrorType.AUTHENTICATION),
            (Exception("Rate limit exceeded"), ETLErrorType.RESOURCE_LIMIT),
            (Exception("Unknown error"), ETLErrorType.UNKNOWN)
        ]
        
        for error, expected_type in test_cases:
            result = error_handler.classify_error(error)
            assert result == expected_type
    
    def test_determine_severity(self, error_handler):
        """Test error severity determination."""
        # Test severity mapping
        severity_tests = [
            (ETLErrorType.AUTHENTICATION, ETLErrorSeverity.CRITICAL),
            (ETLErrorType.DATABASE_CONNECTION, ETLErrorSeverity.HIGH),
            (ETLErrorType.DATA_VALIDATION, ETLErrorSeverity.LOW),
            (ETLErrorType.NETWORK_TIMEOUT, ETLErrorSeverity.MEDIUM)
        ]
        
        for error_type, expected_severity in severity_tests:
            result = error_handler.determine_severity(error_type, Exception("test"))
            assert result == expected_severity
    
    def test_calculate_delay(self, error_handler):
        """Test retry delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=10.0)
        
        # Test exponential backoff
        delay1 = error_handler.calculate_delay(1, config)
        delay2 = error_handler.calculate_delay(2, config)
        delay3 = error_handler.calculate_delay(3, config)
        
        assert delay1 >= 0.5  # With jitter, should be at least half base delay
        assert delay2 > delay1  # Should increase
        assert delay3 <= 10.0  # Should not exceed max delay
    
    def test_should_retry(self, error_handler):
        """Test retry decision logic."""
        # Test with different error types and attempts
        assert error_handler.should_retry(ETLErrorType.DATABASE_CONNECTION, 1) == True
        assert error_handler.should_retry(ETLErrorType.DATABASE_CONNECTION, 5) == False
        assert error_handler.should_retry(ETLErrorType.DATA_VALIDATION, 1) == False  # No retry for validation
    
    @pytest.mark.asyncio
    async def test_handle_error_with_retry_success(self, error_handler):
        """Test successful retry after initial failure."""
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Database connection failed")
            return "success"
        
        result = await error_handler.handle_error_with_retry(failing_function)
        
        assert result == "success"
        assert call_count == 2
        assert len(error_handler.error_history) == 1
    
    @pytest.mark.asyncio
    async def test_handle_error_with_retry_max_attempts(self, error_handler):
        """Test max retry attempts exceeded."""
        async def always_failing_function():
            raise Exception("Database connection failed")
        
        with pytest.raises(ETLError):
            await error_handler.handle_error_with_retry(
                always_failing_function,
                custom_retry_config=RetryConfig(max_attempts=2, base_delay=0.1)
            )
        
        assert len(error_handler.error_history) == 2
    
    def test_get_error_statistics(self, error_handler):
        """Test error statistics generation."""
        # Add some test errors
        test_errors = [
            ETLError("DB error 1", ETLErrorType.DATABASE_CONNECTION, ETLErrorSeverity.HIGH),
            ETLError("DB error 2", ETLErrorType.DATABASE_CONNECTION, ETLErrorSeverity.HIGH),
            ETLError("Auth error", ETLErrorType.AUTHENTICATION, ETLErrorSeverity.CRITICAL),
            ETLError("Validation error", ETLErrorType.DATA_VALIDATION, ETLErrorSeverity.LOW)
        ]
        
        for error in test_errors:
            error_handler.log_error(error)
        
        stats = error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 4
        assert stats["by_type"]["database_connection"] == 2
        assert stats["by_type"]["authentication"] == 1
        assert stats["by_severity"]["high"] == 2
        assert stats["by_severity"]["critical"] == 1
        assert len(stats["recent_critical"]) == 1


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_etl_workflow(self):
        """Test complete ETL workflow from trigger to completion."""
        # This would be a comprehensive integration test
        # For now, we'll test the main components work together
        
        orchestrator = ETLOrchestrator()
        mock_analytics_service = Mock()
        mock_analytics_service.export_data_for_synapse.return_value = {
            "appointments": [{"id": "test"}]
        }
        
        with patch.object(orchestrator.data_exporter, 'export_and_upload_data') as mock_export, \
             patch.object(orchestrator.pipeline_trigger, 'trigger_pipeline') as mock_trigger:
            
            mock_export.return_value = {"appointments": "test_file.parquet"}
            mock_trigger.return_value = {"status": "triggered", "run_id": "test_run"}
            
            result = await orchestrator.run_incremental_etl(
                mock_analytics_service,
                "appointments",
                date(2024, 1, 1),
                date(2024, 1, 31)
            )
            
            assert result["status"] == "completed"
            assert "data_exports" in result
            assert "pipeline_run" in result
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in ETL workflow."""
        error_handler = ETLErrorHandler()
        
        # Simulate a function that fails twice then succeeds
        call_count = 0
        
        async def unreliable_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary Azure service error")
            return {"status": "success"}
        
        result = await error_handler.handle_error_with_retry(
            unreliable_function,
            custom_retry_config=RetryConfig(max_attempts=3, base_delay=0.1)
        )
        
        assert result["status"] == "success"
        assert call_count == 3
        assert len(error_handler.error_history) == 2  # Two failed attempts logged


if __name__ == "__main__":
    pytest.main([__file__])