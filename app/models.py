from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, Table
from sqlalchemy.orm import relationship
from app.database import Base  # <-- Import Base from main.py

# Association table for many-to-many relationship between Researcher and Article
researcher_article_association = Table(
    "researcher_article_association",
    Base.metadata,
    Column("researcher_id", Integer, ForeignKey("researchers.id"), primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True)
)

class Researcher(Base):
    __tablename__ = "researchers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    university = Column(String, nullable=False)
    profile_url = Column(String, nullable=True)
    articles = relationship(
        "Article",
        secondary="researcher_article_association",
        back_populates="researchers"
    )

class Journal(Base):
    __tablename__ = "journals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    abdc_rank = Column(String, nullable=True)
    impact_factor = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    articles = relationship("Article", back_populates="journal")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    article_type = Column(String, nullable=True)
    article_url = Column(String, nullable=False)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=True)
    researchers = relationship(
        "Researcher",
        secondary="researcher_article_association",
        back_populates="articles"
    )
    journal = relationship("Journal", back_populates="articles")