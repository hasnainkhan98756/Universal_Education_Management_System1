from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime

class Student(Base):
    __tablename__ = 'students'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(50), unique=True, nullable=False) 
    admission_number = Column(String(50), nullable=True)
    enrollment_number = Column(String(50), nullable=True)
    
    # 1. Personal Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    dob = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    nationality = Column(String(50), default="Pakistani")
    religion = Column(String(50), nullable=True)
    place_of_birth = Column(String(100), nullable=True)
    b_form = Column(String(50), nullable=True)
    photo_path = Column(String(500), nullable=True)

    # 2. Contact & Address
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    current_address = Column(String(500), nullable=True)
    permanent_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    
    # 3. Parent / Guardian Info
    father_name = Column(String(100), nullable=True)
    father_cnic = Column(String(50), nullable=True)
    father_phone = Column(String(20), nullable=True)
    father_occupation = Column(String(100), nullable=True)
    
    mother_name = Column(String(100), nullable=True)
    mother_cnic = Column(String(50), nullable=True)
    
    guardian_name = Column(String(100), nullable=True)
    guardian_cnic = Column(String(50), nullable=True)
    guardian_relationship = Column(String(50), nullable=True)
    guardian_phone = Column(String(20), nullable=True)
    family_income = Column(String(50), nullable=True)
    
    # 4. Emergency & Medical
    emergency_contact_person = Column(String(100), nullable=True)
    emergency_relationship = Column(String(50), nullable=True)
    emergency_contact_number = Column(String(50), nullable=True)
    medical_notes = Column(String(500), nullable=True)
    allergies = Column(String(500), nullable=True)
    
    # 5. Previous Education
    previous_school = Column(String(200), nullable=True)
    previous_class = Column(String(50), nullable=True)
    previous_exam = Column(String(50), nullable=True)
    previous_session = Column(String(50), nullable=True)
    previous_result = Column(String(50), nullable=True)
    tc_number = Column(String(50), nullable=True)
    tc_date = Column(String(50), nullable=True)
    
    # 6. Siblings
    sibling_info = Column(String(500), nullable=True)

    # 7. Academic Foundation Links
    academic_session = Column(String(50), nullable=False)
    class_id = Column(Integer, ForeignKey('academic_classes.id', ondelete="SET NULL"), nullable=True)
    section_id = Column(Integer, ForeignKey('academic_sections.id', ondelete="SET NULL"), nullable=True)
    admission_date = Column(String(20), nullable=True)
    admission_type = Column(String(50), nullable=True) # New, Transfer, Re-Admission
    status = Column(String(50), default="Active") 

    # 8. Fees
    monthly_fee = Column(Float, default=0.0)
    six_month_fee = Column(Float, default=0.0)
    annual_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    admission_fee = Column(Float, default=0.0)
    admission_fee_paid = Column(Boolean, default=False)
    billing_cycle = Column(String(50), default="Monthly") # Monthly, 6-Month, Annual
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    academic_class = relationship("database.models.academic.AcademicClass")
    academic_section = relationship("database.models.academic.AcademicSection")

    @property
    def name(self):
        f = self.first_name or ""
        l = self.last_name or ""
        return f"{f} {l}".strip() or "Student"

    @property
    def full_name(self):
        return self.name