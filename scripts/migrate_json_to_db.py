import json
import uuid
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from webservice.models import Profile, Conversation, Message

def main():
    """
    Migrates existing JSON data from profiles.json and conversations.json into the SQLite database. 
    Runs once as a one-time migration script.
    """
    engine = create_engine("sqlite:////app/data/gophergpt.db")
    session = Session(engine)

    with open("webservice/data/profiles.json") as file:
        profiles = json.load(file)

    for user_id, data in profiles.items():
        session.add(Profile(user_id=user_id, 
                            major=data.get("major"),
                            level=data.get("level"),
                            year=data.get("year"),
                            personalization_notes=data.get("personalization_notes")
                            ))
        
    with open("webservice/data/conversations.json") as file:
        conversations = json.load(file)

    for conv in conversations:
        session.add(Conversation(id=str(conv["id"]),
                                title=conv["title"],
                                ))
        
        for msg in conv["messages"]:
            session.add(Message(id=str(uuid.uuid4()),
                                role="user" if msg["isUser"] else "agent",
                                text=msg["text"],
                                content=msg["content"],
                                created_at=datetime.datetime.fromtimestamp(conv["id"] / 1000),
                                conversation_id=str(conv["id"])
                                ))

    session.commit()
    session.close()


if __name__ == '__main__':
    main()