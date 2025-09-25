# Educify AI Teacher-Student Matching System

An intelligent AI-powered system that matches students with suitable teachers based on learning preferences, availability, budget, and compatibility factors.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Integration Guide](#integration-guide)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)

## Overview

Educify uses machine learning to intelligently match students with teachers based on multiple compatibility factors including subjects, teaching/learning styles, availability, location preferences, and budget constraints. The system combines content-based filtering with collaborative filtering to provide accurate recommendations.

### Key Components
- **AI Matching Engine**: Core algorithm using scikit-learn and custom feature engineering
- **REST API**: FastAPI-based service for real-time matching
- **Training Pipeline**: Automated model retraining with MLflow tracking
- **Caching Layer**: Redis for high-performance response caching
- **Data Storage**: PostgreSQL for persistent data storage
- **Monitoring**: Prometheus metrics and Grafana dashboards

## Features

- **Intelligent Matching**: Multi-factor compatibility scoring
- **Real-time API**: Sub-second response times with caching
- **Scalable Architecture**: Kubernetes-ready with auto-scaling
- **Continuous Learning**: Models improve with user feedback
- **API Authentication**: Secure access with rate limiting
- **Comprehensive Monitoring**: Performance metrics and alerting
- **Batch Processing**: Handle multiple matching requests efficiently

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Mobile App    │    │  Backend API    │
│   Application   │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │              Educify API                    │
          │         (FastAPI + Authentication)          │
          └─────────┬───────────────────────┬───────────┘
                    │                       │
          ┌─────────▼───────────┐  ┌────────▼────────────┐
          │   Matching Engine   │  │   Training Pipeline │
          │   (scikit-learn)    │  │     (MLflow)        │
          └─────────┬───────────┘  └─────────┬───────────┘
                    │                        │
          ┌─────────▼────────────────────────▼───────────┐
          │              Data Layer                      │
          │  Redis (Cache) | PostgreSQL | S3 (Models)   │
          └─────────────────────────────────────────────┘
```

## Prerequisites

- **Docker & Docker Compose** (for local development)
- **Python 3.11+** (for direct installation)
- **Kubernetes** (for production deployment)
- **AWS Account** (for cloud deployment)

### System Requirements
- RAM: 4GB minimum, 8GB recommended
- Storage: 10GB free space
- CPU: 2+ cores recommended

## Installation

### Option 1: Docker Compose (Recommended for Development)

1. **Clone the repository**
```bash
git clone <repository-url>
cd educify
```

2. **Create required directories**
```bash
mkdir models data
```

3. **Generate training dataset**
```bash
python dataset_generator.py
```

4. **Configure environment**
```bash
# Create .env file
cat > .env << EOF
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://user:password@postgres:5432/matching_db
MLFLOW_TRACKING_URI=http://mlflow:5000
LOG_LEVEL=INFO
MODEL_RETRAIN_THRESHOLD=0.8
DB_PASSWORD=your_secure_password_here
AWS_REGION=us-west-2
EOF
```

5. **Start services**
```bash
docker-compose up -d --build
```

6. **Verify installation**
```bash
curl http://localhost:8000/health
```

### Option 2: Manual Installation

1. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

2. **Start Redis and PostgreSQL**
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15
```

3. **Generate dataset and run API**
```bash
python dataset_generator.py
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost:5432/matching_db` |
| `MLFLOW_TRACKING_URI` | MLflow server URL | `http://localhost:5000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MODEL_RETRAIN_THRESHOLD` | R² threshold for retraining | `0.8` |

### Docker Compose Services

| Service | Port | Purpose |
|---------|------|---------|
| `matching-api` | 8000 | Main API service |
| `training-service` | - | Model training pipeline |
| `redis` | 6379 | Caching layer |
| `postgres` | 5432 | Data storage |
| `mlflow` | 5000 | ML experiment tracking |

## Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": 1694627478.123,
  "teachers_loaded": 200,
  "model_ready": true
}
```

### Find Teacher Matches

```bash
curl -X POST http://localhost:8000/match-public \
  -H "Content-Type: application/json" \
  -d '{
    "id": "student_001",
    "subjects": ["mathematics", "physics"],
    "learning_style": "visual",
    "availability": ["morning", "evening"],
    "location_preference": "online",
    "budget_range": [25, 45],
    "experience_level": "intermediate",
    "age": 22
  }'
```

### Submit Feedback

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mk_test_key_dev" \
  -d '{
    "student_id": "student_001",
    "teacher_id": "t0001",
    "rating": 4.5,
    "lesson_completed": true,
    "feedback_text": "Excellent teacher!"
  }'
```

## API Documentation

### Authentication

All API endpoints (except public testing endpoints) require authentication via API key:

```http
X-API-Key: your_api_key_here
```

### Available API Keys (Development)

| Team | API Key | Rate Limit |
|------|---------|------------|
| Frontend | `mk_frontend_team_key123` | 1000/hour |
| Mobile | `mk_mobile_team_key456` | 500/hour |
| Analytics | `mk_analytics_team_key789` | 200/hour |
| Testing | `mk_test_key_dev` | 100/hour |

### Endpoints

#### POST /match
Find matching teachers for a student.

**Request Body:**
```json
{
  "id": "string",
  "subjects": ["string"],
  "learning_style": "visual|auditory|kinesthetic|reading",
  "availability": ["morning|afternoon|evening|weekend"],
  "location_preference": "online|in_person|both",
  "budget_range": [min_price, max_price],
  "experience_level": "beginner|intermediate|advanced",
  "preferred_teacher_gender": "male|female|any",
  "age": 18
}
```

**Response:**
```json
[
  {
    "teacher_id": "t0001",
    "student_id": "student_001",
    "compatibility_score": 0.89,
    "confidence": 0.76,
    "reasons": ["Teaches mathematics, physics", "Available during preferred times"],
    "teacher_details": {
      "id": "t0001",
      "subjects": ["mathematics", "physics"],
      "teaching_style": "visual",
      "availability": ["morning", "afternoon"],
      "location_preference": "online",
      "hourly_rate": 35.0,
      "experience_years": 8,
      "rating": 4.8,
      "total_students": 75,
      "specializations": ["calculus", "linear_algebra"],
      "gender": "female",
      "languages": ["english", "french"]
    }
  }
]
```

#### POST /feedback
Submit feedback for teacher-student interactions.

#### GET /teacher/{teacher_id}/stats
Get detailed statistics for a specific teacher.

#### Interactive API Documentation
Visit `http://localhost:8000/docs` for complete interactive API documentation.

## Integration Guide

### Frontend Integration (React/Vue/Angular)

```javascript
class EducifyAPI {
  constructor(apiKey, baseURL = 'https://api.educify.yourcompany.com') {
    this.apiKey = apiKey;
    this.baseURL = baseURL;
  }

  async findMatches(studentData) {
    const response = await fetch(`${this.baseURL}/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify(studentData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }

  async submitFeedback(feedbackData) {
    const response = await fetch(`${this.baseURL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify(feedbackData)
    });
    
    return await response.json();
  }
}

// Usage
const educify = new EducifyAPI('mk_frontend_team_key123');

const matches = await educify.findMatches({
  id: 'user_123',
  subjects: ['mathematics'],
  learning_style: 'visual',
  availability: ['evening'],
  location_preference: 'online',
  budget_range: [20, 50],
  experience_level: 'intermediate'
});
```

### Mobile App Integration (React Native/Flutter)

```dart
// Flutter example
class EducifyService {
  final String apiKey;
  final String baseUrl;
  
  EducifyService({required this.apiKey, this.baseUrl = 'https://api.educify.yourcompany.com'});
  
  Future<List<TeacherMatch>> findMatches(StudentRequest request) async {
    final response = await http.post(
      Uri.parse('$baseUrl/match'),
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: jsonEncode(request.toJson()),
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => TeacherMatch.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load matches');
    }
  }
}
```

### Backend System Integration (Node.js/Python/Java)

```python
# Python example
import requests
import json

class EducifyClient:
    def __init__(self, api_key, base_url="https://api.educify.yourcompany.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def find_matches(self, student_data, top_k=10):
        response = self.session.post(
            f"{self.base_url}/match",
            json=student_data,
            params={'top_k': top_k}
        )
        response.raise_for_status()
        return response.json()
    
    def submit_feedback(self, feedback_data):
        response = self.session.post(
            f"{self.base_url}/feedback",
            json=feedback_data
        )
        response.raise_for_status()
        return response.json()

# Usage
client = EducifyClient('mk_analytics_team_key789')
matches = client.find_matches({
    'id': 'student_456',
    'subjects': ['physics', 'chemistry'],
    'learning_style': 'hands_on',
    'availability': ['weekend'],
    'location_preference': 'both',
    'budget_range': [30, 60],
    'experience_level': 'advanced'
})
```

## Deployment

### Local Development
```bash
docker-compose up -d --build
```

### Production Deployment (AWS)

1. **Deploy Infrastructure**
```bash
cd terraform
terraform init
terraform apply -var="db_password=YourSecurePassword123!"
```

2. **Configure Kubernetes**
```bash
aws eks update-kubeconfig --region us-west-2 --name matching-cluster
```

3. **Deploy Application**
```bash
# Build and push images to ECR
./scripts/build-and-push.sh

# Deploy to Kubernetes
./scripts/deploy.sh
```

4. **Setup Monitoring**
```bash
./scripts/monitoring-setup.sh
```

### Environment-specific Configurations

#### Development
- Single replica
- Local storage
- Verbose logging
- Mock data acceptable

#### Staging
- 2-3 replicas
- Managed databases
- Production-like data
- Performance testing

#### Production
- Auto-scaling (2-20 replicas)
- High availability databases
- SSL/TLS encryption
- Comprehensive monitoring

## Monitoring

### Available Dashboards

1. **API Metrics**: `http://localhost:3000` (Grafana)
   - Request rates and response times
   - Error rates and status codes
   - Cache hit ratios

2. **Model Performance**: `http://localhost:5000` (MLflow)
   - Model accuracy metrics
   - Training history
   - Model versions and artifacts

3. **System Metrics**: `http://localhost:9090` (Prometheus)
   - Resource utilization
   - Database performance
   - Container health

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|---------|
| API Response Time | > 500ms | Scale up replicas |
| Model R² Score | < 0.8 | Trigger retraining |
| Error Rate | > 5% | Investigate logs |
| Cache Hit Ratio | < 80% | Optimize caching |
| Database CPU | > 80% | Scale database |

### Alerts Configuration

Critical alerts are configured for:
- API downtime (> 1 minute)
- High error rates (> 10%)
- Database connection failures
- Model performance degradation

## Contributing

### Development Setup

1. **Fork and clone the repository**
2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install development dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists
```

4. **Run tests**
```bash
pytest tests/ -v
```

### Code Standards

- **Python**: Follow PEP 8 style guide
- **API**: RESTful conventions
- **Documentation**: Docstrings for all functions
- **Testing**: Minimum 80% code coverage

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with appropriate tests
3. Update documentation if needed
4. Submit PR with clear description
5. Ensure all CI checks pass

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'matcher'
# Solution: Ensure all Python files are in the same directory
python -c "import sys; print(sys.path)"
```

#### Docker Build Failures
```bash
# Error: COPY models/ ./models/ - not found
# Solution: Create missing directories
mkdir models data
```

#### API Returns Empty Results
```bash
# Check if dataset exists
ls data/
# If missing, generate dataset
python dataset_generator.py
```

#### High Memory Usage
```bash
# Check container memory usage
docker stats
# Solution: Reduce batch sizes or increase container memory limits
```

#### Database Connection Issues
```bash
# Test database connectivity
docker-compose exec postgres psql -U user -d matching_db
# Check connection string in environment variables
```

### Debug Commands

```bash
# View container logs
docker-compose logs matching-api
docker-compose logs training-service

# Check service health
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Kubernetes debugging (production)
kubectl get pods -n matching-system
kubectl logs -f deployment/matching-api -n matching-system
kubectl describe pod <pod-name> -n matching-system
```

### Performance Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Slow API responses | Response time > 1s | Enable Redis caching, optimize queries |
| High CPU usage | CPU > 80% consistently | Scale horizontally, optimize algorithms |
| Memory leaks | Memory usage increasing over time | Review memory usage patterns, restart containers |
| Database locks | Slow database queries | Optimize indexes, review query patterns |

### Getting Help

1. **Check the logs first** - Most issues show up in container logs
2. **Verify configuration** - Ensure environment variables are set correctly
3. **Test components individually** - Isolate the failing component
4. **Check resource usage** - Monitor CPU, memory, and disk usage
5. **Review recent changes** - Check if recent deployments introduced issues

### Support Contacts

- **Technical Issues**: Create GitHub issue
- **Production Emergencies**: Contact DevOps team
- **API Questions**: Check `/docs` endpoint first
- **Integration Support**: Refer to integration examples above

---


## Changelog

### v1.0.0 (Current)
- Initial release with core matching functionality
- REST API with authentication
- Docker and Kubernetes deployment
- Basic monitoring and metrics

### Planned Features
- Advanced ML models (neural networks)
- Real-time notifications
- Multi-language support
- Advanced analytics dashboard
