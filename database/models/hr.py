from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime

class Employee(Base):
    __tablename__ = 'employees'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(50), unique=True, nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    father_husband_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    dob = Column(String(20), nullable=True)
    cnic = Column(String(50), nullable=True)
    blood_group = Column(String(10), nullable=True)
    marital_status = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    alt_phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    photo_path = Column(String(500), nullable=True)
    
    # Emergency Contact
    emergency_name = Column(String(100), nullable=True)
    emergency_phone = Column(String(50), nullable=True)
    emergency_rel = Column(String(50), nullable=True)

    # Employment Details
    emp_type = Column(String(50), default="Teacher")  # Teacher, Principal, Admin, Clerk, Support, etc.
    department = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    joining_date = Column(String(20), nullable=True)
    status = Column(String(50), default="Active")  # Active, Inactive, Resigned, Terminated, Retired, On Leave
    employment_type = Column(String(50), default="Permanent")  # Permanent, Contract, Visiting, Part-time
    contract_start = Column(String(20), nullable=True)
    contract_end = Column(String(20), nullable=True)
    experience = Column(String(100), nullable=True)
    previous_employer = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    # Salary & Allowances
    basic_salary = Column(Float, default=0.0)
    house_allowance = Column(Float, default=0.0)
    medical_allowance = Column(Float, default=0.0)
    transport_allowance = Column(Float, default=0.0)
    other_allowance = Column(Float, default=0.0)
    tax_deduction = Column(Float, default=0.0)
    
    # Banking
    bank_name = Column(String(100), nullable=True)
    account_no = Column(String(100), nullable=True)
    iban = Column(String(100), nullable=True)
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    qualifications = relationship("EmployeeQualification", back_populates="employee", cascade="all, delete-orphan")
    assignments = relationship("TeacherAssignment", back_populates="employee", cascade="all, delete-orphan")
    attendance = relationship("StaffAttendance", back_populates="employee", cascade="all, delete-orphan")
    payroll = relationship("PayrollRecord", back_populates="employee", cascade="all, delete-orphan")

    @property
    def name(self):
        f = self.first_name or ""
        l = self.last_name or ""
        return f"{f} {l}".strip() or "Employee"

    @property
    def full_name(self):
        return self.name

    @property
    def qualification(self):
        if hasattr(self, 'qualifications') and self.qualifications:
            degrees = [q.degree for q in self.qualifications if getattr(q, 'degree', None)]
            if degrees:
                return ", ".join(degrees)
        return ""

    @qualification.setter
    def qualification(self, val):
        if not val:
            return
        if hasattr(self, 'qualifications') and self.qualifications:
            self.qualifications[0].degree = str(val)
        else:
            qual_cls = globals().get('EmployeeQualification')
            if qual_cls:
                self.qualifications = [qual_cls(degree=str(val))]


class EmployeeQualification(Base):
    __tablename__ = 'employee_qualifications'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    degree = Column(String(150), nullable=False)
    major_subject = Column(String(150), nullable=True)
    institution = Column(String(200), nullable=True)
    passing_year = Column(String(20), nullable=True)
    grade_marks = Column(String(50), nullable=True)
    notes = Column(String(255), nullable=True)

    employee = relationship("Employee", back_populates="qualifications")


class TeacherAssignment(Base):
    __tablename__ = 'teacher_assignments'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey('academic_classes.id', ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey('academic_sections.id', ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey('academic_subjects.id', ondelete="CASCADE"), nullable=False)
    academic_session = Column(String(50), nullable=False)
    periods_per_week = Column(Integer, default=5)

    employee = relationship("Employee", back_populates="assignments")
    academic_class = relationship("database.models.academic.AcademicClass")
    academic_section = relationship("database.models.academic.AcademicSection")
    academic_subject = relationship("database.models.academic.AcademicSubject")


class StaffAttendance(Base):
    __tablename__ = 'staff_attendance'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    date = Column(String(20), nullable=False)
    status = Column(String(20), default="Present")  # Present, Absent, Late, Half Day, Leave, Holiday
    remarks = Column(String(255), nullable=True)

    employee = relationship("Employee", back_populates="attendance")


class PayrollRecord(Base):
    __tablename__ = 'payroll_records'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_no = Column(String(50), unique=True, nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    
    pay_month = Column(String(50), nullable=False)
    basic_salary = Column(Float, default=0.0)
    allowances = Column(Float, default=0.0)
    bonus = Column(Float, default=0.0)
    overtime = Column(Float, default=0.0)
    gross_salary = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    advance = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    net_salary = Column(Float, default=0.0)
    
    status = Column(String(50), default="Pending")  # Pending, Paid, Partially Paid
    payment_date = Column(String(20), nullable=True)
    payment_method = Column(String(50), nullable=True)
    notes = Column(String(255), nullable=True)
    
    employee = relationship("Employee", back_populates="payroll")