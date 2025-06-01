from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    file_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    hash = Column(String(64), unique=True, nullable=False)
    processed = Column(Boolean, default=False)
    splitter_method = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    image = relationship("Image", back_populates="file", uselist=False, cascade="all, delete-orphan")

class Image(Base):
    __tablename__ = 'images'

    file_id = Column(Integer, ForeignKey('files.id', ondelete="CASCADE"), primary_key=True)
    width = Column(Integer)
    height = Column(Integer)
    thumbnail = Column(LargeBinary)
    caption = Column(String)

    file = relationship("File", back_populates="image")


class Dialog(Base):
    __tablename__ = 'dialogs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    user_text = Column(String, nullable=False)
    assistant_text = Column(String, nullable=False)