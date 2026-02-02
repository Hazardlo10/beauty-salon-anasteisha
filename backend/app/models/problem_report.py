"""
Модель сообщения о проблеме
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from ..database import Base


class ProblemReport(Base):
    """Сообщение о проблеме с сайтом"""

    __tablename__ = "problem_reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    problem_type = Column(String(50), nullable=False)  # bug, suggestion, question, other
    description = Column(Text, nullable=False)
    page_url = Column(String(500), nullable=True)
    status = Column(String(20), default="new")  # new, in_progress, resolved
    telegram_sent = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<ProblemReport {self.problem_type} - {self.status}>"
