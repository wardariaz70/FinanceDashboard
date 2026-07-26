import bcrypt
from sqlalchemy.orm import Session
from models import User


# 1. Password Hashing & Verification
def hash_password(password: str) -> str:
    """Hashes a raw password string."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# 2. Authenticate User
def authenticate_user(db: Session, username: str, password: str):
    """Checks if user exists and password is correct."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


# 3. Helper to Seed Initial Admin User
def create_initial_admin(db: Session):
    """Creates a default admin user if no users exist in the DB."""
    admin_exists = db.query(User).filter(User.username == "admin").first()
    if not admin_exists:
        hashed_pwd = hash_password("admin123")  # Default password
        admin_user = User(
            username="admin", password=hashed_pwd, role="Finance"
        )
        db.add(admin_user)
        db.commit()
        print("Default admin created (Username: admin, Password: admin123)")