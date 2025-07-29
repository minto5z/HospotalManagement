"""
Tests for analytics service functionality.
Tests data transformation, aggregation logic, and export functions.
"""
import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.analytics import AnalyticsService
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.hospital_resource import HospitalResource
from app.models.analytics import (
    AppointmentExport, ResourceUtilizationExport, DoctorPerformanceExport,
    DoctorUtilizationReport, AppointmentTrendsReport, ResourceUsageReport,
    PatientAgeGroup, TimeSlotAnalysis, DateAnalysis
)


class TestAnalyticsService:
    """Test analytics service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def analytics_service(self, mock_db):
        """Analytics service instance with mocked database."""
        return AnalyticsService(mock_db)
    
    @pytest.fixture
    def sample_patient(self):
        """Sample patient for testing."""
        return Patient(
            patient_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 1),
            gender="Male",
            phone_number="123-456-7890",
            email="john.doe@example.com"
        )
    
    @pytest.fixture
    def sample_doctor(self):
        """Sample doctor for testing."""
        return Doctor(
            doctor_id=uuid4(),
            first_name="Dr. Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD12345",
            department="Cardiology"
        )
    
    @pytest.fixture
    def sample_appointment(self, sample_patient, sample_doctor):
        """Sample appointment for testing."""
        return Appointment(
            appointment_id=uuid4(),
            patient_id=sample_patient.patient_id,
            doctor_id=sample_doctor.doctor_id,
            appointment_datetime=datetime(2024, 1, 15, 10, 0),
            duration=30,
            status="Completed",
            notes="Regular checkup"
        )
    
    @pytest.fixture
    def sample_resource(self):
        """Sample hospital resource for testing."""
        return HospitalResource(
            resource_id=uuid4(),
            resource_name="Operating Room 1",
            resource_type="Room",
            location="Floor 2",
            status="Available"
        )


class TestDataTransformation:
    """Test data transformation methods."""
    
    def test_transform_appointments_for_analytics(self, analytics_service, mock_db, sample_patient, sample_doctor, sample_appointment):
        """Test appointment data transformation."""
        # Mock database query results
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = [
            (sample_appointment, sample_patient, sample_doctor)
        ]
        
        # Test transformation
        result = analytics_service.transform_appointments_for_analytics(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert len(result) == 1
        assert isinstance(result[0], AppointmentExport)
        assert result[0].appointment_id == sample_appointment.appointment_id
        assert result[0].patient_id == sample_appointment.patient_id
        assert result[0].doctor_id == sample_appointment.doctor_id
        assert result[0].doctor_specialization == sample_doctor.specialization
        assert result[0].patient_age_group in ["0-18", "19-35", "36-50", "51-65", "65+"]
    
    def test_transform_resource_utilization_for_analytics(self, analytics_service, mock_db, sample_resource):
        """Test resource utilization data transformation."""
        # Mock database query results
        mock_db.query.return_value.all.return_value = [sample_resource]
        
        # Test transformation
        result = analytics_service.transform_resource_utilization_for_analytics(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2)
        )
        
        assert len(result) == 2  # 2 days of data
        assert all(isinstance(item, ResourceUtilizationExport) for item in result)
        assert result[0].resource_id == sample_resource.resource_id
        assert result[0].resource_type == sample_resource.resource_type
        assert 0 <= result[0].occupancy_rate <= 1
        assert 0 <= result[0].availability_rate <= 1
    
    def test_transform_doctor_performance_for_analytics(self, analytics_service, mock_db):
        """Test doctor performance data transformation."""
        # Mock database query results
        mock_result = Mock()
        mock_result.doctor_id = uuid4()
        mock_result.first_name = "Dr. Jane"
        mock_result.last_name = "Smith"
        mock_result.specialization = "Cardiology"
        mock_result.department = "Cardiology"
        mock_result.appointment_date = date(2024, 1, 15)
        mock_result.total_appointments = 10
        mock_result.completed_appointments = 8
        mock_result.cancelled_appointments = 1
        mock_result.no_show_appointments = 1
        mock_result.total_scheduled_minutes = 300
        
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_result]
        
        # Test transformation
        result = analytics_service.transform_doctor_performance_for_analytics(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert len(result) == 1
        assert isinstance(result[0], DoctorPerformanceExport)
        assert result[0].doctor_id == mock_result.doctor_id
        assert result[0].total_appointments == mock_result.total_appointments
        assert result[0].completed_appointments == mock_result.completed_appointments
        assert 0 <= result[0].utilization_rate <= 1


class TestDataAggregation:
    """Test data aggregation methods."""
    
    def test_generate_doctor_utilization_report(self, analytics_service, mock_db):
        """Test doctor utilization report generation."""
        # Mock database query results
        mock_result = Mock()
        mock_result.doctor_id = uuid4()
        mock_result.first_name = "Dr. Jane"
        mock_result.last_name = "Smith"
        mock_result.specialization = "Cardiology"
        mock_result.department = "Cardiology"
        mock_result.total_appointments = 20
        mock_result.completed_appointments = 18
        mock_result.cancelled_appointments = 1
        mock_result.no_show_appointments = 1
        mock_result.total_scheduled_minutes = 600
        
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_result]
        
        # Test report generation
        result = analytics_service.generate_doctor_utilization_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert len(result) == 1
        assert isinstance(result[0], DoctorUtilizationReport)
        assert result[0].doctor_id == mock_result.doctor_id
        assert result[0].total_appointments == mock_result.total_appointments
        assert result[0].completion_rate == 0.9  # 18/20
        assert result[0].no_show_rate == 0.05  # 1/20
        assert result[0].utilization_rate >= 0
    
    def test_generate_appointment_trends_report(self, analytics_service, mock_db):
        """Test appointment trends report generation."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.count.return_value = 100
        
        # Mock status query
        status_mock = Mock()
        status_mock.status = "Completed"
        status_mock.count = 80
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [status_mock]
        
        # Mock specialization query
        spec_mock = Mock()
        spec_mock.specialization = "Cardiology"
        spec_mock.count = 50
        
        # Mock day of week query
        day_mock = Mock()
        day_mock.day_of_week = 1  # Monday
        day_mock.count = 20
        
        # Mock time query
        time_mock = Mock()
        time_mock.hour = 10
        time_mock.count = 15
        
        # Configure different return values for different queries
        def mock_query_side_effect(*args):
            query_mock = Mock()
            if hasattr(args[0], 'specialization'):
                query_mock.join.return_value.filter.return_value.group_by.return_value.all.return_value = [spec_mock]
            elif 'dow' in str(args):
                query_mock.filter.return_value.group_by.return_value.all.return_value = [day_mock]
            elif 'hour' in str(args):
                query_mock.filter.return_value.group_by.return_value.all.return_value = [time_mock]
            else:
                query_mock.filter.return_value.group_by.return_value.all.return_value = [status_mock]
            return query_mock
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Test report generation
        result = analytics_service.generate_appointment_trends_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert isinstance(result, AppointmentTrendsReport)
        assert result.total_appointments == 100
        assert isinstance(result.appointments_by_status, dict)
        assert isinstance(result.appointments_by_specialization, dict)
        assert isinstance(result.peak_hours, list)
        assert isinstance(result.busiest_days, list)
    
    def test_generate_resource_usage_report(self, analytics_service, mock_db):
        """Test resource usage report generation."""
        # Mock database query results
        type_mock = Mock()
        type_mock.resource_type = "Room"
        type_mock.count = 10
        
        mock_db.query.return_value.group_by.return_value.all.return_value = [type_mock]
        
        # Test report generation
        result = analytics_service.generate_resource_usage_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert isinstance(result, ResourceUsageReport)
        assert isinstance(result.resources_by_type, dict)
        assert "Room" in result.resources_by_type
        assert result.resources_by_type["Room"] == 10
        assert 0 <= result.average_occupancy_rate <= 1
        assert 0 <= result.availability_rate <= 1
        assert isinstance(result.peak_usage_hours, list)


class TestDataExport:
    """Test data export methods."""
    
    def test_export_data_for_synapse_appointments(self, analytics_service):
        """Test data export for appointments."""
        with patch.object(analytics_service, 'transform_appointments_for_analytics') as mock_transform:
            mock_export = AppointmentExport(
                appointment_id=uuid4(),
                patient_id=uuid4(),
                doctor_id=uuid4(),
                appointment_datetime=datetime.now(),
                duration=30,
                status="Completed",
                patient_age_group="36-50",
                doctor_specialization="Cardiology",
                show_status="Show",
                created_at=datetime.now()
            )
            mock_transform.return_value = [mock_export]
            
            result = analytics_service.export_data_for_synapse("appointments")
            
            assert "appointments" in result
            assert len(result["appointments"]) == 1
            assert isinstance(result["appointments"][0], dict)
    
    def test_export_data_for_synapse_all(self, analytics_service):
        """Test data export for all data types."""
        with patch.object(analytics_service, 'transform_appointments_for_analytics') as mock_apt, \
             patch.object(analytics_service, 'transform_resource_utilization_for_analytics') as mock_res, \
             patch.object(analytics_service, 'transform_doctor_performance_for_analytics') as mock_doc:
            
            mock_apt.return_value = []
            mock_res.return_value = []
            mock_doc.return_value = []
            
            result = analytics_service.export_data_for_synapse("all")
            
            assert "appointments" in result
            assert "resource_utilization" in result
            assert "doctor_performance" in result


class TestAnalyticsModels:
    """Test analytics data models."""
    
    def test_patient_age_group_calculation(self):
        """Test patient age group calculation."""
        # Test different age groups
        test_cases = [
            (date(2020, 1, 1), "0-18"),    # 4 years old
            (date(2000, 1, 1), "19-35"),   # 24 years old
            (date(1980, 1, 1), "36-50"),   # 44 years old
            (date(1960, 1, 1), "51-65"),   # 64 years old
            (date(1940, 1, 1), "65+"),     # 84 years old
        ]
        
        for birth_date, expected_group in test_cases:
            age_group = PatientAgeGroup(
                patient_id=uuid4(),
                date_of_birth=birth_date,
                current_date=date(2024, 1, 1)
            )
            assert age_group.age_group == expected_group
    
    def test_time_slot_analysis(self):
        """Test time slot analysis."""
        # Test morning slot
        morning_slot = TimeSlotAnalysis(hour=9, minute=30)
        assert morning_slot.time_period == "Morning"
        assert morning_slot.is_business_hours == True
        assert morning_slot.time_key == 930
        
        # Test evening slot
        evening_slot = TimeSlotAnalysis(hour=19, minute=0)
        assert evening_slot.time_period == "Evening"
        assert evening_slot.is_business_hours == False
        assert evening_slot.time_key == 1900
        
        # Test night slot
        night_slot = TimeSlotAnalysis(hour=2, minute=15)
        assert night_slot.time_period == "Night"
        assert night_slot.is_business_hours == False
    
    def test_date_analysis(self):
        """Test date analysis."""
        test_date = date(2024, 3, 15)  # Friday
        date_analysis = DateAnalysis(date=test_date)
        
        assert date_analysis.date_key == 20240315
        assert date_analysis.quarter == 1
        assert date_analysis.day_name == "Friday"
        assert date_analysis.month_name == "March"
        assert date_analysis.is_weekend == False
        
        # Test weekend
        weekend_date = date(2024, 3, 16)  # Saturday
        weekend_analysis = DateAnalysis(date=weekend_date)
        assert weekend_analysis.is_weekend == True


class TestErrorHandling:
    """Test error handling in analytics service."""
    
    def test_transform_appointments_error_handling(self, analytics_service, mock_db):
        """Test error handling in appointment transformation."""
        # Mock database error
        mock_db.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception) as exc_info:
            analytics_service.transform_appointments_for_analytics()
        
        assert "Database connection error" in str(exc_info.value)
    
    def test_generate_report_error_handling(self, analytics_service, mock_db):
        """Test error handling in report generation."""
        # Mock database error
        mock_db.query.side_effect = Exception("Query execution error")
        
        with pytest.raises(Exception) as exc_info:
            analytics_service.generate_doctor_utilization_report(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )
        
        assert "Query execution error" in str(exc_info.value)


class TestPerformance:
    """Test performance aspects of analytics service."""
    
    def test_large_dataset_handling(self, analytics_service, mock_db):
        """Test handling of large datasets."""
        # Mock large dataset
        large_dataset = []
        for i in range(1000):
            mock_result = Mock()
            mock_result.doctor_id = uuid4()
            mock_result.first_name = f"Doctor{i}"
            mock_result.last_name = f"Smith{i}"
            mock_result.specialization = "Cardiology"
            mock_result.department = "Cardiology"
            mock_result.total_appointments = 10
            mock_result.completed_appointments = 8
            mock_result.cancelled_appointments = 1
            mock_result.no_show_appointments = 1
            mock_result.total_scheduled_minutes = 300
            large_dataset.append(mock_result)
        
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = large_dataset
        
        # Test that large dataset is handled without errors
        result = analytics_service.generate_doctor_utilization_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert len(result) == 1000
        assert all(isinstance(report, DoctorUtilizationReport) for report in result)
    
    def test_date_range_validation(self, analytics_service):
        """Test date range validation."""
        # Test with valid date range
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Should not raise any errors for valid date range
        try:
            analytics_service.export_data_for_synapse(
                "appointments", start_date, end_date
            )
        except Exception as e:
            # Only database-related errors are expected, not date validation errors
            assert "date" not in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__])