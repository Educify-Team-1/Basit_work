from fastapi import FastAPI


app = FastAPI()


@app.post('/teacher-match')
async def generate_teacher_recommendations():
    """returns a list of recommended teachers for a student"""


@app.get('/healt-check')
async def healthcheck():
    return {
        "output": "Student-Teacher API is active!"
    }
