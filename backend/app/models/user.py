from sqlalchemy import Column, Integer, String, Boolean
from app.db.mysql_base import Base
import enum

from app.utils.timezone import beijing_time_now


class User(Base):
    """User model for authentication and profile data"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # User ID, primary key
    username = Column(
        String(50), unique=True, index=True, nullable=False
    )  # Username, unique
    email = Column(String(100), unique=True, index=True, nullable=False)  # Email, unique
    hashed_password = Column(String(100), nullable=False)  # Hashed password
    password_migration_required = Column(Boolean, default=True, nullable=False)  # Password migration flag


    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
