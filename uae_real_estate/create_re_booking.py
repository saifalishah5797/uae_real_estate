"""
Step 2: Payment Plan Template + Booking (with payment schedule) DocTypes.

Copy to: apps/uae_real_estate/uae_real_estate/create_re_booking.py   (same folder as hooks.py)
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.create_re_booking.run
    bench --site uae.localhost migrate && bench restart

Creates:
  RE Payment Plan Item      (child table)
  RE Payment Plan Template  (e.g. "10-20-30-40 Plan")
  RE Booking Payment        (child table: schedule rows inside a booking)
  RE Booking                (submittable; marks unit Booked on submit)
"""
import os
import frappe

APP = "uae_real_estate"
MODULE = "UAE Real Estate"  # must match modules.txt

PERMS_BOOKING = [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    {"role": "Sales Manager", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    {"role": "Sales User", "read": 1, "write": 1, "create": 1},
    {"role": "Accounts User", "read": 1},
]
PERMS_BASIC = [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "Sales Manager", "read": 1, "write": 1, "create": 1},
    {"role": "Sales User", "read": 1},
]


def f(fieldname, label, fieldtype="Data", **kw):
    d = {"fieldname": fieldname, "label": label, "fieldtype": fieldtype}
    d.update(kw)
    return d


DOCTYPES = [
    {
        "name": "RE Payment Plan Item",
        "istable": 1,
        "fields": [
            f("milestone", "Milestone", reqd=1, in_list_view=1),
            f("percentage", "Percentage", "Percent", reqd=1, in_list_view=1),
            f("due_after_days", "Due After (days from booking)", "Int", default="0", in_list_view=1),
        ],
    },
    {
        "name": "RE Payment Plan Template",
        "autoname": "field:plan_name",
        "title_field": "plan_name",
        "fields": [
            f("plan_name", "Plan Name", reqd=1, unique=1, in_list_view=1),
            f("description", "Description", "Small Text"),
            f("items", "Milestones", "Table", options="RE Payment Plan Item", reqd=1),
        ],
        "perms": PERMS_BASIC,
    },
    {
        "name": "RE Booking Payment",
        "istable": 1,
        "fields": [
            f("milestone", "Milestone", in_list_view=1),
            f("percentage", "Percentage", "Percent", in_list_view=1),
            f("due_date", "Due Date", "Date", in_list_view=1),
            f("amount", "Amount", "Currency", in_list_view=1),
            f("paid_amount", "Paid Amount", "Currency", in_list_view=1),
            f("payment_status", "Status", "Select", options="Pending\nPartly Paid\nPaid", default="Pending", in_list_view=1),
        ],
    },
    {
        "name": "RE Booking",
        "autoname": "BKG-.YYYY.-.#####",
        "is_submittable": 1,
        "title_field": "customer",
        "fields": [
            f("customer", "Customer", "Link", options="Customer", reqd=1, in_list_view=1),
            f("booking_date", "Booking Date", "Date", reqd=1, default="Today", in_list_view=1),
            f("unit", "Unit", "Link", options="RE Unit", reqd=1, in_list_view=1),
            f("project", "Project", "Link", options="RE Project", read_only=1, fetch_from="unit.project"),
            f("tower", "Tower", "Link", options="RE Tower", read_only=1, fetch_from="unit.tower"),
            f("pricing_section", "Pricing", "Section Break"),
            f("unit_price", "Unit Price", "Currency", read_only=1),
            f("discount", "Discount", "Currency"),
            f("net_price", "Net Price", "Currency", read_only=1),
            f("vat_percent", "VAT %", "Percent", default="5"),
            f("vat_amount", "VAT Amount", "Currency", read_only=1),
            f("grand_total", "Grand Total", "Currency", read_only=1, in_list_view=1),
            f("token_amount", "Token / Booking Amount", "Currency"),
            f("plan_section", "Payment Plan", "Section Break"),
            f("payment_plan", "Payment Plan Template", "Link", options="RE Payment Plan Template"),
            f("payment_schedule", "Payment Schedule", "Table", options="RE Booking Payment"),
            f("amended_from", "Amended From", "Link", options="RE Booking", read_only=1, no_copy=1),
        ],
        "perms": PERMS_BOOKING,
    },
]

BOOKING_CONTROLLER = '''import frappe
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
'''

SAMPLE_PLAN = {
    "plan_name": "10-20-30-40 Plan",
    "description": "10% on booking, 20% after 30 days, 30% after 90 days, 40% on handover (365 days)",
    "items": [
        {"milestone": "On Booking", "percentage": 10, "due_after_days": 0},
        {"milestone": "First Installment", "percentage": 20, "due_after_days": 30},
        {"milestone": "Second Installment", "percentage": 30, "due_after_days": 90},
        {"milestone": "On Handover", "percentage": 40, "due_after_days": 365},
    ],
}


def run():
    if not frappe.db.exists("Module Def", MODULE):
        frappe.throw(f"Module Def '{MODULE}' not found. Check MODULE in this script.")
    if not frappe.conf.developer_mode:
        frappe.throw("Enable developer_mode first: bench --site uae.localhost set-config developer_mode 1")
    if not frappe.db.exists("DocType", "RE Unit"):
        frappe.throw("RE Unit not found. Run create_re_doctypes.run first.")

    for spec in DOCTYPES:
        if frappe.db.exists("DocType", spec["name"]):
            print(f"skip (exists): {spec['name']}")
            continue
        d = {
            "doctype": "DocType",
            "name": spec["name"],
            "module": MODULE,
            "custom": 0,
            "fields": spec["fields"],
        }
        if spec.get("istable"):
            d["istable"] = 1
            d["editable_grid"] = 1
        else:
            d["permissions"] = spec.get("perms", PERMS_BASIC)
            d["track_changes"] = 1
            if spec.get("autoname"):
                d["autoname"] = spec["autoname"]
            if spec.get("title_field"):
                d["title_field"] = spec["title_field"]
            if spec.get("is_submittable"):
                d["is_submittable"] = 1
        frappe.get_doc(d).insert()
        print(f"created: {spec['name']}")

    # booking controller
    path = frappe.get_app_path(APP, frappe.scrub(MODULE), "doctype", "re_booking", "re_booking.py")
    if os.path.isdir(os.path.dirname(path)):
        with open(path, "w") as fh:
            fh.write(BOOKING_CONTROLLER)
        print(f"wrote controller: {path}")
    else:
        print("controller folder not found; paste logic into re_booking.py manually")

    # sample plan
    if not frappe.db.exists("RE Payment Plan Template", SAMPLE_PLAN["plan_name"]):
        frappe.get_doc({"doctype": "RE Payment Plan Template", **SAMPLE_PLAN}).insert()
        print("created sample plan: " + SAMPLE_PLAN["plan_name"])

    frappe.db.commit()
    frappe.clear_cache()
    print("Done. Run: bench --site uae.localhost migrate && bench restart")
