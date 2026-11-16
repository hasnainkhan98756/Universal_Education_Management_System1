from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.models.base import Base


class TransportRoute(Base):
    __tablename__ = 'transport_routes'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    route_name      = Column(String(200), nullable=False)
    start_point     = Column(String(200), default="")
    end_point       = Column(String(200), default="")
    stops           = Column(Text, default="")
    monthly_fee     = Column(Float, default=0.0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.now)
    vehicles            = relationship("TransportVehicle", back_populates="route", cascade="all, delete-orphan")
    student_assignments = relationship("StudentTransport", back_populates="route", cascade="all, delete-orphan")


class TransportVehicle(Base):
    __tablename__ = 'transport_vehicles'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_number  = Column(String(50), nullable=False)
    vehicle_type    = Column(String(50), default="Bus")
    capacity        = Column(Integer, default=30)
    driver_name     = Column(String(200), default="")
    driver_phone    = Column(String(50), default="")
    driver_license  = Column(String(100), default="")
    route_id        = Column(Integer, ForeignKey('transport_routes.id'), nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.now)
    route = relationship("TransportRoute", back_populates="vehicles")


class StudentTransport(Base):
    __tablename__ = 'student_transport'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    student_db_id   = Column(Integer, nullable=False)
    student_sys_id  = Column(String(50), default="")
    student_name    = Column(String(200), default="")
    route_id        = Column(Integer, ForeignKey('transport_routes.id'), nullable=False)
    pickup_stop     = Column(String(200), default="")
    joining_date    = Column(Date, nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.now)
    route = relationship("TransportRoute", back_populates="student_assignments")
