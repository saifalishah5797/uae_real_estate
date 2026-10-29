import frappe
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
