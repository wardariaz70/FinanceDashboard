from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from database import Base, engine


# Association Table for Many-to-Many relationship between BudgetHead and Section
budget_head_sections = Table(
    "budget_head_sections",
    Base.metadata,
    Column("budget_head_id", Integer, ForeignKey("budget_heads.id"), primary_key=True),
    Column("section_id", Integer, ForeignKey("sections.id"), primary_key=True),
    extend_existing=True,
)


# 1. Users Table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(
        String(20), nullable=False, default="Section"
    )  # 'Finance', 'Section', 'Secretary', 'DDO'

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
    category = Column(String(20), nullable=False, default="ERE")  # 'ERE' or 'NON-ERE'
    base_allocation = Column(Float, nullable=False, default=0.0)

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
    released_by = Column(String(100), nullable=False, default="admin")
    release_timestamp = Column(DateTime, default=datetime.now)

    section = relationship("Section", back_populates="releases")
    budget_head = relationship("BudgetHead", back_populates="releases")


# 5. Expenditure Table
class Expenditure(Base):
    __tablename__ = "expenditures"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    budget_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=False)
    amount = Column(Float, nullable=False)
    purpose = Column(String(255), nullable=False)
    bill_no = Column(String(50), nullable=False)
    expenditure_date = Column(Date, default=date.today)
    invoice_path = Column(String(255), nullable=True)

    # DDO Scrutiny Fields
    ddo_status = Column(String(50), nullable=False, default="PENDING")  # 'AUTHORISED', 'REJECTED', 'OBJECTION', 'PENDING'
    ddo_remarks = Column(String(255), nullable=True)
    ddo_action_date = Column(Date, nullable=True)

    # Source Work Order Linkage (if converted)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)

    section = relationship("Section", back_populates="expenditures")
    budget_head = relationship("BudgetHead", back_populates="expenditures")
    work_order = relationship("WorkOrder")


# 6. Reappropriation Table (Re+ / Re-)
class Reappropriation(Base):
    __tablename__ = "reappropriations"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    source_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=True)
    target_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=True)
    amount = Column(Float, nullable=False)
    reap_type = Column(String(10), nullable=False)  # 'IN' or 'OUT'
    reason = Column(String(255), nullable=True)
    created_by = Column(String(100), nullable=False, default="admin")
    reap_date = Column(Date, default=date.today)

    section = relationship("Section")
    source_head = relationship("BudgetHead", foreign_keys=[source_head_id])
    target_head = relationship("BudgetHead", foreign_keys=[target_head_id])


# 7. Work Orders Table (Committed Expenses)
class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    budget_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=False)
    order_no = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    vendor_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    order_date = Column(Date, default=date.today)
    status = Column(String(50), nullable=False, default="Pending Expenditure")  # 'Pending Expenditure', 'Converted', 'Cancelled'
    created_by = Column(String(100), nullable=False, default="admin")

    section = relationship("Section")
    budget_head = relationship("BudgetHead")


# 8. Base Allocation Deposit Logs Table
class BaseAllocationLog(Base):
    __tablename__ = "base_allocation_logs"

    id = Column(Integer, primary_key=True, index=True)
    budget_head_id = Column(Integer, ForeignKey("budget_heads.id"), nullable=True)
    amount = Column(Float, nullable=False)
    allocated_by = Column(String(100), nullable=False, default="admin")
    allocation_date = Column(Date, default=date.today)
    notes = Column(String(255), nullable=True)

    budget_head = relationship("BudgetHead")


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database synced successfully!")