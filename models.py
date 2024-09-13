from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta

# Database setup
engine = create_engine('sqlite:///pets.db')
Base = declarative_base()

# Model for recording feedings
class Feed(Base):
    __tablename__ = 'feeds'
    id = Column(Integer, primary_key=True)
    pet_id = Column(Integer, ForeignKey('pets.id'))
    feed_time = Column(DateTime, default=datetime.utcnow)

# Model for pets
class Pet(Base):
    __tablename__ = 'pets'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    photo = Column(String)
    feed_count = Column(Integer, default=0)
    experience = Column(Integer, default=0)
    level = Column(String, default="Nováčik")
    feeds = relationship("Feed", backref="pet")  # Relationship with the Feed model
    tasks = relationship("Task", back_populates="pet")

    def update_level(self):
        # Determine the level based on experience
        if self.experience >= 150:
            self.level = "Legendu zvieraťa"
        elif self.experience >= 120:
            self.level = "Veterán"
        elif self.experience >= 100:
            self.level = "Majster kŕmenia"
        elif self.experience >= 80:
            self.level = "Mladý hrdina"
        elif self.experience >= 60:
            self.level = "Hľadač pokladov"
        elif self.experience >= 40:
            self.level = "Dobrodruh"
        elif self.experience >= 30:
            self.level = "Mladý majster"
        elif self.experience >= 20:
            self.level = "Prieskumník"
        elif self.experience >= 10:
            self.level = "Zvedavec"
        else:
            self.level = "Nováčik"

    def feed_statistics(self, period):
        now = datetime.utcnow()
        if period == 'day':
            start_time = now - timedelta(days=1)
        elif period == 'week':
            start_time = now - timedelta(weeks=1)
        elif period == 'month':
            start_time = now - timedelta(days=30)
        else:
            start_time = datetime.min

        return len([feed for feed in self.feeds if feed.feed_time >= start_time])

# Model for tasks
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    hour = Column(Integer)
    minute = Column(Integer)
    pet_id = Column(Integer, ForeignKey('pets.id'))
    pet = relationship("Pet", back_populates="tasks")

# Create tables
Base.metadata.create_all(engine)

# Session setup
Session = sessionmaker(bind=engine)
session = Session()
