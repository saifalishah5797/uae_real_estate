"""
Creates Project, Tower, Unit DocTypes for the real estate module.

Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.create_re_doctypes.run

Copy this file to: apps/uae_real_estate/uae_real_estate/create_re_doctypes.py
Requires developer_mode = 1 (so DocType files are written into the app).
"""
import frappe

APP = "uae_real_estate"
MODULE = "UAE Real Estate"  # must match the Module Def created by `bench new-app`

PERMS = [
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
        "name": "RE Project",
        "autoname": "field:project_name",
        "title_field": "project_name",
        "fields": [
            f("project_name", "Project Name", reqd=1, unique=1, in_list_view=1),
            f("status", "Status", "Select", options="Planning\nUnder Construction\nCompleted", default="Planning", in_list_view=1),
            f("city", "City / Emirate", in_list_view=1),
            f("location", "Location / Area"),
            f("rera_number", "RERA / Permit No."),
            f("launch_date", "Launch Date", "Date"),
            f("handover_date", "Expected Handover", "Date"),
            f("description", "Description", "Small Text"),
        ],
    },
    {
        "name": "RE Tower",
        "autoname": "format:{project}-{tower_name}",
        "title_field": "tower_name",
        "fields": [
            f("project", "Project", "Link", options="RE Project", reqd=1, in_list_view=1),
            f("tower_name", "Tower / Block Name", reqd=1, in_list_view=1),
            f("total_floors", "Total Floors", "Int", in_list_view=1),
            f("status", "Status", "Select", options="Planning\nUnder Construction\nCompleted", default="Planning"),
        ],
    },
    {
        "name": "RE Unit",
        "autoname": "format:{tower}-{unit_no}",
        "title_field": "unit_no",
        "fields": [
            f("unit_no", "Unit No", reqd=1, in_list_view=1),
            f("project", "Project", "Link", options="RE Project", reqd=1, in_list_view=1),
            f("tower", "Tower", "Link", options="RE Tower", reqd=1, in_list_view=1),
            f("floor", "Floor", "Int", reqd=1),
            f("unit_type", "Unit Type", "Select", options="Studio\n1BR\n2BR\n3BR\n4BR\nPenthouse\nShop\nOffice", in_list_view=1),
            f("facing", "Facing / View", "Select", options="\nNorth\nSouth\nEast\nWest\nSea View\nCity View\nGarden View"),
            f("status", "Status", "Select", options="Available\nHold\nBooked\nSold", default="Available", in_list_view=1, in_standard_filter=1),
            f("area_section", "Area (sq ft)", "Section Break"),
            f("carpet_area", "Carpet Area", "Float"),
            f("builtup_area", "Built-up Area", "Float"),
            f("super_builtup_area", "Saleable / Super Built-up Area", "Float", reqd=1),
            f("price_section", "Pricing", "Section Break"),
            f("base_rate", "Base Rate per sq ft", "Currency", reqd=1),
            f("floor_rise", "Floor Rise Charge", "Currency"),
            f("plc", "Preferred Location Charge (PLC)", "Currency"),
            f("parking_charges", "Parking Charges", "Currency"),
            f("total_price", "Total Price", "Currency", read_only=1, in_list_view=1),
        ],
    },
]

UNIT_CONTROLLER = '''import frappe
from frappe.model.document import Document


class REUnit(Document):
    def validate(self):
        self.calculate_total_price()

    def calculate_total_price(self):
        area = self.super_builtup_area or 0
        rate = self.base_rate or 0
        self.total_price = (
            area * rate
            + (self.floor_rise or 0)
            + (self.plc or 0)
            + (self.parking_charges or 0)
        )
'''


def run():
    if not frappe.db.exists("Module Def", MODULE):
        frappe.throw(f"Module Def '{MODULE}' not found. Check MODULE in this script.")
    if not frappe.conf.developer_mode:
        frappe.throw("Enable developer_mode first: bench --site uae.localhost set-config developer_mode 1")

    for spec in DOCTYPES:
        if frappe.db.exists("DocType", spec["name"]):
            print(f"skip (exists): {spec['name']}")
            continue
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": spec["name"],
            "module": MODULE,
            "custom": 0,
            "autoname": spec["autoname"],
            "title_field": spec["title_field"],
            "track_changes": 1,
            "fields": spec["fields"],
            "permissions": PERMS,
        })
        doc.insert()
        print(f"created: {spec['name']}")

    # Unit price auto-calculation controller
    import os
    path = frappe.get_app_path(
        APP, frappe.scrub(MODULE), "doctype", "re_unit", "re_unit.py"
    )
    if os.path.isdir(os.path.dirname(path)):
        with open(path, "w") as fh:
            fh.write(UNIT_CONTROLLER)
        print(f"wrote controller: {path}")
    else:
        print("controller folder not found; add calculate_total_price to re_unit.py manually")

    frappe.db.commit()
    frappe.clear_cache()
    print("Done. Run: bench --site uae.localhost migrate && bench restart")
