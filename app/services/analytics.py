"""
Analytics service for data aggregation and Azure Synapse integration.
Handles ETL operations and data transformation for analytics.
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
import logging

from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.hospital_resource import HospitalResource
from app.models.analytics import (
    FactAppointment, FactResourceUtilization, FactDoctorUtilization,
    DimDoctor, DimPatient, DimResource, DimDate, DimTime,
    DoctorUtilizationReport, AppointmentTrendsReport, ResourceUsageReport,
    AppointmentExport, ResourceUtilizationExport, DoctorPerformanceExport,
    PatientAgeGroup, TimeSlotAnalysis, DateAnalysis,
    AppointmentStatus, ResourceType, ResourceStatus
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics data processing and aggregation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Data Transformation Methods
    
    def transform_appointments_for_analytics(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[AppointmentExport]:
        """Transform appointment data for analytics export."""
        try:
            query = self.db.query(
                Appointment, Patient, Doctor
            ).join(
                Patient, Appointment.patient_id == Patient.patient_id
            ).join(
                Doctor, Appointment.doctor_id == Doctor.doctor_id
            )
            
            if start_date:
                query = query.filter(func.date(Appointment.appointment_datetime) >= start_date)
            if end_date:
                query = query.filter(func.date(Appointment.appointment_datetime) <= end_date)
            
            results = query.all()
            
            transformed_data = []
            for appointment, patient, doctor in results:
                # Calculate patient age group
                age_group_calc = PatientAgeGroup(
                    patient_id=patient.patient_id,
                    date_of_birth=patient.date_of_birth
                )
                
                # Determine show status
                show_status = "Show" if appointment.status in ["Completed"] else "No-Show" if appointment.status == "No-Show" else "Scheduled"
                
                # Calculate wait time (mock calculation - would need actual check-in data)
                wait_time = None
                if appointment.status == "Completed":
                    wait_time = 15  # Mock average wait time
                
                export_data = AppointmentExport(
                    appointment_id=appointment.appointment_id,
                    patient_id=appointment.patient_id,
                    doctor_id=appointment.doctor_id,
                    appointment_datetime=appointment.appointment_datetime,
                    duration=appointment.duration,
                    status=appointment.status,
                    notes=appointment.notes,
                    patient_age_group=age_group_calc.age_group,
                    patient_gender=patient.gender,
                    doctor_specialization=doctor.specialization,
                    doctor_department=doctor.department,
                    wait_time=wait_time,
                    show_status=show_status,
                    created_at=appointment.created_at,
                    updated_at=appointment.updated_at
                )
                transformed_data.append(export_data)
            
            logger.info(f"Transformed {len(transformed_data)} appointments for analytics")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming appointments for analytics: {e}")
            raise
    
    def transform_resource_utilization_for_analytics(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[ResourceUtilizationExport]:
        """Transform resource utilization data for analytics export."""
        try:
            # Get all resources
            resources = self.db.query(HospitalResource).all()
            
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            transformed_data = []
            
            for resource in resources:
                # Calculate utilization for each day in the date range
                current_date = start_date
                while current_date <= end_date:
                    # Mock calculation - in real implementation, would track actual usage
                    total_assignments = 0
                    total_occupied_hours = 0.0
                    maintenance_hours = 0.0
                    
                    if resource.status == "Occupied":
                        total_assignments = 1
                        total_occupied_hours = 8.0  # Mock 8 hours usage
                    elif resource.status == "Maintenance":
                        maintenance_hours = 4.0  # Mock 4 hours maintenance
                    
                    # Calculate rates
                    total_available_hours = 24.0
                    occupancy_rate = total_occupied_hours / total_available_hours
                    availability_rate = (total_available_hours - maintenance_hours) / total_available_hours
                    
                    export_data = ResourceUtilizationExport(
                        resource_id=resource.resource_id,
                        resource_name=resource.resource_name,
                        resource_type=resource.resource_type,
                        location=resource.location,
                        date=current_date,
                        total_assignments=total_assignments,
                        total_occupied_hours=total_occupied_hours,
                        occupancy_rate=occupancy_rate,
                        maintenance_hours=maintenance_hours,
                        availability_rate=availability_rate,
                        created_at=datetime.utcnow()
                    )
                    transformed_data.append(export_data)
                    
                    current_date += timedelta(days=1)
            
            logger.info(f"Transformed {len(transformed_data)} resource utilization records for analytics")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming resource utilization for analytics: {e}")
            raise
    
    def transform_doctor_performance_for_analytics(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[DoctorPerformanceExport]:
        """Transform doctor performance data for analytics export."""
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            # Query doctor performance data
            query = self.db.query(
                Doctor.doctor_id,
                Doctor.first_name,
                Doctor.last_name,
                Doctor.specialization,
                Doctor.department,
                func.date(Appointment.appointment_datetime).label('appointment_date'),
                func.count(Appointment.appointment_id).label('total_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'Completed', 1),
                        else_=0
                    )
                ).label('completed_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'Cancelled', 1),
                        else_=0
                    )
                ).label('cancelled_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'No-Show', 1),
                        else_=0
                    )
                ).label('no_show_appointments'),
                func.sum(Appointment.duration).label('total_scheduled_minutes')
            ).join(
                Appointment, Doctor.doctor_id == Appointment.doctor_id
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).group_by(
                Doctor.doctor_id,
                Doctor.first_name,
                Doctor.last_name,
                Doctor.specialization,
                Doctor.department,
                func.date(Appointment.appointment_datetime)
            )
            
            results = query.all()
            
            transformed_data = []
            for result in results:
                # Calculate utilization rate
                actual_worked_minutes = result.completed_appointments * 30  # Assume 30 min average
                utilization_rate = (
                    actual_worked_minutes / result.total_scheduled_minutes 
                    if result.total_scheduled_minutes > 0 else 0.0
                )
                
                export_data = DoctorPerformanceExport(
                    doctor_id=result.doctor_id,
                    doctor_name=f"{result.first_name} {result.last_name}",
                    specialization=result.specialization,
                    department=result.department,
                    date=result.appointment_date,
                    total_appointments=result.total_appointments,
                    completed_appointments=result.completed_appointments,
                    cancelled_appointments=result.cancelled_appointments,
                    no_show_appointments=result.no_show_appointments,
                    total_scheduled_minutes=result.total_scheduled_minutes,
                    actual_worked_minutes=actual_worked_minutes,
                    utilization_rate=utilization_rate,
                    created_at=datetime.utcnow()
                )
                transformed_data.append(export_data)
            
            logger.info(f"Transformed {len(transformed_data)} doctor performance records for analytics")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming doctor performance for analytics: {e}")
            raise
    
    # Data Aggregation Methods
    
    def generate_doctor_utilization_report(
        self, 
        start_date: date, 
        end_date: date,
        doctor_id: Optional[UUID] = None
    ) -> List[DoctorUtilizationReport]:
        """Generate doctor utilization report."""
        try:
            query = self.db.query(
                Doctor.doctor_id,
                Doctor.first_name,
                Doctor.last_name,
                Doctor.specialization,
                Doctor.department,
                func.count(Appointment.appointment_id).label('total_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'Completed', 1),
                        else_=0
                    )
                ).label('completed_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'Cancelled', 1),
                        else_=0
                    )
                ).label('cancelled_appointments'),
                func.sum(
                    func.case(
                        (Appointment.status == 'No-Show', 1),
                        else_=0
                    )
                ).label('no_show_appointments'),
                func.sum(Appointment.duration).label('total_scheduled_minutes')
            ).join(
                Appointment, Doctor.doctor_id == Appointment.doctor_id
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            )
            
            if doctor_id:
                query = query.filter(Doctor.doctor_id == doctor_id)
            
            query = query.group_by(
                Doctor.doctor_id,
                Doctor.first_name,
                Doctor.last_name,
                Doctor.specialization,
                Doctor.department
            )
            
            results = query.all()
            
            reports = []
            for result in results:
                # Calculate metrics
                completion_rate = (
                    result.completed_appointments / result.total_appointments 
                    if result.total_appointments > 0 else 0.0
                )
                no_show_rate = (
                    result.no_show_appointments / result.total_appointments 
                    if result.total_appointments > 0 else 0.0
                )
                
                days_in_period = (end_date - start_date).days + 1
                avg_appointments_per_day = result.total_appointments / days_in_period
                
                total_scheduled_hours = result.total_scheduled_minutes / 60.0
                actual_worked_hours = result.completed_appointments * 0.5  # Assume 30 min average
                utilization_rate = (
                    actual_worked_hours / total_scheduled_hours 
                    if total_scheduled_hours > 0 else 0.0
                )
                
                report = DoctorUtilizationReport(
                    doctor_id=result.doctor_id,
                    doctor_name=f"{result.first_name} {result.last_name}",
                    specialization=result.specialization,
                    department=result.department,
                    period_start=start_date,
                    period_end=end_date,
                    total_appointments=result.total_appointments,
                    completed_appointments=result.completed_appointments,
                    cancelled_appointments=result.cancelled_appointments,
                    no_show_appointments=result.no_show_appointments,
                    completion_rate=completion_rate,
                    no_show_rate=no_show_rate,
                    average_appointments_per_day=avg_appointments_per_day,
                    total_scheduled_hours=total_scheduled_hours,
                    actual_worked_hours=actual_worked_hours,
                    utilization_rate=utilization_rate
                )
                reports.append(report)
            
            logger.info(f"Generated {len(reports)} doctor utilization reports")
            return reports
            
        except Exception as e:
            logger.error(f"Error generating doctor utilization report: {e}")
            raise
    
    def generate_appointment_trends_report(
        self, 
        start_date: date, 
        end_date: date
    ) -> AppointmentTrendsReport:
        """Generate appointment trends report."""
        try:
            # Get total appointments
            total_appointments = self.db.query(Appointment).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).count()
            
            # Get appointments by status
            status_query = self.db.query(
                Appointment.status,
                func.count(Appointment.appointment_id).label('count')
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).group_by(Appointment.status)
            
            appointments_by_status = {
                result.status: result.count for result in status_query.all()
            }
            
            # Get appointments by specialization
            specialization_query = self.db.query(
                Doctor.specialization,
                func.count(Appointment.appointment_id).label('count')
            ).join(
                Appointment, Doctor.doctor_id == Appointment.doctor_id
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).group_by(Doctor.specialization)
            
            appointments_by_specialization = {
                result.specialization: result.count for result in specialization_query.all()
            }
            
            # Get appointments by day of week
            day_query = self.db.query(
                func.extract('dow', Appointment.appointment_datetime).label('day_of_week'),
                func.count(Appointment.appointment_id).label('count')
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).group_by(func.extract('dow', Appointment.appointment_datetime))
            
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            appointments_by_day_of_week = {}
            for result in day_query.all():
                day_name = day_names[int(result.day_of_week)]
                appointments_by_day_of_week[day_name] = result.count
            
            # Get appointments by time period
            time_query = self.db.query(
                func.extract('hour', Appointment.appointment_datetime).label('hour'),
                func.count(Appointment.appointment_id).label('count')
            ).filter(
                and_(
                    func.date(Appointment.appointment_datetime) >= start_date,
                    func.date(Appointment.appointment_datetime) <= end_date
                )
            ).group_by(func.extract('hour', Appointment.appointment_datetime))
            
            appointments_by_time_period = {"Morning": 0, "Afternoon": 0, "Evening": 0, "Night": 0}
            peak_hours = []
            max_count = 0
            
            for result in time_query.all():
                hour = int(result.hour)
                count = result.count
                
                if count > max_count:
                    max_count = count
                    peak_hours = [hour]
                elif count == max_count:
                    peak_hours.append(hour)
                
                time_analysis = TimeSlotAnalysis(hour=hour, minute=0)
                appointments_by_time_period[time_analysis.time_period] += count
            
            # Calculate busiest days
            busiest_days = sorted(
                appointments_by_day_of_week.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            busiest_days = [day for day, _ in busiest_days]
            
            report = AppointmentTrendsReport(
                period_start=start_date,
                period_end=end_date,
                total_appointments=total_appointments,
                appointments_by_status=appointments_by_status,
                appointments_by_specialization=appointments_by_specialization,
                appointments_by_day_of_week=appointments_by_day_of_week,
                appointments_by_time_period=appointments_by_time_period,
                average_wait_time=15.0,  # Mock value
                peak_hours=peak_hours,
                busiest_days=busiest_days
            )
            
            logger.info("Generated appointment trends report")
            return report
            
        except Exception as e:
            logger.error(f"Error generating appointment trends report: {e}")
            raise
    
    def generate_resource_usage_report(
        self, 
        start_date: date, 
        end_date: date
    ) -> ResourceUsageReport:
        """Generate resource usage report."""
        try:
            # Get resources by type
            type_query = self.db.query(
                HospitalResource.resource_type,
                func.count(HospitalResource.resource_id).label('count')
            ).group_by(HospitalResource.resource_type)
            
            resources_by_type = {
                result.resource_type: result.count for result in type_query.all()
            }
            
            # Calculate utilization metrics (mock calculations)
            total_resources = sum(resources_by_type.values())
            total_utilization_hours = total_resources * 8.0 * (end_date - start_date).days  # Mock
            average_occupancy_rate = 0.65  # Mock 65% average occupancy
            
            utilization_by_resource_type = {
                "Room": 0.70,
                "Equipment": 0.60,
                "Bed": 0.65
            }
            
            # Mock peak usage hours
            peak_usage_hours = [9, 10, 11, 14, 15, 16]
            
            # Mock underutilized and overutilized resources
            underutilized_resources = [
                {"resource_id": "mock-id-1", "resource_name": "CT Scanner 2", "utilization_rate": 0.30},
                {"resource_id": "mock-id-2", "resource_name": "Operating Room 5", "utilization_rate": 0.25}
            ]
            
            overutilized_resources = [
                {"resource_id": "mock-id-3", "resource_name": "MRI Machine 1", "utilization_rate": 0.95},
                {"resource_id": "mock-id-4", "resource_name": "ICU Bed 3", "utilization_rate": 0.90}
            ]
            
            maintenance_hours = total_resources * 2.0 * (end_date - start_date).days  # Mock
            availability_rate = 0.92  # Mock 92% availability
            
            report = ResourceUsageReport(
                period_start=start_date,
                period_end=end_date,
                resources_by_type=resources_by_type,
                total_utilization_hours=total_utilization_hours,
                average_occupancy_rate=average_occupancy_rate,
                utilization_by_resource_type=utilization_by_resource_type,
                peak_usage_hours=peak_usage_hours,
                underutilized_resources=underutilized_resources,
                overutilized_resources=overutilized_resources,
                maintenance_hours=maintenance_hours,
                availability_rate=availability_rate
            )
            
            logger.info("Generated resource usage report")
            return report
            
        except Exception as e:
            logger.error(f"Error generating resource usage report: {e}")
            raise
    
    # Data Export Methods
    
    def export_data_for_synapse(
        self, 
        data_type: str, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Export data for Azure Synapse integration."""
        try:
            exported_data = {}
            
            if data_type == "appointments" or data_type == "all":
                appointments = self.transform_appointments_for_analytics(start_date, end_date)
                exported_data["appointments"] = [apt.dict() for apt in appointments]
            
            if data_type == "resources" or data_type == "all":
                resources = self.transform_resource_utilization_for_analytics(start_date, end_date)
                exported_data["resource_utilization"] = [res.dict() for res in resources]
            
            if data_type == "doctors" or data_type == "all":
                doctors = self.transform_doctor_performance_for_analytics(start_date, end_date)
                exported_data["doctor_performance"] = [doc.dict() for doc in doctors]
            
            logger.info(f"Exported {data_type} data for Synapse integration")
            return exported_data
            
        except Exception as e:
            logger.error(f"Error exporting data for Synapse: {e}")
            raise