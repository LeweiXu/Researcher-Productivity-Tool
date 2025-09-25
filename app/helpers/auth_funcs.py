from app.models import Users
from sqlalchemy.orm import Session
import bcrypt
from app.database import SessionLocal

def create_user(username: str, email: str, password: str):
    db = SessionLocal()
    try:
        # Hash and salt the password
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = Users(username=username, email=email, hashed_password=hashed_pw.decode('utf-8'))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()

def authenticate_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(Users).filter(Users.username == username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
            return True
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Example usage: create a user
    create_user("yuanji.wen", "yuanji.wen@uwa.edu.au", "Group18IsGreat")