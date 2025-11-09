# payroll_app.py
import sys
import sqlite3
import os
import csv
from datetime import datetime
from fpdf import FPDF

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QMessageBox, QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt

DB_FILE = "payroll.db"
PAYSLIP_DIR = "payslips"

# ---------- Database helpers ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT,
            job_title TEXT,
            base_salary REAL NOT NULL,
            allowance REAL DEFAULT 0,
            deduction REAL DEFAULT 0,
            overtime_rate REAL DEFAULT 0,
            bank_account TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pay_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER,
            pay_date TEXT,
            gross REAL,
            net REAL,
            note TEXT,
            FOREIGN KEY(emp_id) REFERENCES employees(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_employee(emp):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO employees (name, department, job_title, base_salary, allowance, deduction, overtime_rate, bank_account)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (emp['name'], emp.get('department',''), emp.get('job_title',''),
          emp['base_salary'], emp.get('allowance',0), emp.get('deduction',0),
          emp.get('overtime_rate',0), emp.get('bank_account','')))
    conn.commit()
    conn.close()

def update_employee(emp_id, emp):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        UPDATE employees SET name=?, department=?, job_title=?, base_salary=?, allowance=?, deduction=?, overtime_rate=?, bank_account=?
        WHERE id=?
    ''', (emp['name'], emp.get('department',''), emp.get('job_title',''),
          emp['base_salary'], emp.get('allowance',0), emp.get('deduction',0),
          emp.get('overtime_rate',0), emp.get('bank_account',''), emp_id))
    conn.commit()
    conn.close()

def delete_employee(emp_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('DELETE FROM employees WHERE id=?', (emp_id,))
    conn.commit()
    conn.close()

def get_all_employees():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT id, name, department, job_title, base_salary, allowance, deduction, overtime_rate, bank_account FROM employees')
    rows = cur.fetchall()
    conn.close()
    return rows

def add_pay_record(emp_id, pay_date, gross, net, note=''):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO pay_records (emp_id, pay_date, gross, net, note)
        VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, pay_date, gross, net, note))
    conn.commit()
    conn.close()

# ---------- Salary calculation ----------
def calculate_salary_for_employee(base_salary, allowance, deduction, overtime_hours, overtime_rate):
    gross = base_salary + allowance + (overtime_hours * overtime_rate)
    tax = 0  # placeholder: you can add tax rules here
    net = gross - deduction - tax
    return gross, net

# ---------- Payslip PDF ----------
def generate_payslip_pdf(emp_row, pay_date, gross, net, overtime_hours, save_dir=PAYSLIP_DIR):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    emp_id, name, dept, job, base_salary, allowance, deduction, overtime_rate, bank = emp_row
    filename = f"{save_dir}/payslip_{emp_id}_{pay_date.replace(' ', '_').replace(':','-')}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, "Company XYZ - Payslip", ln=1, align='C')
    pdf.ln(4)
    pdf.cell(0, 6, f"Employee: {name} (ID: {emp_id})", ln=1)
    pdf.cell(0, 6, f"Department: {dept}    Job Title: {job}", ln=1)
    pdf.cell(0, 6, f"Bank: {bank}", ln=1)
    pdf.ln(4)
    pdf.cell(0, 6, f"Pay Date: {pay_date}", ln=1)
    pdf.ln(4)
    pdf.cell(0, 6, f"Base Salary: {base_salary:.2f}", ln=1)
    pdf.cell(0, 6, f"Allowance: {allowance:.2f}", ln=1)
    pdf.cell(0, 6, f"Overtime Hours: {overtime_hours}  Rate: {overtime_rate:.2f}", ln=1)
    pdf.cell(0, 6, f"Gross Pay: {gross:.2f}", ln=1)
    pdf.cell(0, 6, f"Deductions: {deduction:.2f}", ln=1)
    pdf.cell(0, 6, f"Net Pay: {net:.2f}", ln=1)
    pdf.ln(8)
    pdf.cell(0, 6, "Thank you for your service.", ln=1)
    pdf.output(filename)
    return filename

# ---------- GUI ----------
class PayrollApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Payroll Management - Demo (PyQt6)")
        self.resize(900, 550)
        init_db()
        self.selected_emp_id = None
        self.build_ui()
        self.load_employees()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left: table
        left = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID","Name","Department","Job","Base Salary"])
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self.on_table_click)
        left.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Employee")
        add_btn.clicked.connect(self.on_add)
        edit_btn = QPushButton("Edit Employee")
        edit_btn.clicked.connect(self.on_edit)
        del_btn = QPushButton("Delete Employee")
        del_btn.clicked.connect(self.on_delete)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.on_export_csv)
        btn_row.addWidget(add_btn); btn_row.addWidget(edit_btn); btn_row.addWidget(del_btn); btn_row.addWidget(export_btn)
        left.addLayout(btn_row)

        main_layout.addLayout(left, 60)

        # Right: form & salary actions
        right = QVBoxLayout()
        right.addWidget(QLabel("Employee Details"))

        self.input_name = QLineEdit()
        self.input_dept = QLineEdit()
        self.input_job = QLineEdit()
        self.input_base = QLineEdit()
        self.input_allow = QLineEdit()
        self.input_ded = QLineEdit()
        self.input_ot_rate = QLineEdit()
        self.input_bank = QLineEdit()
        self.input_ot_hours = QSpinBox()
        self.input_ot_hours.setRange(0, 500)

        form_items = [
            ("Name", self.input_name),
            ("Department", self.input_dept),
            ("Job Title", self.input_job),
            ("Base Salary", self.input_base),
            ("Allowance", self.input_allow),
            ("Deduction", self.input_ded),
            ("Overtime Rate (per hour)", self.input_ot_rate),
            ("Overtime Hours", self.input_ot_hours),
            ("Bank Account", self.input_bank),
        ]
        for label_text, widget in form_items:
            l = QLabel(label_text)
            right.addWidget(l)
            right.addWidget(widget)

        calc_btn = QPushButton("Calculate Salary & Generate Payslip")
        calc_btn.clicked.connect(self.on_calculate_and_payslip)
        right.addWidget(calc_btn)

        summary_btn = QPushButton("Quick Payroll Summary (CSV)")
        summary_btn.clicked.connect(self.on_export_csv)
        right.addWidget(summary_btn)

        # status / simple help
        right.addStretch()
        help_label = QLabel("Tip: select an employee on the left, edit fields and click Edit to update.\nPayslips saved in ./payslips/")
        help_label.setWordWrap(True)
        right.addWidget(help_label)

        main_layout.addLayout(right, 40)

    def load_employees(self):
        rows = get_all_employees()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            emp_id, name, dept, job, base_salary, allowance, deduction, overtime_rate, bank = row
            self.table.setItem(r, 0, QTableWidgetItem(str(emp_id)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(dept))
            self.table.setItem(r, 3, QTableWidgetItem(job))
            self.table.setItem(r, 4, QTableWidgetItem(f"{base_salary:.2f}"))

    def on_table_click(self, row, col):
        # load selected employee into the form
        self.selected_emp_id = int(self.table.item(row,0).text())
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('SELECT id, name, department, job_title, base_salary, allowance, deduction, overtime_rate, bank_account FROM employees WHERE id=?', (self.selected_emp_id,))
        r = cur.fetchone()
        conn.close()
        if r:
            _, name, dept, job, base, allow, ded, otr, bank = r
            self.input_name.setText(name)
            self.input_dept.setText(dept)
            self.input_job.setText(job)
            self.input_base.setText(str(base))
            self.input_allow.setText(str(allow))
            self.input_ded.setText(str(ded))
            self.input_ot_rate.setText(str(otr))
            self.input_bank.setText(bank)

    def read_form(self):
        try:
            base = float(self.input_base.text() or "0")
            allow = float(self.input_allow.text() or "0")
            ded = float(self.input_ded.text() or "0")
            otr = float(self.input_ot_rate.text() or "0")
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Numeric fields must contain numbers.")
            return None
        return {
            'name': self.input_name.text().strip(),
            'department': self.input_dept.text().strip(),
            'job_title': self.input_job.text().strip(),
            'base_salary': base,
            'allowance': allow,
            'deduction': ded,
            'overtime_rate': otr,
            'bank_account': self.input_bank.text().strip()
        }

    def on_add(self):
        emp = self.read_form()
        if not emp: return
        if not emp['name']:
            QMessageBox.warning(self, "Missing", "Please enter a name.")
            return
        add_employee(emp)
        self.load_employees()
        QMessageBox.information(self, "Added", "Employee added successfully.")

    def on_edit(self):
        if not self.selected_emp_id:
            QMessageBox.warning(self, "Select", "Please select an employee first.")
            return
        emp = self.read_form()
        if not emp: return
        update_employee(self.selected_emp_id, emp)
        self.load_employees()
        QMessageBox.information(self, "Updated", "Employee updated successfully.")

    def on_delete(self):
        if not self.selected_emp_id:
            QMessageBox.warning(self, "Select", "Please select an employee first.")
            return
        reply = QMessageBox.question(self, "Confirm", "Delete selected employee?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_employee(self.selected_emp_id)
            self.selected_emp_id = None
            self.load_employees()

    def on_calculate_and_payslip(self):
        if not self.selected_emp_id:
            QMessageBox.warning(self, "Select", "Select an employee from the left first.")
            return
        emp_rows = [r for r in get_all_employees() if r[0] == self.selected_emp_id]
        if not emp_rows:
            QMessageBox.warning(self, "Error", "Employee not found.")
            return
        emp = emp_rows[0]
        try:
            overtime_hours = int(self.input_ot_hours.value())
        except:
            overtime_hours = 0
        base = emp[4]; allow = emp[5]; ded = emp[6]; otrate = emp[7]
        gross, net = calculate_salary_for_employee(base, allow, ded, overtime_hours, otrate)
        pay_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        add_pay_record(self.selected_emp_id, pay_date, gross, net, note=f"Overtime: {overtime_hours}")
        pdf_file = generate_payslip_pdf(emp, pay_date, gross, net, overtime_hours)
        QMessageBox.information(self, "Payslip", f"Payslip generated: {pdf_file}")

    def on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "payroll_summary.csv", "CSV Files (*.csv)")
        if not path:
            return
        rows = get_all_employees()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID","Name","Department","Job","Base Salary","Allowance","Deduction","Overtime Rate","Bank"])
            for r in rows:
                writer.writerow(r)
        QMessageBox.information(self, "Exported", f"CSV saved to {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PayrollApp()
    window.show()
    sys.exit(app.exec())
