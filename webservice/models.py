from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy import String, DateTime, JSON, ForeignKey

class Base(DeclarativeBase):
    pass

class Profile(Base):
    """
    stores a user's academic information used to personalize responses
    """

    __tablename__ = "profiles"

    user_id = mapped_column(String, primary_key=True)
    major = mapped_column(String, nullable=True)
    level = mapped_column(String, nullable=True)
    year = mapped_column(String, nullable=True)
    personalization_notes = mapped_column(String, nullable=True)

class Conversation(Base):
    """
    represents a single chat session, optionally tied to a profile
    """

    __tablename__ = "conversations"

    id = mapped_column(String, primary_key=True)
    title = mapped_column(String, nullable=True)
    profile_id = mapped_column(String, ForeignKey("profiles.user_id"), nullable=True)

class Message(Base):
    """
    a single message within a conversation, sent by either the user or the agent
    """
    
    __tablename__ = "messages"

    id = mapped_column(String, primary_key=True)
    role = mapped_column(String, nullable=False)
    text = mapped_column(String, nullable=False)
    content = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime, nullable=False)
    conversation_id = mapped_column(String, ForeignKey("conversations.id"), nullable=False)
