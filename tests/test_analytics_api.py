"""
Tests for analytics API endpoints.
Tests endpoint responses, calculations, and authorization.
"""
import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models.user import User, UserRole
from app.models.analytics import (
    DoctorUtilizationReport, AppointmentTrendsReport, ResourceUsageReport
)


class TestAnalyticsEndpoints:
    """Test analytics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Mock admin user for testing."""
        user = Mock(spec=User)
        user.user_id = uuid4()
        user.username = "admin"
        user.role = UserRole.ADMIN
        user.is_active = True
        return user
    
    @pytest.fixture
    def doctor_user(self):
        """Mock doctor user for testing."""
        user = Mock(spec=User)
        user.user_id = uuid4()
        user.username = "doctor"
        user.role = UserRole.DOCTOR
        user.is_active = True
        return user
    
    @pytest.fixture
    def staff_user(self):
        """Mock staff user for testing."""
        user = Mock(spec=User)
        user.user_id = uuid4()
        user.username = "staff"
        user.role = UserRole.STAFF
        user.is_active = True
        return user
    
    @pytest.fixture
    def patient_user(self):
        """Mock patient user for testing."""
        user = Mock(spec=User)
        user.user_id = uuid4()
        user.username = "patient"
        user.role = UserRole.PATIENT
        user.is_active = True
        return user


class TestDoctorUtilizationEndpoint:
    """Test doctor utilization endpoint."""
    
    def test_get_doctor_utilization_success(self, client, admin_user):
        """Test successful doctor utilization request."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service response
            mock_report = DoctorUtilizationReport(
                doctor_id=uuid4(),
                doctor_name="Dr. John Smith",
                specialization="Cardiology",
                department="Cardiology",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                total_appointments=20,
                completed_appointments=18,
                cancelled_appointments=1,
                no_show_appointments=1,
                completion_rate=0.9,
                no_show_rate=0.05,
                average_appointments_per_day=0.65,
                total_scheduled_hours=10.0,
                actual_worked_hours=9.0,
                utilization_rate=0.9
            )
            
            mock_service.return_value.generate_doctor_utilization_report.return_value = [mock_report]
            
            response = client.get(
                "/api/v1/analytics/doctor-utilization",
                params={
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["doctor_name"] == "Dr. John Smith"
            assert data[0]["specialization"] == "Cardiology"
            assert data[0]["completion_rate"] == 0.9
    
    def test_get_doctor_utilization_unauthorized(self, client, patient_user):
        """Test unauthorized access to doctor utilization."""
        with patch('app.core.dependencies.get_current_user', return_value=patient_user):
            response = client.get("/api/v1/analytics/doctor-utilization")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_doctor_utilization_invalid_date_range(self, client, admin_user):
        """Test invalid date range."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user):
            response = client.get(
                "/api/v1/analytics/doctor-utilization",
                params={
                    "start_date": "2024-01-31",
                    "end_date": "2024-01-01"  # End before start
                }
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Start date must be before or equal to end date" in response.json()["detail"]
    
    def test_get_doctor_utilization_date_range_too_large(self, client, admin_user):
        """Test date range exceeding limit."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user):
            response = client.get(
                "/api/v1/analytics/doctor-utilization",
                params={
                    "start_date": "2023-01-01",
                    "end_date": "2024-12-31"  # More than 365 days
                }
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Date range cannot exceed 365 days" in response.json()["detail"]
    
    def test_get_doctor_utilization_specific_doctor(self, client, doctor_user):
        """Test getting utilization for specific doctor."""
        with patch('app.core.dependencies.get_current_user', return_value=doctor_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            doctor_id = uuid4()
            mock_report = DoctorUtilizationReport(
                doctor_id=doctor_id,
                doctor_name="Dr. Jane Doe",
                specialization="Neurology",
                department="Neurology",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                total_appointments=15,
                completed_appointments=14,
                cancelled_appointments=0,
                no_show_appointments=1,
                completion_rate=0.93,
                no_show_rate=0.07,
                average_appointments_per_day=0.48,
                total_scheduled_hours=7.5,
                actual_worked_hours=7.0,
                utilization_rate=0.93
            )
            
            mock_service.return_value.generate_doctor_utilization_report.return_value = [mock_report]
            
            response = client.get(
                "/api/v1/analytics/doctor-utilization",
                params={"doctor_id": str(doctor_id)}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["doctor_id"] == str(doctor_id)


class TestAppointmentTrendsEndpoint:
    """Test appointment trends endpoint."""
    
    def test_get_appointment_trends_success(self, client, staff_user):
        """Test successful appointment trends request."""
        with patch('app.core.dependencies.get_current_user', return_value=staff_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service response
            mock_report = AppointmentTrendsReport(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                total_appointments=100,
                appointments_by_status={"Completed": 80, "Cancelled": 15, "No-Show": 5},
                appointments_by_specialization={"Cardiology": 40, "Neurology": 30, "Orthopedics": 30},
                appointments_by_day_of_week={"Monday": 20, "Tuesday": 18, "Wednesday": 16, "Thursday": 22, "Friday": 24},
                appointments_by_time_period={"Morning": 40, "Afternoon": 35, "Evening": 25, "Night": 0},
                average_wait_time=15.5,
                peak_hours=[9, 10, 14, 15],
                busiest_days=["Friday", "Thursday", "Monday"]
            )
            
            mock_service.return_value.generate_appointment_trends_report.return_value = mock_report
            
            response = client.get("/api/v1/analytics/appointment-trends")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_appointments"] == 100
            assert "Completed" in data["appointments_by_status"]
            assert "Cardiology" in data["appointments_by_specialization"]
            assert len(data["peak_hours"]) == 4
    
    def test_get_appointment_trends_unauthorized(self, client, patient_user):
        """Test unauthorized access to appointment trends."""
        with patch('app.core.dependencies.get_current_user', return_value=patient_user):
            response = client.get("/api/v1/analytics/appointment-trends")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN


class TestResourceUsageEndpoint:
    """Test resource usage endpoint."""
    
    def test_get_resource_usage_success(self, client, admin_user):
        """Test successful resource usage request."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service response
            mock_report = ResourceUsageReport(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                resources_by_type={"Room": 20, "Equipment": 15, "Bed": 50},
                total_utilization_hours=2040.0,
                average_occupancy_rate=0.68,
                utilization_by_resource_type={"Room": 0.75, "Equipment": 0.60, "Bed": 0.70},
                peak_usage_hours=[9, 10, 11, 14, 15, 16],
                underutilized_resources=[
                    {"resource_id": "room-5", "resource_name": "Operating Room 5", "utilization_rate": 0.25}
                ],
                overutilized_resources=[
                    {"resource_id": "bed-3", "resource_name": "ICU Bed 3", "utilization_rate": 0.95}
                ],
                maintenance_hours=120.0,
                availability_rate=0.92
            )
            
            mock_service.return_value.generate_resource_usage_report.return_value = mock_report
            
            response = client.get("/api/v1/analytics/resource-usage")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["average_occupancy_rate"] == 0.68
            assert "Room" in data["resources_by_type"]
            assert len(data["peak_usage_hours"]) == 6
            assert len(data["underutilized_resources"]) == 1
    
    def test_get_resource_usage_filtered_by_type(self, client, staff_user):
        """Test resource usage filtered by type."""
        with patch('app.core.dependencies.get_current_user', return_value=staff_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            mock_report = ResourceUsageReport(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                resources_by_type={"Room": 20, "Equipment": 15, "Bed": 50},
                total_utilization_hours=2040.0,
                average_occupancy_rate=0.68,
                utilization_by_resource_type={"Room": 0.75, "Equipment": 0.60, "Bed": 0.70},
                peak_usage_hours=[9, 10, 11, 14, 15, 16],
                underutilized_resources=[],
                overutilized_resources=[],
                maintenance_hours=120.0,
                availability_rate=0.92
            )
            
            mock_service.return_value.generate_resource_usage_report.return_value = mock_report
            
            response = client.get(
                "/api/v1/analytics/resource-usage",
                params={"resource_type": "Room"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            # Should only contain Room data after filtering
            assert "Room" in data["resources_by_type"]
            assert "Room" in data["utilization_by_resource_type"]
    
    def test_get_resource_usage_invalid_type(self, client, admin_user):
        """Test invalid resource type."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user):
            response = client.get(
                "/api/v1/analytics/resource-usage",
                params={"resource_type": "InvalidType"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid resource type" in response.json()["detail"]
    
    def test_get_resource_usage_doctor_unauthorized(self, client, doctor_user):
        """Test doctor cannot access resource usage (admin/staff only)."""
        with patch('app.core.dependencies.get_current_user', return_value=doctor_user):
            response = client.get("/api/v1/analytics/resource-usage")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDashboardSummaryEndpoint:
    """Test dashboard summary endpoint."""
    
    def test_get_dashboard_summary_success(self, client, admin_user):
        """Test successful dashboard summary request."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service responses
            mock_doctor_reports = [
                DoctorUtilizationReport(
                    doctor_id=uuid4(),
                    doctor_name="Dr. Smith",
                    specialization="Cardiology",
                    period_start=date.today() - timedelta(days=7),
                    period_end=date.today(),
                    total_appointments=10,
                    completed_appointments=9,
                    cancelled_appointments=1,
                    no_show_appointments=0,
                    completion_rate=0.9,
                    no_show_rate=0.0,
                    average_appointments_per_day=1.4,
                    total_scheduled_hours=5.0,
                    actual_worked_hours=4.5,
                    utilization_rate=0.9
                )
            ]
            
            mock_resource_report = ResourceUsageReport(
                period_start=date.today() - timedelta(days=7),
                period_end=date.today(),
                resources_by_type={"Room": 10, "Equipment": 5, "Bed": 20},
                total_utilization_hours=840.0,
                average_occupancy_rate=0.65,
                utilization_by_resource_type={"Room": 0.70, "Equipment": 0.60, "Bed": 0.65},
                peak_usage_hours=[9, 10, 14, 15],
                underutilized_resources=[],
                overutilized_resources=[],
                maintenance_hours=40.0,
                availability_rate=0.95
            )
            
            mock_service.return_value.generate_doctor_utilization_report.return_value = mock_doctor_reports
            mock_service.return_value.generate_resource_usage_report.return_value = mock_resource_report
            
            response = client.get("/api/v1/analytics/dashboard-summary")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "date_generated" in data
            assert "period" in data
            assert "appointments" in data
            assert "doctors" in data
            assert "resources" in data
            assert "alerts" in data
            assert data["doctors"]["total_active"] == 1
            assert data["resources"]["total_resources"] == 35


class TestExportDataEndpoint:
    """Test data export endpoint."""
    
    def test_export_analytics_data_success(self, client, admin_user):
        """Test successful data export."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service response
            mock_export_data = {
                "appointments": [
                    {
                        "appointment_id": str(uuid4()),
                        "patient_id": str(uuid4()),
                        "doctor_id": str(uuid4()),
                        "appointment_datetime": "2024-01-15T10:00:00",
                        "status": "Completed"
                    }
                ]
            }
            
            mock_service.return_value.export_data_for_synapse.return_value = mock_export_data
            
            response = client.post(
                "/api/v1/analytics/export-data",
                params={
                    "data_type": "appointments",
                    "format": "json"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "export_info" in data
            assert "data" in data
            assert data["export_info"]["data_type"] == "appointments"
            assert "appointments" in data["data"]
    
    def test_export_analytics_data_unauthorized(self, client, staff_user):
        """Test unauthorized data export (admin only)."""
        with patch('app.core.dependencies.get_current_user', return_value=staff_user):
            response = client.post(
                "/api/v1/analytics/export-data",
                params={"data_type": "appointments"}
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_export_analytics_data_invalid_type(self, client, admin_user):
        """Test invalid data type for export."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/v1/analytics/export-data",
                params={"data_type": "invalid_type"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid data type" in response.json()["detail"]


class TestETLManagementEndpoints:
    """Test ETL management endpoints."""
    
    def test_trigger_etl_pipeline_success(self, client, admin_user):
        """Test successful ETL pipeline trigger."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.core.scheduler.etl_scheduler') as mock_scheduler:
            
            # Mock scheduler response
            mock_result = {
                "job_id": "manual_etl_appointments_20240115_120000",
                "status": "completed",
                "start_time": "2024-01-15T12:00:00",
                "end_time": "2024-01-15T12:05:00",
                "data_exports": {"appointments": ["file1.parquet"]},
                "pipeline_runs": {"appointments": {"status": "success"}}
            }
            
            mock_scheduler.trigger_manual_etl.return_value = mock_result
            
            response = client.post(
                "/api/v1/analytics/trigger-etl",
                params={
                    "data_type": "appointments",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "completed"
            assert "job_id" in data
    
    def test_trigger_etl_pipeline_unauthorized(self, client, doctor_user):
        """Test unauthorized ETL trigger (admin only)."""
        with patch('app.core.dependencies.get_current_user', return_value=doctor_user):
            response = client.post(
                "/api/v1/analytics/trigger-etl",
                params={
                    "data_type": "appointments",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_etl_status_success(self, client, staff_user):
        """Test successful ETL status request."""
        with patch('app.core.dependencies.get_current_user', return_value=staff_user), \
             patch('app.core.scheduler.etl_scheduler') as mock_scheduler:
            
            # Mock scheduler responses
            mock_history = [
                {
                    "job_id": "daily_full_etl_20240115",
                    "job_type": "daily_full_etl",
                    "status": "completed",
                    "start_time": "2024-01-15T02:00:00",
                    "end_time": "2024-01-15T02:15:00"
                }
            ]
            
            mock_scheduled_jobs = [
                {
                    "id": "daily_full_etl",
                    "name": "Daily Full ETL",
                    "next_run_time": "2024-01-16T02:00:00",
                    "trigger": "cron[hour=2, minute=0]"
                }
            ]
            
            mock_scheduler.get_job_history.return_value = mock_history
            mock_scheduler.get_scheduled_jobs.return_value = mock_scheduled_jobs
            
            response = client.get("/api/v1/analytics/etl-status")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "scheduled_jobs" in data
            assert "job_history" in data
            assert len(data["scheduled_jobs"]) == 1
            assert len(data["job_history"]) == 1
    
    def test_manage_etl_job_pause(self, client, admin_user):
        """Test pausing ETL job."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.core.scheduler.etl_scheduler') as mock_scheduler:
            
            mock_scheduler.pause_job.return_value = True
            
            response = client.post("/api/v1/analytics/etl-job/daily_full_etl/pause")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "paused successfully" in data["message"]
            assert data["job_id"] == "daily_full_etl"
            assert data["action"] == "pause"


class TestErrorHandling:
    """Test error handling in analytics endpoints."""
    
    def test_service_error_handling(self, client, admin_user):
        """Test handling of service errors."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user), \
             patch('app.services.analytics.AnalyticsService') as mock_service:
            
            # Mock service error
            mock_service.return_value.generate_doctor_utilization_report.side_effect = Exception("Database error")
            
            response = client.get("/api/v1/analytics/doctor-utilization")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Error generating doctor utilization report" in response.json()["detail"]
    
    def test_invalid_date_format(self, client, admin_user):
        """Test invalid date format handling."""
        with patch('app.core.dependencies.get_current_user', return_value=admin_user):
            response = client.get(
                "/api/v1/analytics/doctor-utilization",
                params={
                    "start_date": "invalid-date",
                    "end_date": "2024-01-31"
                }
            )
            
            # FastAPI should return 422 for validation errors
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


if __name__ == "__main__":
    pytest.main([__file__])