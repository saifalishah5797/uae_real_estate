import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt


class REBooking(Document):
    def validate(self):
        self.check_unit_available()
        self.calculate_totals()
        if self.payment_plan and not self.payment_schedule:
            self.generate_schedule()
        self.validate_schedule()

    def check_unit_available(self):
        if self.docstatus != 0:
            return
        status = frappe.db.get_value("RE Unit", self.unit, "status")
        if status not in ("Available", "Hold"):
            frappe.throw(_("Unit {0} is {1} and cannot be booked.").format(self.unit, status))

    def calculate_totals(self):
        self.unit_price = frappe.db.get_value("RE Unit", self.unit, "total_price") or 0
        self.net_price = flt(self.unit_price) - flt(self.discount)
        if self.net_price < 0:
            frappe.throw(_("Discount cannot exceed the unit price."))
        self.vat_amount = self.net_price * flt(self.vat_percent) / 100
        self.grand_total = self.net_price + self.vat_amount
        self.total_paid = sum(flt(r.paid_amount) for r in self.payment_schedule)
        self.outstanding = flt(self.grand_total) - flt(self.total_paid)

    def generate_schedule(self):
        plan = frappe.get_doc("RE Payment Plan Template", self.payment_plan)
        self.set("payment_schedule", [])
        for item in plan.items:
            self.append("payment_schedule", {
                "milestone": item.milestone,
                "percentage": item.percentage,
                "due_date": add_days(self.booking_date, item.due_after_days or 0),
                "amount": flt(self.grand_total) * flt(item.percentage) / 100,
                "payment_status": "Pending",
            })

    def validate_schedule(self):
        if not self.payment_schedule:
            return
        total = sum(flt(r.percentage) for r in self.payment_schedule)
        if abs(total - 100) > 0.01:
            frappe.throw(_("Payment schedule must total 100% (currently {0}%).").format(total))

    def on_submit(self):
        # re-check to avoid double booking
        status = frappe.db.get_value("RE Unit", self.unit, "status")
        if status not in ("Available", "Hold"):
            frappe.throw(_("Unit {0} is already {1}.").format(self.unit, status))
        frappe.db.set_value("RE Unit", self.unit, "status", "Booked")

    def on_cancel(self):
        frappe.db.set_value("RE Unit", self.unit, "status", "Available")
