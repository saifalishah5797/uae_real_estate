"""
Booking -> Payment Entry integration (v2: also keeps Total Paid / Outstanding on the booking).

Copy to: apps/uae_real_estate/uae_real_estate/payments.py   (replace the old file)
Run setup_dashboard.run BEFORE using this version (it adds the total_paid / outstanding fields).

Provides:
  make_payment_entry(booking, row_idx, amount)  - called by the "Payment Entry" button on RE Booking
  update_booking_payment(doc, method)           - hooked on Payment Entry submit / cancel
"""
import frappe
from frappe import _
from frappe.utils import flt, nowdate


@frappe.whitelist()
def make_payment_entry(booking, row_idx, amount=None):
    bk = frappe.get_doc("RE Booking", booking)
    if bk.docstatus != 1:
        frappe.throw(_("Submit the booking before collecting payments."))

    row = next((r for r in bk.payment_schedule if r.idx == int(row_idx)), None)
    if not row:
        frappe.throw(_("Milestone row not found."))

    pending = flt(row.amount) - flt(row.paid_amount)
    amount = flt(amount) or pending
    if amount <= 0:
        frappe.throw(_("Nothing pending for this milestone."))
    if amount > pending + 0.01:
        frappe.throw(_("Amount {0} is more than the pending {1}.").format(amount, pending))

    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
        "Global Defaults", "default_company"
    )
    if not company:
        frappe.throw(_("Set a default Company first."))

    c = frappe.get_cached_doc("Company", company)
    receivable = c.default_receivable_account
    cash_or_bank = c.default_cash_account or c.default_bank_account
    if not receivable or not cash_or_bank:
        frappe.throw(
            _("Set Default Receivable Account and Default Cash/Bank Account in Company {0}.").format(company)
        )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.company = company
    pe.posting_date = nowdate()
    pe.party_type = "Customer"
    pe.party = bk.customer
    pe.paid_from = receivable
    pe.paid_to = cash_or_bank
    pe.paid_from_account_currency = c.default_currency
    pe.paid_to_account_currency = c.default_currency
    pe.source_exchange_rate = 1
    pe.target_exchange_rate = 1
    pe.paid_amount = amount
    pe.received_amount = amount
    pe.reference_no = bk.name
    pe.reference_date = nowdate()
    pe.remarks = _("{0} for booking {1}, unit {2}").format(row.milestone, bk.name, bk.unit)
    pe.re_booking = bk.name
    pe.re_booking_row = row.name
    pe.insert()
    return pe.name


def update_booking_payment(doc, method=None):
    row_name = doc.get("re_booking_row")
    if not row_name:
        return

    # 1) milestone row
    paid = frappe.db.sql(
        "select coalesce(sum(paid_amount), 0) from `tabPayment Entry` "
        "where re_booking_row = %s and docstatus = 1",
        row_name,
    )[0][0]
    amount = frappe.db.get_value("RE Booking Payment", row_name, "amount") or 0

    if flt(paid) >= flt(amount) - 0.01:
        status = "Paid"
    elif flt(paid) > 0:
        status = "Partly Paid"
    else:
        status = "Pending"

    frappe.db.set_value(
        "RE Booking Payment", row_name, {"paid_amount": paid, "payment_status": status}
    )

    # 2) booking totals (used by the dashboard)
    parent = frappe.db.get_value("RE Booking Payment", row_name, "parent")
    total_paid = frappe.db.sql(
        "select coalesce(sum(paid_amount), 0) from `tabRE Booking Payment` where parent = %s",
        parent,
    )[0][0]
    grand = frappe.db.get_value("RE Booking", parent, "grand_total") or 0
    frappe.db.set_value(
        "RE Booking",
        parent,
        {"total_paid": total_paid, "outstanding": flt(grand) - flt(total_paid)},
        update_modified=False,
    )
