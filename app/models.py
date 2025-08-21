from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for many-to-many relationship between Researcher and Publications
researcher_publication_association = Table(
    "Researcher_publication_association",
    Base.metadata,
    Column("researcher_id", Integer, ForeignKey("Researchers.id"), primary_key=True),
    Column("publication_id", Integer, ForeignKey("Publications.id"), primary_key=True)
)

class Researchers(Base):
    __tablename__ = "Researchers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    university = Column(String, nullable=False)
    profile_url = Column(String, nullable=True)
    publication = relationship(
        "Publications",
        secondary="Researcher_publication_association",
        back_populates="researcher"
    )

class Journals(Base):
    __tablename__ = "Journals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    abdc_rank = Column(String, nullable=True)
    impact_factor = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    publication = relationship("Publications", back_populates="journal")

class Publications(Base):
    __tablename__ = "Publications"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    publication_type = Column(String, nullable=True)
    publication_url = Column(String, nullable=True)
    journal_name = Column(String, nullable=True)
    researcher_id = Column(Integer, ForeignKey("Researchers.id"), nullable=False)
    journal_id = Column(Integer, ForeignKey("Journals.id"), nullable=True)
    researcher = relationship(
        "Researchers",
        secondary="Researcher_publication_association",
        back_populates="publication"
    )
    journal = relationship("Journals", back_populates="publication")