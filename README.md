# Student-Teacher Matching System

A production-ready, scalable system for matching students with teachers based on subject, availability, budget, and ratings. Built with FastAPI and designed for easy ML integration.

## 🚀 Features

- **Smart Matching Algorithm**: Filters by subject, budget, and availability, then ranks by rating and experience
- **Top N Matches**: Returns top 3 teachers (configurable) like Uber shows nearby drivers
- **RESTful API**: Clean endpoints for matching, teacher listing, and student profiles
- **Modular Architecture**: Easily extensible for ML models, payment systems, and more
- **Mock Data Ready**: Works with local JSON, ready to connect to real APIs/databases
- **Production Ready**: Docker support, logging, error handling, and health checks
- **ML Hooks**: Designed to integrate machine learning models for personalized recommendations

## 📁 Project Structure

```
/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── models/                 # Pydantic data models
│   │   ├── student.py
│   │   ├── teacher.py
│   │   └── match.py
│   ├── services/               # Business logic
│   │   ├── matching_service.py # Core matching algorithm
│   │   └── data_service.py     # Data access abstraction
│   ├── api/                    # API routes
│   │   └── routes.py
│   ├── core/                   # Configuration & utilities
│   │   ├── config.py
│   │   └── logging.py
│   └── data/                   # Mock data (JSON files)
│       ├── students.json
│       └── teachers.json
├── tests/                      # Test suite
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── requirements.txt            # Python dependencies
└── README.md
```

## 🛠️ Installation & Setup

### Local Development

1. **Clone and navigate to project**:
```bash
cd student-teacher-matching
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Create environment file**:
```bash
cp .env.example .env
```

5. **Create data files**:
Create `app/data/students.json` and `app/data/teachers.json` with the sample data provided in the code.

6. **Create logs directory**:
```bash
mkdir logs
```

7. **Run the application**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Access the API**:
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health

### Docker Deployment

1. **Build and run with Docker Compose**:
```bash
docker-compose up --build
```

2. **Or build manually**:
```bash
docker build -t teacher-matching .
docker run -p 8000:8000 teacher-matching
```

## 📡 API Endpoints

### 1. Match Student to Teachers
```http
POST /api/v1/match
Content-Type: application/json

{
  "student_id": "S001",
  "subject": "Mathematics",
  "preferred_time_slots": [
    {
      "day": "Monday",
      "start_time": "14:00",
      "end_time": "16:00"
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "student_id": "S001",
  "subject": "Mathematics",
  "matches": [
    {
      "teacher": {
        "id": "T001",
        "name": "Dr. Jane Smith",
        "rating": 4.8,
        "hourly_rate": 45.0,
        "experience_years": 8
      },
      "score": {
        "overall_score": 92.5,
        "rating_score": 96.0,
        "availability_score": 85.0
      },
      "matching_subjects": ["Mathematics"],
      "matching_time_slots": [...],
      "recommended_reason": "Highly rated (4.8/5.0) • 8 years experience"
    }
  ],
  "total_matches": 3,
  "timestamp": "2025-10-01T14:30:00"
}
```

### 2. Get All Teachers (with filters)
```http
GET /api/v1/teachers?subject=Mathematics&min_rating=4.5&max_rate=50
```

### 3. Get Student Profile
```http
GET /api/v1/students/S001
```

### 4. Health Check
```http
GET /api/v1/health
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_matching_service.py -v
```

## ⚙️ Configuration

Edit `.env` file to customize:

```env
# Return top 5 matches instead of 3
MAX_MATCHES=5

# Adjust scoring weights
RATING_WEIGHT=0.7
AVAILABILITY_WEIGHT=0.3

# Change data source (future: api, database)
DATA_SOURCE=local
```

## 🔮 Future Enhancements

### ML Integration Ready
The system is designed for easy ML integration:

```python
# In matching_service.py - replace _calculate_match_score with:

def _calculate_match_score_ml(self, student, teacher, matching_slots):
    """Use ML model for scoring"""
    features = self._extract_features(student, teacher, matching_slots)
    prediction = self.ml_model.predict(features)
    return prediction
```

### Recommended Next Steps

1. **Database Integration**: Replace JSON with PostgreSQL/MongoDB
   - Update `data_service.py` to use SQLAlchemy or motor
   
2. **ML Recommendation System**:
   - Collect match history data
   - Train model on successful matches
   - Replace rule-based scoring with ML predictions

3. **Payment Integration**:
   - Add Stripe/PayPal endpoints
   - Track bookings and payments

4. **Real-time Features**:
   - WebSocket for live availability
   - Notification system for new matches

5. **Advanced Filtering**:
   - Learning style compatibility
   - Student performance tracking
   - Teacher specializations

## 🏗️ Architecture Decisions

### Why This Structure?

1. **Service Layer Pattern**: Separates business logic from API routes
2. **Data Abstraction**: Easy to swap JSON → API → Database
3. **Pydantic Models**: Type safety and automatic validation
4. **Async Ready**: All services use async/await for scalability
5. **Dependency Injection**: Easy to mock services for testing

### Matching Algorithm

Current algorithm (rule-based):
1. Filter by subject match
2. Filter by budget constraints
3. Filter by availability overlap
4. Score remaining candidates (rating + availability)
5. Return top N sorted by score

**ML Upgrade Path**: Replace step 4 with trained model that learns from:
- Historical match success rates
- Student feedback scores
- Session completion rates
- Re-booking patterns

## 📊 Sample Data

The system includes sample data for 2 students and 4 teachers covering:
- Mathematics, Physics, Chemistry, Biology, Computer Science
- Various availability patterns
- Different price points ($38-$55/hour)
- Rating range (4.6-4.9)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - feel free to use in your projects

## 🆘 Troubleshooting

**Issue**: ModuleNotFoundError
```bash
# Ensure you're in project root and virtual env is activated
pip install -r requirements.txt
```

**Issue**: Port already in use
```bash
# Change port in .env or use different port
uvicorn app.main:app --port 8001
```

**Issue**: No matches found
- Check student budget vs teacher rates
- Verify availability overlap exists
- Confirm subject is in teacher's subjects list

## 📞 Support

For issues, feature requests, or questions:
- Open a GitHub issue
- Check API documentation at `/docs`
- Review logs in `logs/` directory

---

**Built with ❤️ for Educify**