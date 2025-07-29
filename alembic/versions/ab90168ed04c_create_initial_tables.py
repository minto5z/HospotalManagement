"""Create initial tables

Revision ID: ab90168ed04c
Revises: 
Create Date: 2025-07-29 13:45:52.237300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER


# revision identifiers, used by Alembic.
revision: str = 'ab90168ed04c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('patient_id', UNIQUEIDENTIFIER, primary_key=True, nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('date_of_birth', sa.Date, nullable=False),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('emergency_contact', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create doctors table
    op.create_table(
        'doctors',
        sa.Column('doctor_id', UNIQUEIDENTIFIER, primary_key=True, nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('specialization', sa.String(100), nullable=False),
        sa.Column('license_number', sa.String(50), unique=True, nullable=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create hospital_resources table
    op.create_table(
        'hospital_resources',
        sa.Column('resource_id', UNIQUEIDENTIFIER, primary_key=True, nullable=False),
        sa.Column('resource_name', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), default='Available', nullable=False),
        sa.Column('assigned_to_patient_id', UNIQUEIDENTIFIER, nullable=True),
        sa.Column('assigned_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_patient_id'], ['patients.patient_id']),
    )
    
    # Create doctor_schedules table
    op.create_table(
        'doctor_schedules',
        sa.Column('schedule_id', UNIQUEIDENTIFIER, primary_key=True, nullable=False),
        sa.Column('doctor_id', UNIQUEIDENTIFIER, nullable=False),
        sa.Column('day_of_week', sa.Integer, nullable=False),
        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id']),
    )
    
    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('appointment_id', UNIQUEIDENTIFIER, primary_key=True, nullable=False),
        sa.Column('patient_id', UNIQUEIDENTIFIER, nullable=False),
        sa.Column('doctor_id', UNIQUEIDENTIFIER, nullable=False),
        sa.Column('appointment_datetime', sa.DateTime, nullable=False),
        sa.Column('duration', sa.Integer, default=30, nullable=False),
        sa.Column('status', sa.String(20), default='Scheduled', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id']),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id']),
    )
    
    # Create indexes for performance optimization
    op.create_index('ix_patients_last_name', 'patients', ['last_name'])
    op.create_index('ix_patients_email', 'patients', ['email'])
    op.create_index('ix_patients_phone_number', 'patients', ['phone_number'])
    op.create_index('ix_patients_is_active', 'patients', ['is_active'])
    
    op.create_index('ix_doctors_specialization', 'doctors', ['specialization'])
    op.create_index('ix_doctors_department', 'doctors', ['department'])
    op.create_index('ix_doctors_is_active', 'doctors', ['is_active'])
    
    op.create_index('ix_appointments_datetime', 'appointments', ['appointment_datetime'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.create_index('ix_appointments_patient_id', 'appointments', ['patient_id'])
    op.create_index('ix_appointments_doctor_id', 'appointments', ['doctor_id'])
    
    op.create_index('ix_hospital_resources_type', 'hospital_resources', ['resource_type'])
    op.create_index('ix_hospital_resources_status', 'hospital_resources', ['status'])
    op.create_index('ix_hospital_resources_location', 'hospital_resources', ['location'])
    
    op.create_index('ix_doctor_schedules_doctor_id', 'doctor_schedules', ['doctor_id'])
    op.create_index('ix_doctor_schedules_day_of_week', 'doctor_schedules', ['day_of_week'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_doctor_schedules_day_of_week', 'doctor_schedules')
    op.drop_index('ix_doctor_schedules_doctor_id', 'doctor_schedules')
    op.drop_index('ix_hospital_resources_location', 'hospital_resources')
    op.drop_index('ix_hospital_resources_status', 'hospital_resources')
    op.drop_index('ix_hospital_resources_type', 'hospital_resources')
    op.drop_index('ix_appointments_doctor_id', 'appointments')
    op.drop_index('ix_appointments_patient_id', 'appointments')
    op.drop_index('ix_appointments_status', 'appointments')
    op.drop_index('ix_appointments_datetime', 'appointments')
    op.drop_index('ix_doctors_is_active', 'doctors')
    op.drop_index('ix_doctors_department', 'doctors')
    op.drop_index('ix_doctors_specialization', 'doctors')
    op.drop_index('ix_patients_is_active', 'patients')
    op.drop_index('ix_patients_phone_number', 'patients')
    op.drop_index('ix_patients_email', 'patients')
    op.drop_index('ix_patients_last_name', 'patients')
    
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('appointments')
    op.drop_table('doctor_schedules')
    op.drop_table('hospital_resources')
    op.drop_table('doctors')
    op.drop_table('patients')
