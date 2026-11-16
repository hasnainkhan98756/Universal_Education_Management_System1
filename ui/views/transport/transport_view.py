from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QFrame, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.transport_service import TransportService
from database.connection import get_session
from database.models.student import Student
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, TableActionButton, TableTextButton, create_table_actions_cell,
    SearchInput, style_modern_table, style_modern_tabs
)


def _btn(text, obj_name="btn_primary"):
    b = QPushButton(text)
    b.setObjectName(obj_name)
    return b


class RouteDialog(QDialog):
    def __init__(self, parent=None, route=None):
        super().__init__(parent)
        self.setWindowTitle("Add Route" if not route else "Edit Route")
        self.setMinimumWidth(400)
        lay = QVBoxLayout(self); form = QFormLayout(); form.setSpacing(12)

        self.inp_name  = QLineEdit(); self.inp_name.setPlaceholderText("e.g. Route A - North Campus")
        self.inp_start = QLineEdit(); self.inp_start.setPlaceholderText("Starting point")
        self.inp_end   = QLineEdit(); self.inp_end.setPlaceholderText("End point")
        self.inp_stops = QLineEdit(); self.inp_stops.setPlaceholderText("Stop1, Stop2, Stop3")
        self.sp_fee    = QDoubleSpinBox(); self.sp_fee.setRange(0, 99999); self.sp_fee.setPrefix("Rs. ")

        # Styles removed

        form.addRow("<b>Route Name:</b>",   self.inp_name)
        form.addRow("<b>From:</b>",          self.inp_start)
        form.addRow("<b>To:</b>",            self.inp_end)
        form.addRow("<b>Stops (comma):</b>", self.inp_stops)
        form.addRow("<b>Monthly Fee:</b>",   self.sp_fee)
        lay.addLayout(form)

        if route:
            self.inp_name.setText(route.route_name)
            self.inp_start.setText(route.start_point)
            self.inp_end.setText(route.end_point)
            self.inp_stops.setText(route.stops)
            self.sp_fee.setValue(route.monthly_fee)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "route_name":  self.inp_name.text(),
            "start_point": self.inp_start.text(),
            "end_point":   self.inp_end.text(),
            "stops":       self.inp_stops.text(),
            "monthly_fee": self.sp_fee.value(),
        }


class VehicleDialog(QDialog):
    def __init__(self, routes, parent=None, vehicle=None):
        super().__init__(parent)
        self.setWindowTitle("Add Vehicle" if not vehicle else "Edit Vehicle")
        self.setMinimumWidth(400)
        lay = QVBoxLayout(self); form = QFormLayout(); form.setSpacing(12)

        self.inp_number  = QLineEdit(); self.inp_number.setPlaceholderText("e.g. ABC-123")
        self.combo_type  = QComboBox(); self.combo_type.addItems(["Bus","Van","Mini-Bus","Coaster"])
        self.sp_capacity = QSpinBox(); self.sp_capacity.setRange(1, 100); self.sp_capacity.setValue(30)
        self.inp_driver  = QLineEdit()
        self.inp_phone   = QLineEdit()
        self.inp_license = QLineEdit()
        self.combo_route = QComboBox(); self.combo_route.addItem("-- No Route --", None)
        for r in routes:
            self.combo_route.addItem(r.route_name, r.id)

        # Styles removed

        form.addRow("<b>Vehicle No:</b>",    self.inp_number)
        form.addRow("<b>Type:</b>",           self.combo_type)
        form.addRow("<b>Capacity:</b>",       self.sp_capacity)
        form.addRow("<b>Driver Name:</b>",   self.inp_driver)
        form.addRow("<b>Driver Phone:</b>",  self.inp_phone)
        form.addRow("<b>License No:</b>",    self.inp_license)
        form.addRow("<b>Assigned Route:</b>",self.combo_route)
        lay.addLayout(form)

        if vehicle:
            self.inp_number.setText(vehicle.vehicle_number)
            self.combo_type.setCurrentText(vehicle.vehicle_type)
            self.sp_capacity.setValue(vehicle.capacity)
            self.inp_driver.setText(vehicle.driver_name)
            self.inp_phone.setText(vehicle.driver_phone)
            self.inp_license.setText(vehicle.driver_license)
            if vehicle.route_id:
                idx = self.combo_route.findData(vehicle.route_id)
                if idx >= 0: self.combo_route.setCurrentIndex(idx)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "vehicle_number": self.inp_number.text(),
            "vehicle_type":   self.combo_type.currentText(),
            "capacity":       self.sp_capacity.value(),
            "driver_name":    self.inp_driver.text(),
            "driver_phone":   self.inp_phone.text(),
            "driver_license": self.inp_license.text(),
            "route_id":       self.combo_route.currentData(),
        }


class AssignStudentDialog(QDialog):
    def __init__(self, routes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Student to Transport")
        self.setMinimumWidth(420)
        self.selected_student = None
        lay = QVBoxLayout(self); form = QFormLayout(); form.setSpacing(12)

        self.inp_search  = SearchInput(placeholder="Student ID or Name...")
        self.btn_search  = ModernButton("Search", icon_name="search", variant="secondary")
        self.btn_search.clicked.connect(self._search)
        self.lbl_student = QLabel("No student selected.")

        s_row = QHBoxLayout(); s_row.addWidget(self.inp_search); s_row.addWidget(self.btn_search)

        self.combo_route = QComboBox()
        for r in routes:
            self.combo_route.addItem(f"{r.route_name} (Rs.{r.monthly_fee:.0f}/mo)", r.id)

        self.inp_stop = QLineEdit(); self.inp_stop.setPlaceholderText("Pickup stop name")

        form.addRow("<b>Search Student:</b>", s_row)
        form.addRow("",                        self.lbl_student)
        form.addRow("<b>Route:</b>",           self.combo_route)
        form.addRow("<b>Pickup Stop:</b>",     self.inp_stop)
        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _search(self):
        q = self.inp_search.text().strip()
        if not q: return
        db = get_session()
        try:
            stu = db.query(Student).filter(
                (Student.student_id == q) | (Student.first_name.ilike(f"%{q}%"))
            ).filter_by(status="Active").first()
            if stu:
                self.selected_student = stu
                self.lbl_student.setText(f"Selected: {stu.first_name} {stu.last_name or ''} ({stu.student_id})")
                self.lbl_student.setStyleSheet("color:#16A34A;font-weight:bold;background:transparent;border:none;")
            else:
                self.selected_student = None
                self.lbl_student.setText("Student not found.")
                self.lbl_student.setStyleSheet("color:#DC2626;background:transparent;border:none;")
        finally:
            db.close()


class TransportView(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        header = PageHeader(
            title="Transport Management",
            subtitle="Manage school bus routes, vehicle fleets, and student route assignments",
            icon_name="bus",
        )
        main.addWidget(header)

        # Stats
        self.stats_bar = QHBoxLayout()
        self.stats_bar.setSpacing(14)
        self.card_routes   = MetricCard(title="Routes", value="0", icon_name="map-pin", accent_color="#1D4ED8")
        self.card_vehicles = MetricCard(title="Vehicles", value="0", icon_name="bus", accent_color="#8B5CF6")
        self.card_students = MetricCard(title="Students on Transport", value="0", icon_name="users-2", accent_color="#10B981")
        
        self.card_routes._val = self.card_routes.lbl_val
        self.card_vehicles._val = self.card_vehicles.lbl_val
        self.card_students._val = self.card_students.lbl_val

        self.stats_bar.addWidget(self.card_routes)
        self.stats_bar.addWidget(self.card_vehicles)
        self.stats_bar.addWidget(self.card_students)
        main.addLayout(self.stats_bar)

        tabs = QTabWidget()
        style_modern_tabs(tabs)
        tabs.addTab(self._routes_tab(),   "Routes")
        tabs.setTabIcon(0, get_icon("map-pin", color="#475569"))
        tabs.addTab(self._vehicles_tab(), "Vehicles")
        tabs.setTabIcon(1, get_icon("bus", color="#475569"))
        tabs.addTab(self._students_tab(), "Student Assignments")
        tabs.setTabIcon(2, get_icon("users-2", color="#475569"))
        main.addWidget(tabs)

        self.refresh_all()

    def _stat(self, label, value, color):
        f = MetricCard(title=label, value=value, icon_name="bus", accent_color=color)
        f._val = f.lbl_val
        return f

    def _routes_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        bar = QHBoxLayout()
        btn_add = ModernButton("Add Route", icon_name="plus", variant="primary")
        btn_add.clicked.connect(self.add_route)
        bar.addStretch(); bar.addWidget(btn_add); lay.addLayout(bar)
        self.tbl_routes = QTableWidget(); self.tbl_routes.setColumnCount(7)
        self.tbl_routes.setHorizontalHeaderLabels(["Route Name","From","To","Stops","Monthly Fee","Students","Actions"])
        self.tbl_routes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_routes.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_routes.setColumnWidth(6, 110)
        self.tbl_routes.verticalHeader().setVisible(False)
        self.tbl_routes.verticalHeader().setDefaultSectionSize(48)
        self.tbl_routes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        style_modern_table(self.tbl_routes)
        lay.addWidget(self.tbl_routes); return w

    def _vehicles_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        bar = QHBoxLayout()
        btn_add = ModernButton("Add Vehicle", icon_name="plus", variant="primary")
        btn_add.clicked.connect(self.add_vehicle)
        bar.addStretch(); bar.addWidget(btn_add); lay.addLayout(bar)
        self.tbl_vehicles = QTableWidget(); self.tbl_vehicles.setColumnCount(7)
        self.tbl_vehicles.setHorizontalHeaderLabels(["Vehicle No","Type","Capacity","Driver","Phone","Route","Actions"])
        self.tbl_vehicles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_vehicles.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_vehicles.setColumnWidth(6, 110)
        self.tbl_vehicles.verticalHeader().setVisible(False)
        self.tbl_vehicles.verticalHeader().setDefaultSectionSize(48)
        self.tbl_vehicles.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        style_modern_table(self.tbl_vehicles)
        lay.addWidget(self.tbl_vehicles); return w

    def _students_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        bar = QHBoxLayout()
        btn_assign = ModernButton("Assign Student", icon_name="plus", variant="primary")
        btn_assign.clicked.connect(self.assign_student)
        bar.addStretch(); bar.addWidget(btn_assign); lay.addLayout(bar)
        self.tbl_students = QTableWidget(); self.tbl_students.setColumnCount(6)
        self.tbl_students.setHorizontalHeaderLabels(["Student ID","Student Name","Route","Pickup Stop","Since","Actions"])
        self.tbl_students.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_students.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tbl_students.setColumnWidth(5, 110)
        self.tbl_students.verticalHeader().setVisible(False)
        self.tbl_students.verticalHeader().setDefaultSectionSize(48)
        self.tbl_students.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        style_modern_table(self.tbl_students)
        lay.addWidget(self.tbl_students); return w

    def refresh_all(self):
        self._refresh_routes(); self._refresh_vehicles(); self._refresh_students()
        s = TransportService.get_dashboard_stats()
        self.card_routes._val.setText(str(s["total_routes"]))
        self.card_vehicles._val.setText(str(s["total_vehicles"]))
        self.card_students._val.setText(str(s["total_students"]))

    def _refresh_routes(self):
        for child in self.tbl_routes.viewport().children():
            if isinstance(child, QWidget):
                child.hide()
                child.setParent(None)
                child.deleteLater()
        self.tbl_routes.clearContents()
        self.tbl_routes.setRowCount(0)

        routes = TransportService.get_all_routes()
        assignments = TransportService.get_students_on_transport()
        self.tbl_routes.setRowCount(len(routes))
        for r, route in enumerate(routes):
            stu_count = sum(1 for a in assignments if a.route_id == route.id)
            items = [route.route_name, route.start_point, route.end_point,
                     route.stops, f"Rs. {route.monthly_fee:.0f}", str(stu_count)]
            for c, v in enumerate(items):
                self.tbl_routes.setItem(r, c, QTableWidgetItem(v))

            be = TableActionButton("pencil", variant="edit", tooltip="Edit Route", size=30)
            bd = TableActionButton("trash-2", variant="delete", tooltip="Delete Route", size=30)
            be.clicked.connect(lambda _, rid=route.id: self.edit_route(rid))
            bd.clicked.connect(lambda _, rid=route.id: self.delete_route(rid))

            act_cell = create_table_actions_cell([be, bd])
            self.tbl_routes.setCellWidget(r, 6, act_cell)
            self.tbl_routes.setRowHeight(r, 48)

    def _refresh_vehicles(self):
        for child in self.tbl_vehicles.viewport().children():
            if isinstance(child, QWidget):
                child.hide()
                child.setParent(None)
                child.deleteLater()
        self.tbl_vehicles.clearContents()
        self.tbl_vehicles.setRowCount(0)

        vehicles = TransportService.get_all_vehicles()
        routes   = {r.id: r.route_name for r in TransportService.get_all_routes()}
        self.tbl_vehicles.setRowCount(len(vehicles))
        for r, v in enumerate(vehicles):
            items = [v.vehicle_number, v.vehicle_type, str(v.capacity),
                     v.driver_name, v.driver_phone,
                     routes.get(v.route_id, "-")]
            for c, val in enumerate(items):
                self.tbl_vehicles.setItem(r, c, QTableWidgetItem(val))

            be = TableActionButton("pencil", variant="edit", tooltip="Edit Vehicle", size=30)
            bd = TableActionButton("trash-2", variant="delete", tooltip="Delete Vehicle", size=30)
            be.clicked.connect(lambda _, vid=v.id: self.edit_vehicle(vid))
            bd.clicked.connect(lambda _, vid=v.id: self.delete_vehicle(vid))

            act_cell = create_table_actions_cell([be, bd])
            self.tbl_vehicles.setCellWidget(r, 6, act_cell)
            self.tbl_vehicles.setRowHeight(r, 48)

    def _refresh_students(self):
        for child in self.tbl_students.viewport().children():
            if isinstance(child, QWidget):
                child.hide()
                child.setParent(None)
                child.deleteLater()
        self.tbl_students.clearContents()
        self.tbl_students.setRowCount(0)

        assignments = TransportService.get_students_on_transport()
        self.tbl_students.setRowCount(len(assignments))
        for r, a in enumerate(assignments):
            route_name = a.route.route_name if a.route else "-"
            items = [a.student_sys_id, a.student_name, route_name,
                     a.pickup_stop, str(a.joining_date) if a.joining_date else ""]
            for c, v in enumerate(items):
                self.tbl_students.setItem(r, c, QTableWidgetItem(v))

            brm = TableTextButton("Remove", icon_name="trash-2", variant="danger")
            brm.clicked.connect(lambda _, aid=a.id: self.remove_student(aid))
            act_cell = create_table_actions_cell([brm])
            self.tbl_students.setCellWidget(r, 5, act_cell)
            self.tbl_students.setRowHeight(r, 48)

    def add_route(self):
        dlg = RouteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = TransportService.add_route(dlg.get_data())
            if ok: QMessageBox.information(self,"Success",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def edit_route(self, route_id):
        routes = TransportService.get_all_routes()
        route  = next((r for r in routes if r.id == route_id), None)
        if not route: return
        dlg = RouteDialog(self, route=route)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = TransportService.update_route(route_id, dlg.get_data())
            if ok: QMessageBox.information(self,"Updated",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def delete_route(self, route_id):
        if QMessageBox.question(self,"Confirm","Delete this route?") == QMessageBox.StandardButton.Yes:
            ok, msg = TransportService.delete_route(route_id)
            if ok: QMessageBox.information(self,"Done",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def add_vehicle(self):
        routes = TransportService.get_all_routes()
        dlg = VehicleDialog(routes, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = TransportService.add_vehicle(dlg.get_data())
            if ok: QMessageBox.information(self,"Success",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def edit_vehicle(self, vehicle_id):
        vehicles = TransportService.get_all_vehicles()
        vehicle  = next((v for v in vehicles if v.id == vehicle_id), None)
        if not vehicle: return
        routes = TransportService.get_all_routes()
        dlg = VehicleDialog(routes, self, vehicle=vehicle)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = TransportService.update_vehicle(vehicle_id, dlg.get_data())
            if ok: QMessageBox.information(self,"Updated",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def delete_vehicle(self, vehicle_id):
        if QMessageBox.question(self,"Confirm","Delete this vehicle?") == QMessageBox.StandardButton.Yes:
            ok, msg = TransportService.delete_vehicle(vehicle_id)
            if ok: QMessageBox.information(self,"Done",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def assign_student(self):
        routes = TransportService.get_all_routes()
        if not routes:
            QMessageBox.warning(self, "No Routes", "Add a route first.")
            return
        dlg = AssignStudentDialog(routes, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not dlg.selected_student:
                QMessageBox.warning(self, "Error", "Search and select a student first.")
                return
            stu  = dlg.selected_student
            rid  = dlg.combo_route.currentData()
            stop = dlg.inp_stop.text().strip()
            ok, msg = TransportService.assign_student(
                stu.id, stu.student_id,
                f"{stu.first_name} {stu.last_name or ''}".strip(), rid, stop
            )
            if ok: QMessageBox.information(self,"Assigned",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)

    def remove_student(self, assignment_id):
        if QMessageBox.question(self,"Confirm","Remove student from transport?") == QMessageBox.StandardButton.Yes:
            ok, msg = TransportService.remove_student_from_transport(assignment_id)
            if ok: QMessageBox.information(self,"Done",msg); self.refresh_all()
            else:  QMessageBox.critical(self,"Error",msg)
