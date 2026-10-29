"""
Step 3 setup: custom fields on Payment Entry + "Payment Entry" button on RE Booking.

Copy to: apps/uae_real_estate/uae_real_estate/add_payment_integration.py
Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.add_payment_integration.run
"""
import os
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

APP = "uae_real_estate"
MODULE = "UAE Real Estate"

BOOKING_JS = r"""frappe.ui.form.on("RE Booking", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        const open_rows = (frm.doc.payment_schedule || []).filter(
            (r) => r.payment_status !== "Paid"
        );
        if (!open_rows.length) return;

        frm.add_custom_button(
            __("Payment Entry"),
            () => {
                const labels = open_rows.map((r) => `${r.idx} - ${r.milestone}`);
                const pending_of = (label) => {
                    const idx = parseInt(label.split(" - ")[0]);
                    const r = open_rows.find((x) => x.idx === idx);
                    return r ? flt(r.amount) - flt(r.paid_amount) : 0;
                };
                const d = new frappe.ui.Dialog({
                    title: __("Collect Payment"),
                    fields: [
                        {
                            fieldname: "milestone",
                            label: __("Milestone"),
                            fieldtype: "Select",
                            options: labels,
                            default: labels[0],
                            reqd: 1,
                            onchange() {
                                d.set_value("amount", pending_of(d.get_value("milestone")));
                            },
                        },
                        {
                            fieldname: "amount",
                            label: __("Amount"),
                            fieldtype: "Currency",
                            default: pending_of(labels[0]),
                            reqd: 1,
                        },
                    ],
                    primary_action_label: __("Create Payment Entry"),
                    primary_action(values) {
                        frappe.call({
                            method: "uae_real_estate.payments.make_payment_entry",
                            args: {
                                booking: frm.doc.name,
                                row_idx: parseInt(values.milestone.split(" - ")[0]),
                                amount: values.amount,
                            },
                            callback(r) {
                                if (r.message) {
                                    d.hide();
                                    frappe.set_route("Form", "Payment Entry", r.message);
                                }
                            },
                        });
                    },
                });
                d.show();
            },
            __("Create")
        );
    },
});
"""


def run():
    create_custom_fields(
        {
            "Payment Entry": [
                {
                    "fieldname": "re_booking",
                    "label": "RE Booking",
                    "fieldtype": "Link",
                    "options": "RE Booking",
                    "insert_after": "party_name",
                    "read_only": 1,
                    "no_copy": 1,
                },
                {
                    "fieldname": "re_booking_row",
                    "label": "RE Booking Row",
                    "fieldtype": "Data",
                    "insert_after": "re_booking",
                    "read_only": 1,
                    "hidden": 1,
                    "no_copy": 1,
                },
            ]
        }
    )
    print("custom fields added on Payment Entry")

    path = frappe.get_app_path(APP, frappe.scrub(MODULE), "doctype", "re_booking", "re_booking.js")
    if os.path.isdir(os.path.dirname(path)):
        with open(path, "w") as fh:
            fh.write(BOOKING_JS)
        print(f"wrote: {path}")
    else:
        print("re_booking folder not found; run create_re_booking.run first")

    frappe.db.commit()
    frappe.clear_cache()
    print("Done. Now add doc_events to hooks.py, then: bench restart")
