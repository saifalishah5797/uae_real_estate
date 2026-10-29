app_name = "uae_real_estate"
app_title = "UAE Real Estate"
app_publisher = "Saif Ali"
app_description = "Real estate ERP: inventory, booking, payment plans"
app_email = "saifalishah5797@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "=", "Payment Entry"], ["fieldname", "in", ["re_booking", "re_booking_row"]]]},
    {"dt": "Number Card", "filters": [["module", "=", "UAE Real Estate"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "UAE Real Estate"]]},
    {"dt": "Dashboard", "filters": [["module", "=", "UAE Real Estate"]]},
    {"dt": "Workspace", "filters": [["module", "=", "UAE Real Estate"]]},
    {"dt": "RE Payment Plan Template"},
]
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/uae_real_estate/css/uae_real_estate.css"
# app_include_js = "/assets/uae_real_estate/js/uae_real_estate.js"

# include js, css files in header of web template
# web_include_css = "/assets/uae_real_estate/css/uae_real_estate.css"
# web_include_js = "/assets/uae_real_estate/js/uae_real_estate.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "uae_real_estate/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "uae_real_estate/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "uae_real_estate.utils.jinja_methods",
# 	"filters": "uae_real_estate.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "uae_real_estate.install.before_install"
# after_install = "uae_real_estate.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "uae_real_estate.uninstall.before_uninstall"
# after_uninstall = "uae_real_estate.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "uae_real_estate.utils.before_app_install"
# after_app_install = "uae_real_estate.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "uae_real_estate.utils.before_app_uninstall"
# after_app_uninstall = "uae_real_estate.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "uae_real_estate.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Payment Entry": {
        "on_submit": "uae_real_estate.payments.update_booking_payment",
        "on_cancel": "uae_real_estate.payments.update_booking_payment",
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"uae_real_estate.tasks.all"
# 	],
# 	"daily": [
# 		"uae_real_estate.tasks.daily"
# 	],
# 	"hourly": [
# 		"uae_real_estate.tasks.hourly"
# 	],
# 	"weekly": [
# 		"uae_real_estate.tasks.weekly"
# 	],
# 	"monthly": [
# 		"uae_real_estate.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "uae_real_estate.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "uae_real_estate.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "uae_real_estate.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["uae_real_estate.utils.before_request"]
# after_request = ["uae_real_estate.utils.after_request"]

# Job Events
# ----------
# before_job = ["uae_real_estate.utils.before_job"]
# after_job = ["uae_real_estate.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"uae_real_estate.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

