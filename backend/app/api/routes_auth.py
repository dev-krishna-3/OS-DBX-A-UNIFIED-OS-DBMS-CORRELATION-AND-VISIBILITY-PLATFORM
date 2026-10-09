"""Authentication routes."""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import mysql.connector

from app.config.database import get_connection
from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    get_user_by_username,
    verify_password,
    get_current_active_user
)
from app.models.users import Token, UserCreate, UserOut, UserInDB

router = APIRouter(prefix="/auth", tags=["auth"])

def get_dbms_connection():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate, 
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """Register a new user in the system."""
    existing_user = get_user_by_username(connection, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, uid_linux, password_hash)
            VALUES (%s, %s, %s)
            """,
            (user_in.username, user_in.uid_linux, hashed_password)
        )
        connection.commit()
        user_id = cursor.lastrowid
        cursor.close()
        
        # Fetch the newly created user
        new_user = get_user_by_username(connection, user_in.username)
        return new_user
    except mysql.connector.Error as err:
        if err.errno == 1062: # Duplicate entry (maybe uid_linux)
            raise HTTPException(status_code=400, detail="UID Linux or Username already exists")
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/token", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    connection: mysql.connector.MySQLConnection = Depends(get_dbms_connection)
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    user = get_user_by_username(connection, username=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Any:
    """Get current user details."""
    return current_user
