# 🎓 Student-Teacher Matching System

Production-ready matching system with real API integration.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file:
```env
DATA_SOURCE=api
API_KEY=mirzaKey
```

### 3. Run
```bash
uvicorn app.main:app --reload
```

### 4. Test
Open http://localhost:8000/docs

## 📡 API Endpoints

### Match Student to Teachers
```bash
POST /api/v1/match
{
  "student_id": "S001",
  "subject": "Mathematics"
}
```

### Get Teachers
```bash
GET /api/v1/teachers?subject=Mathematics&min_rating=4.5
```

### Get Student
```bash
GET /api/v1/students/{id}
```

## 🔧 Configuration

### Use Real API
```env
DATA_SOURCE=api
API_KEY=mirzaKey
```

### Use Local Mock Data
```env
DATA_SOURCE=local
```

## 🐳 Docker

### Build and Run
```bash
docker-compose up --build
```

### Or manually
```bash
docker build -t matching-system .
docker run -p 8000:8000 matching-system
```

## 🧪 Testing

```bash
pytest tests/
```

## 📊 Architecture

```
app/
├── main.py              # FastAPI application
├── models/              # Pydantic models
│   ├── student.py
│   ├── teacher.py
│   └── match.py
├── services/            # Business logic
│   ├── data_service.py      # API/data access
│   └── matching_service.py  # Matching algorithm
├── api/                 # API routes
│   └── routes.py
├── core/                # Configuration
│   ├── config.py
│   └── logging.py
└── data/                # Mock data (fallback)
    ├── students.json
    └── teachers.json
```

## 🎯 Features

✅ Real API integration with http://api.staging.educify.org
✅ Smart matching algorithm (subject + budget + availability)
✅ Returns top 3 teachers (configurable)
✅ Automatic booking creation
✅ Fallback to local data if API fails
✅ Comprehensive logging
✅ Docker support
✅ Test suite included
✅ ML-ready architecture

## 🔮 Future Enhancements

- ML-based teacher recommendations
- Real-time availability updates
- Payment integration
- Student feedback system
- Advanced filtering options

## 📞 Support

For issues or questions, check the logs in `logs/` directory.

## 🙏 Credits

Built with FastAPI, Pydantic, and httpx