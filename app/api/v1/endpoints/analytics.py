"""
Analytics API endpoints for hospital management system.
Provides endpoints for doctor utilization, appointment trends, and resource usage analytics.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.authorization import require_role
from app.models.user import UserRole
from app.services.analytics import AnalyticsService
from app.models.analytics import (
    DoctorUtilizationReport,
    AppointmentTrendsReport,
    ResourceUsageReport
)

router = APIRouter()


@router.get(
    "/doctor-utilization",
    response_model=List[DoctorUtilizationReport],
    summary="Get doctor utilization analytics",
    description="Retrieve doctor utilization metrics including appointment completion rates, working hours, and efficiency metrics."
)
async def get_doctor_utilization(
    start_date: Optional[date] = Query(
        None, 
        description="Start date for the analytics period (YYYY-MM-DD). Defaults to 30 days ago."
    ),
    end_date: Optional[date] = Query(
        None, 
        description="End date for the analytics period (YYYY-MM-DD). Defaults to today."
    ),
    doctor_id: Optional[UUID] = Query(
        None, 
        description="Specific doctor ID to filter results. If not provided, returns all doctors."
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get doctor utilization analytics.
    
    This endpoint provides comprehensive analytics on doctor performance including:
    - Total appointments scheduled and completed
    - Completion rates and no-show rates
    - Working hours and utilization rates
    - Average appointments per day
    
    **Required permissions:** Admin, Doctor, or Staff role
    """
    # Check authorization
    require_role(current_user, [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF])
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        # Check if date range is too large (limit to 1 year)
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 365 days"
            )
        
        # Initialize analytics service
        analytics_service = AnalyticsService(db)
        
        # Generate doctor utilization report
        utilization_reports = analytics_service.generate_doctor_utilization_report(
            start_date=start_date,
            end_date=end_date,
            doctor_id=doctor_id
        )
        
        return utilization_reports
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating doctor utilization report: {str(e)}"
        )


@router.get(
    "/appointment-trends",
    response_model=AppointmentTrendsReport,
    summary="Get appointment trends analytics",
    description="Retrieve appointment trends including status distribution, specialization breakdown, and temporal patterns."
)
async def get_appointment_trends(
    start_date: Optional[date] = Query(
        None, 
        description="Start date for the analytics period (YYYY-MM-DD). Defaults to 30 days ago."
    ),
    end_date: Optional[date] = Query(
        None, 
        description="End date for the analytics period (YYYY-MM-DD). Defaults to today."
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get appointment trends analytics.
    
    This endpoint provides comprehensive analytics on appointment patterns including:
    - Total appointments and status distribution
    - Appointments by medical specialization
    - Temporal patterns (day of week, time of day)
    - Peak hours and busiest days
    - Growth trends compared to previous periods
    
    **Required permissions:** Admin, Doctor, or Staff role
    """
    # Check authorization
    require_role(current_user, [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF])
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        # Check if date range is too large (limit to 1 year)
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 365 days"
            )
        
        # Initialize analytics service
        analytics_service = AnalyticsService(db)
        
        # Generate appointment trends report
        trends_report = analytics_service.generate_appointment_trends_report(
            start_date=start_date,
            end_date=end_date
        )
        
        return trends_report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating appointment trends report: {str(e)}"
        )


@router.get(
    "/resource-usage",
    response_model=ResourceUsageReport,
    summary="Get resource usage analytics",
    description="Retrieve hospital resource utilization metrics including occupancy rates, peak usage times, and efficiency indicators."
)
async def get_resource_usage(
    start_date: Optional[date] = Query(
        None, 
        description="Start date for the analytics period (YYYY-MM-DD). Defaults to 30 days ago."
    ),
    end_date: Optional[date] = Query(
        None, 
        description="End date for the analytics period (YYYY-MM-DD). Defaults to today."
    ),
    resource_type: Optional[str] = Query(
        None, 
        description="Filter by resource type (Room, Equipment, Bed). If not provided, includes all types."
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get resource usage analytics.
    
    This endpoint provides comprehensive analytics on hospital resource utilization including:
    - Resource distribution by type
    - Occupancy rates and utilization hours
    - Peak usage times and patterns
    - Under-utilized and over-utilized resources
    - Maintenance hours and availability rates
    
    **Required permissions:** Admin or Staff role
    """
    # Check authorization - only admin and staff can view resource analytics
    require_role(current_user, [UserRole.ADMIN, UserRole.STAFF])
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        # Check if date range is too large (limit to 1 year)
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 365 days"
            )
        
        # Validate resource type if provided
        valid_resource_types = ["Room", "Equipment", "Bed"]
        if resource_type and resource_type not in valid_resource_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource type. Must be one of: {', '.join(valid_resource_types)}"
            )
        
        # Initialize analytics service
        analytics_service = AnalyticsService(db)
        
        # Generate resource usage report
        usage_report = analytics_service.generate_resource_usage_report(
            start_date=start_date,
            end_date=end_date
        )
        
        # Filter by resource type if specified
        if resource_type:
            # Filter utilization data by resource type
            filtered_utilization = {
                k: v for k, v in usage_report.utilization_by_resource_type.items()
                if k == resource_type
            }
            usage_report.utilization_by_resource_type = filtered_utilization
            
            # Filter resource counts
            filtered_resources = {
                k: v for k, v in usage_report.resources_by_type.items()
                if k == resource_type
            }
            usage_report.resources_by_type = filtered_resources
        
        return usage_report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating resource usage report: {str(e)}"
        )


@router.get(
    "/dashboard-summary",
    summary="Get analytics dashboard summary",
    description="Retrieve a summary of key metrics for the analytics dashboard."
)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get analytics dashboard summary.
    
    This endpoint provides a high-level summary of key hospital metrics for dashboard display:
    - Total appointments today and this week
    - Doctor utilization summary
    - Resource occupancy summary
    - Recent trends and alerts
    
    **Required permissions:** Admin, Doctor, or Staff role
    """
    # Check authorization
    require_role(current_user, [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF])
    
    try:
        # Initialize analytics service
        analytics_service = AnalyticsService(db)
        
        # Get current date ranges
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Get quick metrics
        today_appointments = analytics_service.db.query(
            analytics_service.db.query(analytics_service.db.models.Appointment).filter(
                analytics_service.db.func.date(analytics_service.db.models.Appointment.appointment_datetime) == today
            ).count()
        )
        
        # Generate summary reports for smaller date ranges
        week_doctor_utilization = analytics_service.generate_doctor_utilization_report(
            start_date=week_start,
            end_date=today
        )
        
        week_resource_usage = analytics_service.generate_resource_usage_report(
            start_date=week_start,
            end_date=today
        )
        
        # Calculate summary metrics
        total_doctors = len(week_doctor_utilization)
        avg_doctor_utilization = (
            sum(report.utilization_rate for report in week_doctor_utilization) / total_doctors
            if total_doctors > 0 else 0.0
        )
        
        summary = {
            "date_generated": datetime.utcnow().isoformat(),
            "period": {
                "today": today.isoformat(),
                "week_start": week_start.isoformat(),
                "month_start": month_start.isoformat()
            },
            "appointments": {
                "today_total": 0,  # Would need actual query implementation
                "week_total": sum(report.total_appointments for report in week_doctor_utilization),
                "completion_rate": (
                    sum(report.completion_rate for report in week_doctor_utilization) / total_doctors
                    if total_doctors > 0 else 0.0
                )
            },
            "doctors": {
                "total_active": total_doctors,
                "average_utilization": avg_doctor_utilization,
                "high_performers": len([r for r in week_doctor_utilization if r.utilization_rate > 0.8]),
                "low_performers": len([r for r in week_doctor_utilization if r.utilization_rate < 0.5])
            },
            "resources": {
                "total_resources": sum(week_resource_usage.resources_by_type.values()),
                "average_occupancy": week_resource_usage.average_occupancy_rate,
                "availability_rate": week_resource_usage.availability_rate,
                "resources_by_type": week_resource_usage.resources_by_type
            },
            "alerts": [
                # Mock alerts - would be calculated based on actual thresholds
                {
                    "type": "low_utilization",
                    "message": "3 resources have utilization below 30%",
                    "severity": "warning"
                } if week_resource_usage.average_occupancy_rate < 0.5 else None,
                {
                    "type": "high_no_show",
                    "message": "No-show rate above 15% this week",
                    "severity": "warning"
                } if any(r.no_show_rate > 0.15 for r in week_doctor_utilization) else None
            ]
        }
        
        # Remove None alerts
        summary["alerts"] = [alert for alert in summary["alerts"] if alert is not None]
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating dashboard summary: {str(e)}"
        )


@router.post(
    "/export-data",
    summary="Export analytics data",
    description="Export analytics data for external processing or backup."
)
async def export_analytics_data(
    data_type: str = Query(
        ..., 
        description="Type of data to export (appointments, resources, doctors, all)"
    ),
    start_date: Optional[date] = Query(
        None, 
        description="Start date for export (YYYY-MM-DD). Defaults to 30 days ago."
    ),
    end_date: Optional[date] = Query(
        None, 
        description="End date for export (YYYY-MM-DD). Defaults to today."
    ),
    format: str = Query(
        "json", 
        description="Export format (json, csv). Defaults to json."
    ),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Export analytics data for external processing.
    
    This endpoint allows exporting of analytics data in various formats for:
    - External analysis tools
    - Data backup and archival
    - Integration with other systems
    - Compliance reporting
    
    **Required permissions:** Admin role only
    """
    # Check authorization - only admin can export data
    require_role(current_user, [UserRole.ADMIN])
    
    try:
        # Validate data type
        valid_data_types = ["appointments", "resources", "doctors", "all"]
        if data_type not in valid_data_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data type. Must be one of: {', '.join(valid_data_types)}"
            )
        
        # Validate format
        valid_formats = ["json", "csv"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        # Initialize analytics service
        analytics_service = AnalyticsService(db)
        
        # Export data
        exported_data = analytics_service.export_data_for_synapse(
            data_type=data_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # Prepare response
        export_info = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "data_type": data_type,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "format": format,
            "record_counts": {
                table_name: len(table_data) 
                for table_name, table_data in exported_data.items()
            },
            "exported_by": current_user.username if hasattr(current_user, 'username') else str(current_user.user_id)
        }
        
        if format == "json":
            return {
                "export_info": export_info,
                "data": exported_data
            }
        else:
            # For CSV format, would need to implement CSV conversion
            # For now, return JSON with a note
            return {
                "export_info": export_info,
                "message": "CSV export format not yet implemented. Returning JSON format.",
                "data": exported_data
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting analytics data: {str(e)}"
        )


@router.post(
    "/trigger-etl",
    summary="Manually trigger ETL pipeline",
    description="Manually trigger ETL pipeline for specific data type and date range."
)
async def trigger_etl_pipeline(
    data_type: str = Query(
        ..., 
        description="Type of data to process (appointments, resources, doctors, all)"
    ),
    start_date: date = Query(
        ..., 
        description="Start date for ETL processing (YYYY-MM-DD)"
    ),
    end_date: date = Query(
        ..., 
        description="End date for ETL processing (YYYY-MM-DD)"
    ),
    job_name: Optional[str] = Query(
        None, 
        description="Optional name for the ETL job"
    ),
    current_user = Depends(get_current_user)
):
    """
    Manually trigger ETL pipeline.
    
    This endpoint allows manual triggering of ETL pipelines for:
    - Data reprocessing after corrections
    - Backfilling missing data
    - Testing pipeline functionality
    - Emergency data synchronization
    
    **Required permissions:** Admin role only
    """
    # Check authorization - only admin can trigger ETL
    require_role(current_user, [UserRole.ADMIN])
    
    try:
        # Validate data type
        valid_data_types = ["appointments", "resources", "doctors", "all"]
        if data_type not in valid_data_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data type. Must be one of: {', '.join(valid_data_types)}"
            )
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before or equal to end date"
            )
        
        # Check if date range is too large (limit to 90 days for manual ETL)
        if (end_date - start_date).days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range for manual ETL cannot exceed 90 days"
            )
        
        # Import scheduler here to avoid circular imports
        from app.core.scheduler import etl_scheduler
        
        # Trigger manual ETL
        result = await etl_scheduler.trigger_manual_etl(
            data_type=data_type,
            start_date=start_date,
            end_date=end_date,
            job_name=job_name
        )
        
        return {
            "message": f"ETL pipeline triggered for {data_type}",
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "start_time": result.get("start_time"),
            "end_time": result.get("end_time"),
            "data_exports": result.get("data_exports", {}),
            "pipeline_runs": result.get("pipeline_runs", {}),
            "error": result.get("error")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering ETL pipeline: {str(e)}"
        )


@router.get(
    "/etl-status",
    summary="Get ETL job status and history",
    description="Retrieve status and history of ETL jobs."
)
async def get_etl_status(
    limit: Optional[int] = Query(
        10, 
        description="Number of recent jobs to return. Maximum 100."
    ),
    current_user = Depends(get_current_user)
):
    """
    Get ETL job status and history.
    
    This endpoint provides information about:
    - Recent ETL job executions
    - Job success/failure status
    - Scheduled job information
    - Pipeline execution details
    
    **Required permissions:** Admin or Staff role
    """
    # Check authorization
    require_role(current_user, [UserRole.ADMIN, UserRole.STAFF])
    
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        # Import scheduler here to avoid circular imports
        from app.core.scheduler import etl_scheduler
        
        # Get job history and scheduled jobs
        job_history = etl_scheduler.get_job_history(limit=limit)
        scheduled_jobs = etl_scheduler.get_scheduled_jobs()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "scheduled_jobs": scheduled_jobs,
            "job_history": job_history,
            "total_history_entries": len(etl_scheduler.get_job_history())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ETL status: {str(e)}"
        )


@router.post(
    "/etl-job/{job_id}/{action}",
    summary="Manage ETL scheduled jobs",
    description="Pause, resume, or remove scheduled ETL jobs."
)
async def manage_etl_job(
    job_id: str,
    action: str,
    current_user = Depends(get_current_user)
):
    """
    Manage ETL scheduled jobs.
    
    This endpoint allows management of scheduled ETL jobs:
    - pause: Temporarily pause a scheduled job
    - resume: Resume a paused job
    - remove: Permanently remove a scheduled job
    
    **Required permissions:** Admin role only
    """
    # Check authorization - only admin can manage ETL jobs
    require_role(current_user, [UserRole.ADMIN])
    
    try:
        # Validate action
        valid_actions = ["pause", "resume", "remove"]
        if action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
            )
        
        # Import scheduler here to avoid circular imports
        from app.core.scheduler import etl_scheduler
        
        # Perform action
        if action == "pause":
            success = await etl_scheduler.pause_job(job_id)
        elif action == "resume":
            success = await etl_scheduler.resume_job(job_id)
        elif action == "remove":
            success = await etl_scheduler.remove_job(job_id)
        
        if success:
            return {
                "message": f"Job {job_id} {action}d successfully",
                "job_id": job_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to {action} job {job_id}. Job may not exist or action may not be applicable."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error managing ETL job: {str(e)}"
        )