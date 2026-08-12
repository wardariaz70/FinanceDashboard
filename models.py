from datetime import date
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from database import Base, engine


# Association Table for Many-to-Many relationship between BudgetHead and Section
budget_head_sections = Table(
    "budget_head_sections",
    Base.metadata,
    Column("budget_head_id", Integer, ForeignKey("budget_heads.id"), primary_key=True),
    Column("section_id", Integer, ForeignKey("sections.id"), primary_key=True),
)


# 1. Users Table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(
        String(20), nullable=False, default="Section"
    )  # 'Finance' or 'Section'

    # Optional foreign key for Section users
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    section = relationship("Section", back_populates="users")


# 2. Sections Table
class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="section")
    releases = relationship("FundRelease", back_populates="section")
    expenditures = relationship("Expenditure", back_populates="section")
    budget_heads = relationship(
        "BudgetHead", secondary=budget_head_sections, back_populates="sections"
    )


# 3. Budget Heads Table
class BudgetHead(Base):
    __tablename__ = "budget_heads"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=False)

    releases = relationship("FundRelease", back_populates="budget_head")
    expenditures = relationship("Expenditure", back_populates="budget_head")
    sections = relationship(
        "Section", secondary=budget_head_sections, back_populates="budget_heads"
    )


# 4. Fund Release Table
class FundRelease(Base):
    __tablename__ = "fund_releases"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    budget_head_id = Column(
        Integer, ForeignKey("budget_heads.id"), nullable=False
    )
    amount = Column(Float, nullable=False)
    release_date = Column(Date, default=date.today)

    section = relationship("Section", back_populates="releases")
    budget_head = relationship("BudgetHead", back_populates="releases")


# 5. Expenditure Table
# Inside models.py -> Expenditure class

class Expenditure(Base):
    __tablename__ = "expenditures"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    budget_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=False)
    amount = Column(Float, nullable=False)
    purpose = Column(String(255), nullable=False)
    bill_no = Column(String(50), nullable=False)
    expenditure_date = Column(Date, default=date.today)
    invoice_path = Column(String(255), nullable=True)  # <--- New field added!

    section = relationship("Section", back_populates="expenditures")
    budget_head = relationship("BudgetHead", back_populates="expenditures")


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database synced successfully!")