"""
End-to-end test for the Real Estate flow.

Copy to: apps/uae_real_estate/uae_real_estate/e2e_test.py   (same folder as hooks.py)
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.e2e_test.run

Flow:
  Project -> Tower -> Unit -> Customer -> Booking (draft) -> Submit
  -> double-booking blocked -> Payment Entry (full) -> Payment Entry (partial)
  -> cancel payment -> cancel booking -> unit released
"""
import frappe
from frappe.utils import flt

from uae_real_estate.payments import make_payment_entry

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition)))
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail and not condition else ""))


def step(title):
    print(f"\n== {title}")


def get_or_create(doctype, name, values):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.get_doc({"doctype": doctype, **values}).insert()


def run():
    results.clear()
    suffix = frappe.generate_hash(length=4).upper()

    # ---------- master data ----------
    step("1. Project, Tower, Unit")
    project = get_or_create("RE Project", "E2E Project", {"project_name": "E2E Project", "city": "Dubai"})
    tower = get_or_create("RE Tower", "E2E Project-A", {"project": project.name, "tower_name": "A", "total_floors": 20})
    unit = frappe.get_doc({
        "doctype": "RE Unit",
        "unit_no": suffix,
        "project": project.name,
        "tower": tower.name,
        "floor": 1,
        "unit_type": "2BR",
        "super_builtup_area": 1000,
        "base_rate": 500,
        "floor_rise": 10000,
    }).insert()
    check("Unit total price = 1000*500 + 10000 = 510000", flt(unit.total_price) == 510000, unit.total_price)
    check("Unit starts as Available", unit.status == "Available", unit.status)

    # ---------- customer ----------
    step("2. Customer")
    cg = frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_value(
        "Customer Group", {"is_group": 0}
    )
    terr = frappe.db.get_single_value("Selling Settings", "territory") or frappe.db.get_value(
        "Territory", {"is_group": 0}
    )
    customer = get_or_create("Customer", "E2E Test Customer", {
        "customer_name": "E2E Test Customer",
        "customer_type": "Individual",
        "customer_group": cg,
        "territory": terr,
    })
    check("Customer exists", frappe.db.exists("Customer", customer.name))

    # ---------- booking ----------
    step("3. Booking (draft)")
    booking = frappe.get_doc({
        "doctype": "RE Booking",
        "customer": customer.name,
        "unit": unit.name,
        "payment_plan": "10-20-30-40 Plan",
    }).insert()
    check("Net price = 510000", flt(booking.net_price) == 510000, booking.net_price)
    check("VAT 5% = 25500", flt(booking.vat_amount) == 25500, booking.vat_amount)
    check("Grand total = 535500", flt(booking.grand_total) == 535500, booking.grand_total)
    check("Schedule has 4 rows", len(booking.payment_schedule) == 4, len(booking.payment_schedule))
    check("Schedule sums to grand total",
          abs(sum(flt(r.amount) for r in booking.payment_schedule) - flt(booking.grand_total)) < 0.01)
    check("Milestone 1 = 53550", flt(booking.payment_schedule[0].amount) == 53550, booking.payment_schedule[0].amount)
    check("Unit still Available before submit",
          frappe.db.get_value("RE Unit", unit.name, "status") == "Available")

    # ---------- submit ----------
    step("4. Submit booking")
    booking.submit()
    check("Unit becomes Booked", frappe.db.get_value("RE Unit", unit.name, "status") == "Booked")

    # ---------- double booking ----------
    step("5. Double booking must be blocked")
    blocked = False
    try:
        frappe.get_doc({
            "doctype": "RE Booking",
            "customer": customer.name,
            "unit": unit.name,
            "payment_plan": "10-20-30-40 Plan",
        }).insert()
    except frappe.ValidationError:
        blocked = True
    check("Second booking on same unit is rejected", blocked)

    # ---------- payments ----------
    step("6. Payment Entry - full payment of milestone 1")
    pe1_name = make_payment_entry(booking.name, 1, None)
    pe1 = frappe.get_doc("Payment Entry", pe1_name)
    check("Payment Entry draft created", pe1.docstatus == 0)
    check("Payment Entry amount = 53550", flt(pe1.paid_amount) == 53550, pe1.paid_amount)
    pe1.submit()
    booking.reload()
    row1 = booking.payment_schedule[0]
    check("Milestone 1 paid_amount = 53550", flt(row1.paid_amount) == 53550, row1.paid_amount)
    check("Milestone 1 status = Paid", row1.payment_status == "Paid", row1.payment_status)

    step("7. Payment Entry - partial payment of milestone 2")
    pe2_name = make_payment_entry(booking.name, 2, 50000)
    pe2 = frappe.get_doc("Payment Entry", pe2_name)
    pe2.submit()
    booking.reload()
    row2 = booking.payment_schedule[1]
    check("Milestone 2 paid_amount = 50000", flt(row2.paid_amount) == 50000, row2.paid_amount)
    check("Milestone 2 status = Partly Paid", row2.payment_status == "Partly Paid", row2.payment_status)

    step("8. Over-payment must be blocked")
    blocked = False
    try:
        make_payment_entry(booking.name, 2, 999999)
    except frappe.ValidationError:
        blocked = True
    check("Amount above pending is rejected", blocked)

    step("9. Cancel the partial payment")
    pe2.reload()
    pe2.cancel()
    booking.reload()
    row2 = booking.payment_schedule[1]
    check("Milestone 2 back to Pending", row2.payment_status == "Pending", row2.payment_status)
    check("Milestone 2 paid_amount = 0", flt(row2.paid_amount) == 0, row2.paid_amount)

    # ---------- cancel booking ----------
    step("10. Cancel booking releases the unit")
    pe1.reload()
    pe1.cancel()  # booking cannot be cancelled while a submitted payment links to it
    booking.reload()
    booking.cancel()
    check("Unit back to Available", frappe.db.get_value("RE Unit", unit.name, "status") == "Available")

    frappe.db.commit()

    # ---------- summary ----------
    passed = sum(1 for _, ok in results if ok)
    print(f"\n==== {passed}/{len(results)} checks passed ====")
    for name, ok in results:
        if not ok:
            print("  FAILED: " + name)
    if passed == len(results):
        print("All good. Flow works end to end.")
