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