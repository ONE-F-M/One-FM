# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
    return [
        _("Accommodation") + ":Link/Accommodation:80",
		_("Unit") + ":Link/Accommodation Unit:80",
		_("Bed") + ":Link/Bed:120",
		_("Employee ID") + ":Data:120",
		_("Employee Name") + ":Data:180",
		_("CIVIL ID") + ":Data:100",
		_("Checkin") + ":Date:100",
		_("Checkin Ref") + ":Link/Accommodation Checkin Checkout:120",
		_("Checkout") + ":Date:100",
		_("Checkout Ref") + ":Link/Accommodation Checkin Checkout:120",
		_("Tenant Category") + ":Data:120"
    ]

def get_conditions(filters):
	conditions = ""
	fields = ['accommodation', 'accommodation_unit', 'bed', 'employee', 'employee_id', 'tenant_category']
	for field in fields:
		if filters.get(field):
			conditions += " and {0}='{1}' ".format(field, filters.get(field))
	return conditions

def get_data(filters):
	data=[]
	conditions = get_conditions(filters)
	acc_list=frappe.db.sql("""select * from `tabAccommodation Checkin Checkout` where type='IN' {0}""".format(conditions), as_dict=1)
	for acc in acc_list:
		checkout_date = ''
		checkout = ''
		accommodation_not_provided_by_company = True
		accommodation_by_company = False
		if acc.employee and filters.get('accommodation_not_provided_by_company'):
			accommodation_by_company = frappe.db.get_value('Employee', acc.employee, 'one_fm_provide_accommodation_by_company')
		if acc.checked_out:
			checkout = frappe.db.exists('Accommodation Checkin Checkout', {'checkin_reference': acc.name})
			if checkout:
				checkout_date = frappe.db.get_value('Accommodation Checkin Checkout', checkout, 'checkin_checkout_date_time')
		if accommodation_not_provided_by_company and not accommodation_by_company:
			row = [
				acc.accommodation,
				acc.accommodation_unit,
				acc.bed,
				acc.employee_id,
				acc.full_name,
				acc.civil_id,
				acc.checkin_checkout_date_time,
				acc.name,
				checkout_date,
				checkout,
				acc.tenant_category
			]
			data.append(row)

	return data
