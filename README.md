# Hospital Management System

A comprehensive hospital management system with patient management, analytics, and Azure Synapse integration.

## Features

- Patient management
- User authentication and authorization
- Analytics and reporting
- Azure Synapse integration for data warehousing
- Comprehensive error handling and logging
- API documentation

## Getting Started

### Prerequisites

- Python 3.8+
- SQL Server or Azure SQL
- Docker (optional)

### Environment Setup

1. Clone the repository
2. Copy `env.example` to `.env` and configure your environment variables
3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

#### Without Docker

```bash
uvicorn app.main:app --reload
```

#### With Docker

```bash
docker-compose up -d
```

## API Documentation

The API documentation is automatically generated using FastAPI's OpenAPI integration.

### Accessing Documentation

Once the application is running, you can access the documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Documentation Features

- Interactive API exploration
- Request/response examples
- Authentication instructions
- Detailed endpoint descriptions
- Schema definitions

## Testing

### Running Tests

```bash
pytest
```

### Test Coverage

```bash
pytest --cov=app tests/
```

### Integration Tests

The system includes comprehensive integration tests that validate:

- Complete user workflows from API to database
- Cross-service interactions
- Data consistency
- Error handling
- Security controls

## Error Handling

The system implements comprehensive error handling:

- Global exception handlers
- Standardized error responses
- Request correlation IDs for tracking
- Input validation and sanitization
- SQL injection prevention

## Deployment

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t hospital-management-system .
```

2. Run with Docker Compose:
```bash
docker-compose up -d
```

### Azure App Service Deployment

1. Configure your Azure App Service settings
2. Deploy using Azure CLI or GitHub Actions

## Security Features

- JWT-based authentication
- Role-based access control
- Input validation and sanitization
- SQL injection prevention
- Request correlation IDs
- Comprehensive audit logging 



Based on the code I've examined, here's the table structure for the main entities in the Hospital Management System:
1. Patient Table
Column	Type	Constraints	Description
patient_id	UUID	Primary Key	Unique identifier for the patient
first_name	String(50)	NOT NULL	Patient's first name
last_name	String(50)	NOT NULL	Patient's last name
date_of_birth	Date	NOT NULL	Patient's date of birth
gender	String(10)	NULL	Patient's gender
phone_number	String(20)	NULL	Contact phone number
email	String(100)	NULL	Email address
address	String(500)	NULL	Physical address
emergency_contact	String(200)	NULL	Emergency contact information
is_active	Boolean	NOT NULL, Default: true	Whether the patient is active
created_at	DateTime	NOT NULL	Record creation timestamp
updated_at	DateTime	NOT NULL	Record update timestamp
2. Doctor Table
Column	Type	Constraints	Description
doctor_id	UUID	Primary Key	Unique identifier for the doctor
first_name	String(50)	NOT NULL	Doctor's first name
last_name	String(50)	NOT NULL	Doctor's last name
specialization	String(100)	NOT NULL	Medical specialization
license_number	String(50)	NOT NULL, Unique	Professional license number
department	String(100)	NULL	Hospital department
phone_number	String(20)	NULL	Contact phone number
email	String(100)	NULL	Email address
is_active	Boolean	NOT NULL, Default: true	Whether the doctor is active
created_at	DateTime	NOT NULL	Record creation timestamp
updated_at	DateTime	NOT NULL	Record update timestamp
3. Appointment Table
Column	Type	Constraints	Description
appointment_id	UUID	Primary Key	Unique identifier for the appointment
patient_id	UUID	Foreign Key (patients.patient_id)	Reference to the patient
doctor_id	UUID	Foreign Key (doctors.doctor_id)	Reference to the doctor
appointment_datetime	DateTime	NOT NULL	Date and time of the appointment
duration	Integer	NOT NULL, Default: 30	Duration in minutes
status	String(20)	NOT NULL, Default: "Scheduled"	Appointment status
notes	Text	NULL	Additional notes
created_at	DateTime	NOT NULL	Record creation timestamp
updated_at	DateTime	NOT NULL	Record update timestamp
4. Hospital Resource Table
Column	Type	Constraints	Description
resource_id	UUID	Primary Key	Unique identifier for the resource
resource_name	String(100)	NOT NULL	Name of the resource
resource_type	String(50)	NOT NULL	Type (Room, Equipment, Bed)
location	String(100)	NULL	Physical location
status	String(20)	NOT NULL, Default: "Available"	Current status
assigned_to_patient_id	UUID	Foreign Key (patients.patient_id), NULL	Patient assignment
assigned_at	DateTime	NULL	Assignment timestamp
created_at	DateTime	NOT NULL	Record creation timestamp
updated_at	DateTime	NOT NULL	Record update timestamp
5. Doctor Schedule Table
Column	Type	Constraints	Description
schedule_id	UUID	Primary Key	Unique identifier for the schedule
doctor_id	UUID	Foreign Key (doctors.doctor_id)	Reference to the doctor
day_of_week	Integer	NOT NULL	Day of week (0=Sunday, 1=Monday, etc.)
start_time	Time	NOT NULL	Start time of availability
end_time	Time	NOT NULL	End time of availability
is_active	Boolean	NOT NULL, Default: true	Whether the schedule is active
6. User Table
Column	Type	Constraints	Description
user_id	UUID	Primary Key	Unique identifier for the user
username	String(50)	NOT NULL, Unique, Indexed	Username for login
email	String(100)	NOT NULL, Unique, Indexed	Email address
hashed_password	String(255)	NOT NULL	Securely hashed password
full_name	String(100)	NOT NULL	User's full name
role	Enum	NOT NULL, Default: "staff"	User role (admin, doctor, staff, patient)
is_active	Boolean	NOT NULL, Default: true	Whether the user is active
created_at	DateTime	NOT NULL	Record creation timestamp
updated_at	DateTime	NOT NULL	Record update timestamp
last_login	DateTime	NULL	Last login timestamp
These tables form the core data structure of the Hospital Management System, with relationships between them to maintain data integrity and support the application's functionality.