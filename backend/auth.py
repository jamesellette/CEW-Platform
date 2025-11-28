"""
Authentication and authorization module for CEW Training Platform.
Implements JWT-based authentication with role-based access control.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import os

# Security configuration
# In production, set CEW_SECRET_KEY environment variable
SECRET_KEY = os.environ.get("CEW_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


# ============ Models ============

class UserRole:
    """User roles for RBAC."""
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    TRAINEE = "trainee"


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = UserRole.TRAINEE
    disabled: bool = False


class UserInDB(User):
    """User model with hashed password for database storage."""
    hashed_password: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """User creation request model."""
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = UserRole.TRAINEE


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


# ============ In-Memory User Store ============
# In production, replace with a real database

users_db: dict[str, UserInDB] = {}


def _init_default_users():
    """Initialize default users for development."""
    default_users = [
        UserCreate(
            username="admin",
            password="admin123",
            email="admin@cew-training.local",
            full_name="System Administrator",
            role=UserRole.ADMIN
        ),
        UserCreate(
            username="instructor",
            password="instructor123",
            email="instructor@cew-training.local",
            full_name="Training Instructor",
            role=UserRole.INSTRUCTOR
        ),
        UserCreate(
            username="trainee",
            password="trainee123",
            email="trainee@cew-training.local",
            full_name="Training Participant",
            role=UserRole.TRAINEE
        ),
    ]
    for user in default_users:
        if user.username not in users_db:
            create_user(user)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_user(user_data: UserCreate) -> User:
    """Create a new user."""
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    user_in_db = UserInDB(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        hashed_password=hashed_password
    )
    users_db[user_data.username] = user_in_db
    return User(**user_in_db.model_dump(exclude={"hashed_password"}))


def get_user(username: str) -> Optional[UserInDB]:
    """Get a user by username."""
    return users_db.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user by username and password."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get the current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return User(**user.model_dump(exclude={"hashed_password"}))


def require_role(allowed_roles: list[str]):
    """Dependency to require specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def list_users() -> list[User]:
    """List all users (excluding passwords)."""
    return [
        User(**user.model_dump(exclude={"hashed_password"}))
        for user in users_db.values()
    ]


def delete_user(username: str) -> bool:
    """Delete a user by username."""
    if username in users_db:
        del users_db[username]
        return True
    return False


# Initialize default users on module load
_init_default_users()
