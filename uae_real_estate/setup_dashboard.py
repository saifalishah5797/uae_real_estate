"""
Real Estate dashboard setup.

Copy to: apps/uae_real_estate/uae_real_estate/setup_dashboard.py   (same folder as hooks.py)
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.setup_dashboard.run

What it does:
  1. Adds "Total Paid" and "Outstanding" fields to RE Booking
  2. Patches the RE Booking controller so new bookings calculate them
  3. Back-fills the two fields for existing submitted bookings
  4. Creates 7 Number Cards and 5 Dashboard Charts
  5. Creates a Dashboard and a Workspace page ("Real Estate Dashboard")
"""
import json
import os

import frappe
from frappe.utils import flt

APP = "uae_real_estate"
MODULE = "UAE Real Estate"


# ---------------------------------------------------------------- step 1-3
def add_booking_fields():
    dt = frappe.get_doc("DocType", "RE Booking")

    # Frappe auto-adds "amended_from" on submittable DocTypes, and we defined it too,
    # so the DocType can contain it twice. Keep only the first copy of every fieldname.
    seen, unique = set(), []
    for fld in dt.fields:
        if fld.fieldname in seen:
            print(f"removing duplicate field: {fld.fieldname}")
            continue
        seen.add(fld.fieldname)
        unique.append(fld)
    if len(unique) != len(dt.fields):
        dt.set("fields", unique)

    if "total_paid" in seen:
        if len(unique) != len(dt.fields):
            dt.save()
        print("fields already on RE Booking")
        return
    dt.append("fields", {"fieldname": "collection_section", "label": "Collections", "fieldtype": "Section Break"})
    dt.append("fields", {"fieldname": "total_paid", "label": "Total Paid", "fieldtype": "Currency", "read_only": 1})
    dt.append("fields", {"fieldname": "outstanding", "label": "Outstanding", "fieldtype": "Currency", "read_only": 1, "in_list_view": 1})
    dt.save()
    print("added total_paid, outstanding to RE Booking")


def patch_controller():
    path = frappe.get_app_path(APP, frappe.scrub(MODULE), "doctype", "re_booking", "re_booking.py")
    with open(path) as fh:
        code = fh.read()
    if "self.outstanding" in code:
        print("controller already patched")
        return
    anchor = "        self.grand_total = self.net_price + self.vat_amount\n"
    if anchor not in code:
        print("WARNING: could not patch controller automatically. Add these two lines at the end of "
              "calculate_totals():\n"
              "        self.total_paid = sum(flt(r.paid_amount) for r in self.payment_schedule)\n"
              "        self.outstanding = flt(self.grand_total) - flt(self.total_paid)")
        return
    new = anchor + (
        "        self.total_paid = sum(flt(r.paid_amount) for r in self.payment_schedule)\n"
        "        self.outstanding = flt(self.grand_total) - flt(self.total_paid)\n"
    )
    with open(path, "w") as fh:
        fh.write(code.replace(anchor, new))
    print("controller patched")


def backfill():
    names = frappe.get_all("RE Booking", filters={"docstatus": 1}, pluck="name")
    for n in names:
        paid = frappe.db.sql(
            "select coalesce(sum(paid_amount),0) from `tabRE Booking Payment` where parent=%s", n)[0][0]
        grand = frappe.db.get_value("RE Booking", n, "grand_total") or 0
        frappe.db.set_value("RE Booking", n,
                            {"total_paid": paid, "outstanding": flt(grand) - flt(paid)},
                            update_modified=False)
    print(f"back-filled {len(names)} bookings")


# ---------------------------------------------------------------- step 4
def flt_json(dt, *conds):
    return json.dumps([[dt, f, op, v, False] for f, op, v in conds])


BOOKING_SUBMITTED = flt_json("RE Booking", ("docstatus", "=", 1))

NUMBER_CARDS = [
    {"label": "Total Units", "document_type": "RE Unit", "function": "Count", "filters": "[]"},
    {"label": "Available Units", "document_type": "RE Unit", "function": "Count",
     "filters": flt_json("RE Unit", ("status", "=", "Available"))},
    {"label": "Booked Units", "document_type": "RE Unit", "function": "Count",
     "filters": flt_json("RE Unit", ("status", "=", "Booked"))},
    {"label": "Active Bookings", "document_type": "RE Booking", "function": "Count",
     "filters": BOOKING_SUBMITTED},
    {"label": "Sales Value", "document_type": "RE Booking", "function": "Sum",
     "field": "grand_total", "filters": BOOKING_SUBMITTED},
    {"label": "Total Collected", "document_type": "RE Booking", "function": "Sum",
     "field": "total_paid", "filters": BOOKING_SUBMITTED},
    {"label": "Total Outstanding", "document_type": "RE Booking", "function": "Sum",
     "field": "outstanding", "filters": BOOKING_SUBMITTED},
]

CHARTS = [
    {"chart_name": "Units by Status", "chart_type": "Group By", "document_type": "RE Unit",
     "group_by_based_on": "status", "group_by_type": "Count", "type": "Donut", "filters_json": "[]"},
    {"chart_name": "Sales by Project", "chart_type": "Group By", "document_type": "RE Booking",
     "group_by_based_on": "project", "group_by_type": "Sum", "aggregate_function_based_on": "grand_total",
     "type": "Bar", "filters_json": BOOKING_SUBMITTED},
    {"chart_name": "Outstanding by Project", "chart_type": "Group By", "document_type": "RE Booking",
     "group_by_based_on": "project", "group_by_type": "Sum", "aggregate_function_based_on": "outstanding",
     "type": "Bar", "filters_json": BOOKING_SUBMITTED},
    {"chart_name": "Bookings by Payment Plan", "chart_type": "Group By", "document_type": "RE Booking",
     "group_by_based_on": "payment_plan", "group_by_type": "Count", "type": "Pie",
     "filters_json": BOOKING_SUBMITTED},
    {"chart_name": "Monthly Bookings", "chart_type": "Count", "document_type": "RE Booking",
     "based_on": "booking_date", "timespan": "Last Year", "time_interval": "Monthly",
     "type": "Line", "filters_json": BOOKING_SUBMITTED},
]


def create_cards():
    for c in NUMBER_CARDS:
        if frappe.db.exists("Number Card", c["label"]):
            print(f"card exists: {c['label']}")
            continue
        doc = {
            "doctype": "Number Card",
            "label": c["label"],
            "type": "Document Type",
            "document_type": c["document_type"],
            "function": c["function"],
            "filters_json": c["filters"],
            "is_public": 1,
            "show_percentage_stats": 1,
            "stats_time_interval": "Monthly",
            "module": MODULE,
        }
        if c.get("field"):
            doc["aggregate_function_based_on"] = c["field"]
        frappe.get_doc(doc).insert()
        print(f"card: {c['label']}")


def create_charts():
    for c in CHARTS:
        if frappe.db.exists("Dashboard Chart", c["chart_name"]):
            print(f"chart exists: {c['chart_name']}")
            continue
        frappe.get_doc({"doctype": "Dashboard Chart", "is_public": 1, "module": MODULE,
                        "is_custom": 0, "number_of_groups": 0, **c}).insert()
        print(f"chart: {c['chart_name']}")


# ---------------------------------------------------------------- step 5
def create_dashboard():
    name = "Real Estate Dashboard"
    if frappe.db.exists("Dashboard", name):
        print("dashboard exists")
        return
    frappe.get_doc({
        "doctype": "Dashboard",
        "dashboard_name": name,
        "module": MODULE,
        "cards": [{"card": c["label"]} for c in NUMBER_CARDS],
        "charts": [{"chart": c["chart_name"], "width": "Half"} for c in CHARTS],
    }).insert()
    print("dashboard created")


def create_workspace():
    name = "Real Estate Dashboard"
    if frappe.db.exists("Workspace", name):
        print("workspace exists")
        return

    def bid():
        return frappe.generate_hash(length=10)

    shortcuts = [("Units", "RE Unit"), ("Bookings", "RE Booking"),
                 ("Projects", "RE Project"), ("Payment Plans", "RE Payment Plan Template")]

    content = [{"id": bid(), "type": "header",
                "data": {"text": "<span class=\"h4\"><b>Real Estate Overview</b></span>", "col": 12}}]
    for c in NUMBER_CARDS:
        content.append({"id": bid(), "type": "number_card",
                        "data": {"number_card_name": c["label"], "col": 3}})
    for c in CHARTS:
        content.append({"id": bid(), "type": "chart",
                        "data": {"chart_name": c["chart_name"], "col": 6}})
    content.append({"id": bid(), "type": "header",
                    "data": {"text": "<span class=\"h4\"><b>Quick Access</b></span>", "col": 12}})
    for label, _ in shortcuts:
        content.append({"id": bid(), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})

    frappe.get_doc({
        "doctype": "Workspace",
        "name": name,
        "title": name,
        "label": name,
        "module": MODULE,
        "public": 1,
        "icon": "building",
        "content": json.dumps(content),
        "number_cards": [{"number_card_name": c["label"], "label": c["label"]} for c in NUMBER_CARDS],
        "charts": [{"chart_name": c["chart_name"], "label": c["chart_name"]} for c in CHARTS],
        "shortcuts": [{"label": l, "type": "DocType", "link_to": d, "doc_view": "List"} for l, d in shortcuts],
    }).insert()
    print("workspace created")


# ---------------------------------------------------------------- main
def run():
    if not frappe.db.exists("DocType", "RE Booking"):
        frappe.throw("RE Booking not found. Run the earlier setup scripts first.")
    if not frappe.conf.developer_mode:
        frappe.throw("Enable developer_mode first: bench --site uae.localhost set-config developer_mode 1")

    add_booking_fields()
    patch_controller()
    frappe.db.commit()
    backfill()
    create_cards()
    create_charts()
    create_dashboard()
    try:
        create_workspace()
    except Exception as e:
        print(f"workspace skipped ({e}). The Dashboard still works at /app/dashboard-view/Real Estate Dashboard")

    frappe.db.commit()
    frappe.clear_cache()
    print("\nDone. Run: bench --site uae.localhost migrate && bench restart")
    print("Open: /app/real-estate-dashboard   or   /app/dashboard-view/Real%20Estate%20Dashboard")
