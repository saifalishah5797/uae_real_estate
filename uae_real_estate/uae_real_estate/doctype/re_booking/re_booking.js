frappe.ui.form.on("RE Booking", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

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
