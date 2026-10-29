"""
Data API for the Real Estate Command Center page.

Copy to: apps/uae_real_estate/uae_real_estate/dashboard_api.py   (same folder as hooks.py)
"""
import frappe
from frappe.utils import add_months, flt, getdate, nowdate


def _currency():
    try:
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
            "Global Defaults", "default_company"
        )
        return frappe.get_cached_value("Company", company, "default_currency") or "AED"
    except Exception:
        return "AED"


@frappe.whitelist()
def get_dashboard_data(project=None):
    frappe.has_permission("RE Booking", "read", throw=True)

    p = {"project": project} if project else {}
    pf = " and project = %(project)s" if project else ""
    bpf = " and b.project = %(project)s" if project else ""
    today = nowdate()

    # ---------------- units
    units_by_status = {
        r.status: r.n
        for r in frappe.db.sql(
            f"select status, count(*) n from `tabRE Unit` where 1=1 {pf} group by status", p, as_dict=1
        )
    }
    total_units = sum(units_by_status.values())

    # ---------------- bookings / money
    k = frappe.db.sql(
        f"""select count(*) bookings,
                   coalesce(sum(grand_total),0) sales,
                   coalesce(sum(total_paid),0) collected,
                   coalesce(sum(outstanding),0) outstanding
            from `tabRE Booking` where docstatus = 1 {pf}""",
        p, as_dict=1,
    )[0]
    pct = (flt(k.collected) / flt(k.sales) * 100) if flt(k.sales) else 0

    overdue = frappe.db.sql(
        f"""select coalesce(sum(r.amount - r.paid_amount),0) amt, count(*) n
            from `tabRE Booking Payment` r join `tabRE Booking` b on b.name = r.parent
            where b.docstatus = 1 and r.payment_status != 'Paid' and r.due_date < %(today)s {bpf}""",
        {**p, "today": today}, as_dict=1,
    )[0]

    # ---------------- by project (always all projects)
    by_project = frappe.db.sql(
        """select b.project, count(*) bookings,
                  coalesce(sum(b.grand_total),0) sales,
                  coalesce(sum(b.total_paid),0) collected,
                  coalesce(sum(b.outstanding),0) outstanding
           from `tabRE Booking` b where b.docstatus = 1 group by b.project order by sales desc""",
        as_dict=1,
    )

    # ---------------- monthly trend (12 months)
    first = getdate(today).replace(day=1)
    months = [add_months(first, -i) for i in range(11, -1, -1)]
    rows = frappe.db.sql(
        f"""select date_format(booking_date, '%%Y-%%m') m, count(*) c, coalesce(sum(grand_total),0) v
            from `tabRE Booking`
            where docstatus = 1 and booking_date >= %(since)s {pf}
            group by m""",
        {**p, "since": months[0]}, as_dict=1,
    )
    lookup = {r.m: r for r in rows}
    monthly = []
    for m in months:
        key = m.strftime("%Y-%m")
        r = lookup.get(key)
        monthly.append({"label": m.strftime("%b %y"), "count": r.c if r else 0, "value": flt(r.v) if r else 0})

    # ---------------- stack plan
    tower_filters = {"project": project} if project else {}
    towers = frappe.get_all("RE Tower", filters=tower_filters, fields=["name", "project", "tower_name"],
                            order_by="project, tower_name")
    units = frappe.get_all(
        "RE Unit", filters=tower_filters,
        fields=["name", "unit_no", "tower", "floor", "status", "unit_type", "total_price"],
        order_by="tower, floor, unit_no", limit_page_length=600,
    )

    # ---------------- recent bookings
    recent = frappe.get_all(
        "RE Booking", filters={"docstatus": 1, **tower_filters},
        fields=["name", "customer", "unit", "booking_date", "grand_total", "total_paid", "outstanding"],
        order_by="booking_date desc, creation desc", limit_page_length=8,
    )

    # ---------------- payments due
    due = frappe.db.sql(
        f"""select r.parent booking, b.customer, b.unit, r.milestone, r.due_date,
                   (r.amount - r.paid_amount) pending, r.payment_status
            from `tabRE Booking Payment` r join `tabRE Booking` b on b.name = r.parent
            where b.docstatus = 1 and r.payment_status != 'Paid' {bpf}
            order by r.due_date asc limit 8""",
        p, as_dict=1,
    )

    return {
        "currency": _currency(),
        "kpis": {
            "total_units": total_units,
            "available": units_by_status.get("Available", 0),
            "hold": units_by_status.get("Hold", 0),
            "booked": units_by_status.get("Booked", 0),
            "sold": units_by_status.get("Sold", 0),
            "bookings": k.bookings,
            "sales": flt(k.sales),
            "collected": flt(k.collected),
            "outstanding": flt(k.outstanding),
            "collection_pct": round(pct, 1),
            "overdue_amount": flt(overdue.amt),
            "overdue_count": overdue.n,
        },
        "units_by_status": units_by_status,
        "by_project": by_project,
        "monthly": monthly,
        "towers": towers,
        "units": units,
        "recent": recent,
        "due": due,
    }
