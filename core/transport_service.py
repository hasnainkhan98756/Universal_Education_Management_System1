from datetime import date, datetime
from database.connection import get_session
from database.models.transport import TransportRoute, TransportVehicle, StudentTransport


class TransportService:

    # ── Routes ────────────────────────────────────────────────────
    @staticmethod
    def add_route(data: dict):
        db = get_session()
        try:
            r = TransportRoute(
                route_name  = data.get("route_name", "").strip(),
                start_point = data.get("start_point", "").strip(),
                end_point   = data.get("end_point", "").strip(),
                stops       = data.get("stops", "").strip(),
                monthly_fee = float(data.get("monthly_fee", 0)),
            )
            db.add(r)
            db.commit()
            return True, f"Route '{r.route_name}' added."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_all_routes():
        db = get_session()
        try:
            return db.query(TransportRoute).filter_by(is_active=True).order_by(TransportRoute.id.desc()).all()
        finally:
            db.close()

    @staticmethod
    def update_route(route_id: int, data: dict):
        db = get_session()
        try:
            r = db.query(TransportRoute).filter_by(id=route_id).first()
            if not r: return False, "Route not found."
            r.route_name  = data.get("route_name", r.route_name).strip()
            r.start_point = data.get("start_point", r.start_point).strip()
            r.end_point   = data.get("end_point", r.end_point).strip()
            r.stops       = data.get("stops", r.stops).strip()
            r.monthly_fee = float(data.get("monthly_fee", r.monthly_fee))
            db.commit()
            return True, "Route updated."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def delete_route(route_id: int):
        db = get_session()
        try:
            r = db.query(TransportRoute).filter_by(id=route_id).first()
            if not r: return False, "Route not found."
            r.is_active = False
            db.commit()
            return True, "Route deactivated."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    # ── Vehicles ──────────────────────────────────────────────────
    @staticmethod
    def add_vehicle(data: dict):
        db = get_session()
        try:
            v = TransportVehicle(
                vehicle_number = data.get("vehicle_number", "").strip(),
                vehicle_type   = data.get("vehicle_type", "Bus").strip(),
                capacity       = int(data.get("capacity", 30)),
                driver_name    = data.get("driver_name", "").strip(),
                driver_phone   = data.get("driver_phone", "").strip(),
                driver_license = data.get("driver_license", "").strip(),
                route_id       = data.get("route_id") or None,
            )
            db.add(v)
            db.commit()
            return True, f"Vehicle '{v.vehicle_number}' added."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_all_vehicles():
        db = get_session()
        try:
            return db.query(TransportVehicle).filter_by(is_active=True).order_by(TransportVehicle.id.desc()).all()
        finally:
            db.close()

    @staticmethod
    def update_vehicle(vehicle_id: int, data: dict):
        db = get_session()
        try:
            v = db.query(TransportVehicle).filter_by(id=vehicle_id).first()
            if not v: return False, "Vehicle not found."
            v.vehicle_number = data.get("vehicle_number", v.vehicle_number).strip()
            v.vehicle_type   = data.get("vehicle_type", v.vehicle_type).strip()
            v.capacity       = int(data.get("capacity", v.capacity))
            v.driver_name    = data.get("driver_name", v.driver_name).strip()
            v.driver_phone   = data.get("driver_phone", v.driver_phone).strip()
            v.driver_license = data.get("driver_license", v.driver_license).strip()
            v.route_id       = data.get("route_id") or None
            db.commit()
            return True, "Vehicle updated."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def delete_vehicle(vehicle_id: int):
        db = get_session()
        try:
            v = db.query(TransportVehicle).filter_by(id=vehicle_id).first()
            if not v: return False, "Vehicle not found."
            v.is_active = False
            db.commit()
            return True, "Vehicle removed."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    # ── Student Assignments ────────────────────────────────────────
    @staticmethod
    def assign_student(student_db_id, student_sys_id, student_name, route_id, pickup_stop):
        db = get_session()
        try:
            existing = db.query(StudentTransport).filter_by(
                student_db_id=student_db_id, is_active=True
            ).first()
            if existing:
                return False, f"{student_name} is already assigned to a route. Remove first."
            st = StudentTransport(
                student_db_id  = student_db_id,
                student_sys_id = student_sys_id,
                student_name   = student_name,
                route_id       = route_id,
                pickup_stop    = pickup_stop,
                joining_date   = date.today(),
            )
            db.add(st)
            db.commit()
            return True, f"{student_name} assigned to route."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def remove_student_from_transport(assignment_id: int):
        db = get_session()
        try:
            st = db.query(StudentTransport).filter_by(id=assignment_id).first()
            if not st: return False, "Assignment not found."
            st.is_active = False
            db.commit()
            return True, "Student removed from transport."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_students_on_transport():
        from sqlalchemy.orm import joinedload
        db = get_session()
        try:
            return db.query(StudentTransport).options(joinedload(StudentTransport.route)).filter_by(is_active=True).order_by(StudentTransport.route_id).all()
        finally:
            db.close()

    @staticmethod
    def get_dashboard_stats():
        db = get_session()
        try:
            return {
                "total_routes":   db.query(TransportRoute).filter_by(is_active=True).count(),
                "total_vehicles": db.query(TransportVehicle).filter_by(is_active=True).count(),
                "total_students": db.query(StudentTransport).filter_by(is_active=True).count(),
            }
        finally:
            db.close()
