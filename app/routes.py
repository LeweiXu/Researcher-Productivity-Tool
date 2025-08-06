from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Welcome to the G8 Research Portal"}

@router.get("/hello")
def say_hello():
    return {"message": "Hello from routes!"}
