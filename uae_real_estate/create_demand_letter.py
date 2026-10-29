"""
Demand Letter print format for RE Booking + a "Demand Letter" button on the booking form.

Copy to: apps/uae_real_estate/uae_real_estate/create_demand_letter.py   (same folder as hooks.py)
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.create_demand_letter.run
    bench --site uae.localhost clear-cache && bench restart

Re-run any time to refresh the template after editing HTML below.
"""
import os

import frappe

APP = "uae_real_estate"
MODULE = "UAE Real Estate"
FORMAT_NAME = "Demand Letter"

HTML = r"""
<style>
	.dl{font-family:Helvetica,Arial,sans-serif;color:#1f2937;font-size:12px;line-height:1.55}
	.dl-top{height:8px;background:linear-gradient(90deg,#1e3a8a,#6366f1,#06b6d4);border-radius:4px}
	.dl-head{display:flex;justify-content:space-between;align-items:flex-start;margin:18px 0 22px}
	.dl-co{font-size:20px;font-weight:800;color:#1e3a8a}
	.dl-sub{color:#6b7280;font-size:11px}
	.dl-ref{text-align:right;font-size:11px;color:#374151}
	.dl-ref b{color:#111827}
	.dl h2{font-size:15px;margin:0 0 10px;color:#111827}
	.dl-box{border:1px solid #c7d2fe;background:#eef2ff;border-radius:10px;padding:14px 18px;margin:16px 0;display:flex;justify-content:space-between;align-items:center}
	.dl-box.late{border-color:#fecdd3;background:#fff1f2}
	.dl-box .lbl{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#6b7280}
	.dl-box .amt{font-size:24px;font-weight:800;color:#1e3a8a}
	.dl-box.late .amt{color:#be123c}
	.dl-meta{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0}
	.dl-meta div{min-width:120px}
	.dl-meta .k{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#6b7280}
	.dl-meta .v{font-weight:700;font-size:13px}
	.dl table{width:100%;border-collapse:collapse;margin-top:8px}
	.dl th{background:#1e3a8a;color:#fff;font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:8px;text-align:left}
	.dl td{padding:8px;border-bottom:1px solid #e5e7eb;font-size:11.5px}
	.dl .r{text-align:right}
	.dl tr.cur td{background:#fefce8;font-weight:700}
	.dl .pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:700}
	.dl-sum{margin:14px 0 0 auto;width:55%}
	.dl-sum td{border:0;padding:4px 8px}
	.dl-sum tr.tot td{border-top:2px solid #1e3a8a;font-weight:800;font-size:13px}
	.dl-note{margin-top:22px;font-size:11px;color:#4b5563}
	.dl-sign{margin-top:46px;font-size:12px}
	.dl-foot{margin-top:30px;padding-top:8px;border-top:1px solid #e5e7eb;font-size:10px;color:#9ca3af;text-align:center}
</style>

{% set company = frappe.db.get_single_value("Global Defaults", "default_company") or "" %}
{% set cur = (frappe.db.get_value("Company", company, "default_currency") if company else "AED") or "AED" %}
{% set ns = namespace(nxt=none) %}
{% for r in doc.payment_schedule %}
	{% if r.payment_status != "Paid" and ns.nxt is none %}{% set ns.nxt = r %}{% endif %}
{% endfor %}
{% set days_late = frappe.utils.date_diff(frappe.utils.nowdate(), ns.nxt.due_date) if ns.nxt else 0 %}

<div class="dl">
	<div class="dl-top"></div>

	<div class="dl-head">
		<div>
			<div class="dl-co">{{ company or "Real Estate Developer" }}</div>
			<div class="dl-sub">Accounts &amp; Collections Department</div>
		</div>
		<div class="dl-ref">
			Ref: <b>{{ doc.name }}-DL</b><br>
			Date: <b>{{ frappe.utils.formatdate(frappe.utils.nowdate()) }}</b>
		</div>
	</div>

	<div>
		<b>To:</b> {{ doc.customer }}<br>
		<b>Unit:</b> {{ doc.unit }} &nbsp;|&nbsp; <b>Project:</b> {{ doc.project }} &nbsp;|&nbsp; <b>Tower:</b> {{ doc.tower }}
	</div>

	<h2 style="margin-top:20px">Subject: Payment Demand &ndash; {% if ns.nxt %}{{ ns.nxt.milestone }}{% else %}Statement of Account{% endif %}</h2>

	<p>Dear {{ doc.customer }},</p>

	{% if ns.nxt %}
		<p>
			Thank you for choosing to invest with us. As per the payment plan agreed for your unit
			<b>{{ doc.unit }}</b> (booking <b>{{ doc.name }}</b> dated {{ frappe.utils.formatdate(doc.booking_date) }}),
			we request you to settle the following installment
			{% if days_late > 0 %}which was due on <b>{{ frappe.utils.formatdate(ns.nxt.due_date) }}</b>
			and is now <b>{{ days_late }} day{{ "s" if days_late != 1 }} overdue</b>{% else %}
			falling due on <b>{{ frappe.utils.formatdate(ns.nxt.due_date) }}</b>{% endif %}.
		</p>

		<div class="dl-box {{ 'late' if days_late > 0 }}">
			<div>
				<div class="lbl">Amount Due &ndash; {{ ns.nxt.milestone }}</div>
				<div class="amt">{{ frappe.utils.fmt_money(ns.nxt.amount - ns.nxt.paid_amount, currency=cur) }}</div>
			</div>
			<div style="text-align:right">
				<div class="lbl">Due Date</div>
				<div style="font-size:16px;font-weight:800">{{ frappe.utils.formatdate(ns.nxt.due_date) }}</div>
			</div>
		</div>
	{% else %}
		<p>
			We are pleased to confirm that all installments for your unit <b>{{ doc.unit }}</b> (booking
			<b>{{ doc.name }}</b>) have been received in full. Please find your statement of account below.
		</p>
	{% endif %}

	<div class="dl-meta">
		<div><div class="k">Net Price</div><div class="v">{{ doc.get_formatted("net_price") }}</div></div>
		<div><div class="k">VAT ({{ doc.vat_percent }}%)</div><div class="v">{{ doc.get_formatted("vat_amount") }}</div></div>
		<div><div class="k">Total Payable</div><div class="v">{{ doc.get_formatted("grand_total") }}</div></div>
	</div>

	<h2>Payment Schedule</h2>
	<table>
		<thead>
			<tr><th>#</th><th>Milestone</th><th>Due Date</th><th class="r">%</th>
			<th class="r">Amount</th><th class="r">Paid</th><th>Status</th></tr>
		</thead>
		<tbody>
		{% for r in doc.payment_schedule %}
			<tr class="{{ 'cur' if ns.nxt and r.name == ns.nxt.name }}">
				<td>{{ loop.index }}</td>
				<td>{{ r.milestone }}</td>
				<td>{{ frappe.utils.formatdate(r.due_date) }}</td>
				<td class="r">{{ r.percentage }}%</td>
				<td class="r">{{ r.get_formatted("amount") }}</td>
				<td class="r">{{ r.get_formatted("paid_amount") }}</td>
				<td>
					{% if r.payment_status == "Paid" %}
						<span class="pill" style="background:#d1fae5;color:#047857">Paid</span>
					{% elif r.payment_status == "Partly Paid" %}
						<span class="pill" style="background:#fef3c7;color:#b45309">Partly Paid</span>
					{% else %}
						<span class="pill" style="background:#e0e7ff;color:#3730a3">Pending</span>
					{% endif %}
				</td>
			</tr>
		{% endfor %}
		</tbody>
	</table>

	<table class="dl-sum">
		<tr><td>Total Payable</td><td class="r">{{ doc.get_formatted("grand_total") }}</td></tr>
		<tr><td>Total Received</td><td class="r">{{ doc.get_formatted("total_paid") }}</td></tr>
		<tr class="tot"><td>Balance Outstanding</td><td class="r">{{ doc.get_formatted("outstanding") }}</td></tr>
	</table>

	<div class="dl-note">
		Please make payment by bank transfer, cheque or the payment link shared by our team, quoting
		reference <b>{{ doc.name }}</b>. Kindly ignore this letter if payment has already been made, and share the
		transaction details so we can update your account. For any query, contact our collections team.
	</div>

	<div class="dl-sign">
		Yours sincerely,<br><br><br>
		<b>Accounts Department</b><br>{{ company }}
	</div>

	<div class="dl-foot">This is a system generated letter and does not require a signature.</div>
</div>
"""

BUTTON_JS = """
        frm.add_custom_button(
            __("Demand Letter (PDF)"),
            () => {
                const url =
                    "/api/method/frappe.utils.print_format.download_pdf?doctype=" +
                    encodeURIComponent(frm.doctype) +
                    "&name=" + encodeURIComponent(frm.doc.name) +
                    "&format=" + encodeURIComponent("Demand Letter") +
                    "&no_letterhead=1";
                window.open(frappe.urllib.get_full_url(url));
            },
            __("Create")
        );
"""


def run():
    if not frappe.conf.developer_mode:
        frappe.throw("Enable developer_mode first: bench --site uae.localhost set-config developer_mode 1")

    # 1. Print format
    if frappe.db.exists("Print Format", FORMAT_NAME):
        pf = frappe.get_doc("Print Format", FORMAT_NAME)
        pf.html = HTML
        pf.save()
        print("print format updated")
    else:
        frappe.get_doc({
            "doctype": "Print Format",
            "name": FORMAT_NAME,
            "doc_type": "RE Booking",
            "module": MODULE,
            "standard": "Yes",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": HTML,
            "disabled": 0,
        }).insert()
        print("print format created")

    # 2. Button on the booking form
    path = frappe.get_app_path(APP, frappe.scrub(MODULE), "doctype", "re_booking", "re_booking.js")
    if os.path.exists(path):
        with open(path) as fh:
            js = fh.read()
        anchor = "if (frm.doc.docstatus !== 1) return;\n"
        if "Demand Letter" in js:
            print("button already present")
        elif anchor in js:
            with open(path, "w") as fh:
                fh.write(js.replace(anchor, anchor + BUTTON_JS, 1))
            print("button added to re_booking.js")
        else:
            print("could not patch re_booking.js; use the Print icon -> Demand Letter instead")
    else:
        print("re_booking.js not found; use the Print icon -> Demand Letter instead")

    frappe.db.commit()
    frappe.clear_cache()
    print("\nDone. Run: bench --site uae.localhost clear-cache && bench restart")
