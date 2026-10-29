"""
Demo data generator for the dashboard.

Copy to: apps/uae_real_estate/uae_real_estate/seed_data.py   (same folder as hooks.py)
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.seed_data.run

Remove all demo data again:
    bench --site uae.localhost execute uae_real_estate.seed_data.clear

Creates: 2 projects, 3 towers, 24 units, 12 customers, 3 payment plans,
12 submitted bookings, ~15 payment entries, plus some Hold / Sold units.
Safe to run again (skips what already exists).
"""
import frappe
from frappe.utils import add_days, flt, nowdate

from uae_real_estate.payments import make_payment_entry

DEMO_PROJECTS = ["Palm Heights", "Marina Residency"]

TOWERS = [
    ("Palm Heights", "A", 12),
    ("Palm Heights", "B", 12),
    ("Marina Residency", "A", 20),
]

# unit_type, saleable area, base rate per sq ft
UNIT_TEMPLATES = [
    ("Studio", 450, 900),
    ("1BR", 750, 950),
    ("1BR", 800, 1000),
    ("2BR", 1100, 1050),
    ("2BR", 1250, 1100),
    ("3BR", 1650, 1150),
    ("3BR", 1800, 1200),
    ("Penthouse", 2800, 1500),
]

CUSTOMERS = [
    "Ahmed Al Mansoori", "Fatima Khan", "Rahul Sharma", "Sara Johnson",
    "Mohammed Rashid", "Priya Nair", "Omar Haddad", "Elena Petrova",
    "Yusuf Ali", "Aisha Siddiqui", "David Miller", "Noor Hassan",
]

PLANS = {
    "10-20-30-40 Plan": None,  # already created by create_re_booking
    "20-80 Plan": [
        ("On Booking", 20, 0),
        ("On Handover", 80, 365),
    ],
    "40-30-30 Plan": [
        ("On Booking", 40, 0),
        ("Mid Construction", 30, 180),
        ("On Handover", 30, 540),
    ],
}

# which plan / discount / payment pattern each booking gets
PLAN_CYCLE = ["10-20-30-40 Plan", "20-80 Plan", "40-30-30 Plan"]
DISCOUNTS = [0, 5000, 0, 10000, 0, 0, 7500, 0, 15000, 0, 5000, 0]
# payment pattern: "m1" first milestone paid, "m1m2" first two paid, "part" half of first, "none"
PAYMENT_PATTERN = ["m1m2", "m1", "part", "m1", "none", "m1m2", "m1", "part", "m1", "m1m2", "none", "m1"]


def get_or_create(doctype, name, values):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.get_doc({"doctype": doctype, **values}).insert()


def pay(booking_name, row_idx, amount=None):
    pe_name = make_payment_entry(booking_name, row_idx, amount)
    frappe.get_doc("Payment Entry", pe_name).submit()


def run():
    # ---------- plans ----------
    for plan_name, items in PLANS.items():
        if items is None or frappe.db.exists("RE Payment Plan Template", plan_name):
            continue
        frappe.get_doc({
            "doctype": "RE Payment Plan Template",
            "plan_name": plan_name,
            "items": [{"milestone": m, "percentage": p, "due_after_days": d} for m, p, d in items],
        }).insert()
        print(f"plan: {plan_name}")

    # ---------- projects, towers ----------
    cities = {"Palm Heights": "Dubai", "Marina Residency": "Abu Dhabi"}
    for p in DEMO_PROJECTS:
        get_or_create("RE Project", p, {"project_name": p, "city": cities[p], "status": "Under Construction"})

    towers = []
    for project, tname, floors in TOWERS:
        t = get_or_create("RE Tower", f"{project}-{tname}", {
            "project": project, "tower_name": tname, "total_floors": floors,
            "status": "Under Construction",
        })
        towers.append(t)

    # ---------- units (8 per tower) ----------
    units = []
    for t in towers:
        for i, (utype, area, rate) in enumerate(UNIT_TEMPLATES):
            floor = (i // 2) + 1
            unit_no = f"{floor}0{(i % 2) + 1}"
            name = f"{t.name}-{unit_no}"
            if frappe.db.exists("RE Unit", name):
                units.append(frappe.get_doc("RE Unit", name))
                continue
            u = frappe.get_doc({
                "doctype": "RE Unit",
                "unit_no": unit_no,
                "project": t.project,
                "tower": t.name,
                "floor": floor,
                "unit_type": utype,
                "facing": ["Sea View", "City View", "Garden View", "North"][i % 4],
                "super_builtup_area": area,
                "base_rate": rate,
                "floor_rise": floor * 2000,
                "plc": 15000 if i % 3 == 0 else 0,
                "parking_charges": 25000 if utype not in ("Studio",) else 0,
            }).insert()
            units.append(u)
    print(f"units: {len(units)}")

    # ---------- customers ----------
    cg = frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_value(
        "Customer Group", {"is_group": 0})
    terr = frappe.db.get_single_value("Selling Settings", "territory") or frappe.db.get_value(
        "Territory", {"is_group": 0})
    customers = []
    for c in CUSTOMERS:
        customers.append(get_or_create("Customer", c, {
            "customer_name": c, "customer_type": "Individual",
            "customer_group": cg, "territory": terr,
        }))
    print(f"customers: {len(customers)}")

    # ---------- bookings + payments ----------
    # spread bookings across Palm Heights A/B and Marina so every project has sales
    available = [u for u in units if frappe.db.get_value("RE Unit", u.name, "status") == "Available"]
    picks = available[0:4] + available[8:12] + available[16:20]
    made = 0
    for i, unit in enumerate(picks[:12]):
        if frappe.db.exists("RE Booking", {"unit": unit.name, "docstatus": 1}):
            continue
        bk = frappe.get_doc({
            "doctype": "RE Booking",
            "customer": customers[i].name,
            "unit": unit.name,
            "booking_date": add_days(nowdate(), -(i * 14 + 3)),  # spread over ~5 months
            "discount": DISCOUNTS[i],
            "payment_plan": PLAN_CYCLE[i % 3],
            "token_amount": 5000,
        }).insert()
        bk.submit()
        made += 1

        pattern = PAYMENT_PATTERN[i]
        if pattern in ("m1", "m1m2"):
            pay(bk.name, 1)
        if pattern == "m1m2":
            pay(bk.name, 2)
        if pattern == "part":
            half = flt(bk.payment_schedule[0].amount) / 2
            pay(bk.name, 1, half)
    print(f"bookings created: {made}")

    # ---------- a few Hold / Sold units for variety ----------
    still_free = [u for u in units if frappe.db.get_value("RE Unit", u.name, "status") == "Available"]
    for u in still_free[0:3]:
        frappe.db.set_value("RE Unit", u.name, "status", "Hold")
    for u in still_free[3:5]:
        frappe.db.set_value("RE Unit", u.name, "status", "Sold")

    frappe.db.commit()
    print_summary()


def print_summary():
    total_units = frappe.db.count("RE Unit")
    print("\n==== Summary ====")
    for s in ("Available", "Hold", "Booked", "Sold"):
        print(f"  {s:10} {frappe.db.count('RE Unit', {'status': s})}")
    print(f"  Units total      {total_units}")
    print(f"  Bookings (submit) {frappe.db.count('RE Booking', {'docstatus': 1})}")
    value = frappe.db.sql("select coalesce(sum(grand_total),0) from `tabRE Booking` where docstatus=1")[0][0]
    paid = frappe.db.sql(
        "select coalesce(sum(paid_amount),0) from `tabRE Booking Payment` where parent in "
        "(select name from `tabRE Booking` where docstatus=1)")[0][0]
    print(f"  Sales value      {flt(value):,.0f}")
    print(f"  Collected        {flt(paid):,.0f}")
    print(f"  Outstanding      {flt(value) - flt(paid):,.0f}")


def clear():
    """Delete everything seed_data.run created (demo projects, their units, bookings, payments, customers)."""
    bookings = frappe.get_all("RE Booking", filters={"customer": ["in", CUSTOMERS]}, pluck="name")
    for b in bookings:
        for pe in frappe.get_all("Payment Entry", filters={"re_booking": b}, fields=["name", "docstatus"]):
            doc = frappe.get_doc("Payment Entry", pe.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Payment Entry", pe.name, force=1)
        doc = frappe.get_doc("RE Booking", b)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc("RE Booking", b, force=1)

    for dt in ("RE Unit", "RE Tower"):
        for n in frappe.get_all(dt, filters={"project": ["in", DEMO_PROJECTS]}, pluck="name"):
            frappe.delete_doc(dt, n, force=1)
    for p in DEMO_PROJECTS:
        if frappe.db.exists("RE Project", p):
            frappe.delete_doc("RE Project", p, force=1)
    for c in CUSTOMERS:
        if frappe.db.exists("Customer", c):
            try:
                frappe.delete_doc("Customer", c, force=1)
            except Exception as e:
                print(f"could not delete customer {c}: {e}")

    frappe.db.commit()
    print("Demo data removed.")
