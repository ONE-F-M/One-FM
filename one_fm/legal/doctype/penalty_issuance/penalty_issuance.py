# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.assign_to import add as assign_to

class PenaltyIssuance(Document):
	def after_insert(self):
		self.validate_location()
	
	def on_submit(self):
		self.issue_penalty()

	def validate_location(self):
		if self.different_location:
			subject = _("Penalty Issuance Review")
			message = _("Please review the penalty issuance. The penalty location details were added manually by the supervisor.")
			recipient = ["legal@one-fm.com"]
			frappe.sendmail(recipient, subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)

	def issue_penalty(self):
		for employee in self.employees:
			if frappe.db.exists("Penalty", {"recipient_employee": employee.employee_id, "penalty_issuance": self.name}):
				frappe.throw(_("Penalty already issued to the employee linked to this Penalty Issuance record."))
			user_id = frappe.get_value("Employee", employee.employee_id, "user_id")
			
			penalty = frappe.new_doc("Penalty")
			penalty.penalty_issuance = self.name
			penalty.penalty_issuance_time = self.issuing_time

			penalty.location = self.location

			penalty.issuer_employee = self.issuing_employee
			penalty.issuer_name = self.employee_name
			penalty.issuer_designation = self.designation
			
			penalty.recipient_employee = employee.employee_id
			penalty.recipient_name = employee.employee_name
			penalty.recipient_designation = employee.designation
			penalty.recipient_user = user_id
			
			penalty.penalty_occurence_time = self.penalty_occurence_time
			penalty.penalty_location = self.penalty_location
			penalty.shift = self.shift
			penalty.site = self.site
			penalty.site_location = self.site_location
			penalty.project = self.project

			for penalty_detail in self.penalty_issuance_details:
				penalty_details = {
					"penalty_type": penalty_detail.penalty_type,
					"penalty_type_arabic": penalty_detail.penalty_type_arabic,
					"exact_notes": penalty_detail.exact_notes,
					"attachments": penalty_detail.attachments
				}
				occurences = self.get_occurences(employee.employee_id, penalty_detail.penalty_type)
				occurence = 0
				if len(occurences) > 0:
					#Check if penalty in between start and lapse period, increase the occurence count by 1 and get penalty for that occurence. Set start, lapse date and occurence count

					#If penalty occurence date is between start and lapse date, it means it occured in existing period. Otherwise reset the occurence counter
					if cstr(occurences[0].period_start_date) <= cstr(getdate(self.penalty_occurence_time)) <= cstr(occurences[0].period_lapse_date):
						existing_occurences = self.get_existing_occurences(employee.employee_id, penalty_detail.penalty_type, occurences[0].period_start_date, occurences[0].period_lapse_date, )
						if len(existing_occurences) < 7:
							occurence = len(existing_occurences) + 1
							penalty_details.update({
								'period_start_date': cstr(occurences[0].period_start_date),
								'period_lapse_date': cstr(occurences[0].period_lapse_date),
								'occurence_number': occurence
							})
						else:
							#What to do incase existing occurences are more than 6
							frappe.throw(_("Occurences more than 6"))
					else:
						occurence = 1
						penalty_details.update({
							'period_start_date': cstr(getdate(self.penalty_occurence_time)),
							'period_lapse_date': cstr(add_to_date(getdate(self.penalty_occurence_time), years=1)),
							'occurence_number': occurence
						})
					
				elif len(occurences) == 0:
					#Get penalty for first occurence and set start,lapse date and occurence count
					occurence = 1
					penalty_details.update({
						'period_start_date': cstr(getdate(self.penalty_occurence_time)),
						'period_lapse_date': cstr(add_to_date(getdate(self.penalty_occurence_time), years=1)),
						'occurence_number': occurence
					})
				
				penalty_levied_details = self.get_penalty_levied(occurence, penalty_detail.penalty_type)
				if penalty_levied_details:
					penalty_levied, deduction = penalty_levied_details
					penalty_details.update({
						'penalty_levied': penalty_levied,
						'deduction': deduction
					})
					print(penalty_details)
					penalty.append("penalty_details", penalty_details)

			penalty.save()
			assign_to({
				"assign_to": user_id,
				"doctype": penalty.doctype,
				"name": penalty.name,
				"description": "Penalty Issued by {employee_id}:{issuer}.".format(employee_id=self.issuing_employee, issuer=self.employee_name)
			})
		frappe.db.commit()

	def get_occurences(self, employee_id, penalty_type):
		penalties = frappe.db.sql("""
			SELECT PID.parent, PID.period_start_date, PID.period_lapse_date, PID.occurence_number, DATE(P.penalty_occurence_time) as penalty_date
			FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
			WHERE
				PID.penalty_type="{penalty_type}"
			AND P.recipient_employee="{emp}"
			AND P.workflow_state="Penalty Accepted"
			AND PID.parent=P.name
			AND PID.parenttype="Penalty"
			ORDER BY P.penalty_occurence_time DESC
		""".format(penalty_type=penalty_type, emp=employee_id), as_dict=1)
		return [penalties[0]] if penalties else []

	def get_existing_occurences(self, employee_id, penalty_type, start_date, lapse_date):
		penalties = frappe.db.sql("""
			SELECT tpd.parent
			FROM `tabPenalty` tp, `tabPenalty Issuance Details` tpd
			WHERE
				tpd.penalty_type="{penalty_type}"
			AND tp.recipient_employee="{emp}"
			AND tp.workflow_state="Penalty Accepted"
			AND tpd.parent=tp.name
			AND tpd.parenttype="Penalty"
			AND DATE(tp.penalty_occurence_time) BETWEEN DATE("{start_date}") AND DATE("{lapse_date}")
		""".format(penalty_type=penalty_type, emp=employee_id, start_date=cstr(start_date), lapse_date=cstr(lapse_date)), as_dict=1)
		print(penalties)
		return penalties


	# def get_occurence(self, employee_id, penalty_type):
	# 	print(employee_id, penalty_type)
	# 	penalties = frappe.db.sql("""
	# 		SELECT PID.parent, DATE(P.penalty_occurence_time) as penalty_date
	# 		FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
	# 		WHERE
	# 			PID.penalty_type="{penalty_type}"
	# 		AND P.recipient_employee="{emp}"
	# 		AND PID.parent=P.name
	# 		AND PID.parenttype="Penalty"
	# 		ORDER BY P.penalty_occurence_time ASC
	# 	""".format(penalty_type=penalty_type, emp=employee_id), as_dict=1)
	# 	#AND P.workflow_state="Penalty Accepted"
	# 	#Start and end penalty duration date
	# 	year, month, date = cstr(getdate(self.penalty_occurence_time)).split("-")
	# 	if len(penalties) > 0:
	# 		start_year, start_month, start_date = cstr(penalties[0].penalty_date).split("-")
	# 	else:
	# 		start_year, start_month, start_date = cstr(getdate(self.penalty_occurence_time)).split("-")

	# 	penalty_duration_start = year+"-"+start_month+"-"+start_date
	# 	penalty_duration_end = cstr(add_to_date(year+"-"+start_month+"-"+start_date, years=1))
	# 	print(penalty_duration_start, penalty_duration_end)

	# 	penalties = frappe.db.sql("""
	# 		SELECT PID.parent, DATE(P.penalty_occurence_time) as penalty_date
	# 		FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
	# 		WHERE
	# 			PID.penalty_type="{penalty_type}"
	# 		AND P.recipient_employee="{emp}"
	# 		AND PID.parent=P.name
	# 		AND PID.parenttype="Penalty"
	# 		AND DATE(P.penalty_occurence_time) BETWEEN DATE("{penalty_duration_start}") AND DATE("{penalty_duration_end}")
	# 		ORDER BY P.penalty_occurence_time ASC
	# 	""".format(
	# 		penalty_type=penalty_type, 
	# 		emp=employee_id, 
	# 		penalty_duration_start=penalty_duration_start, 
	# 		penalty_duration_end=penalty_duration_end
	# 	), as_dict=1)


	# 	occurences = len(penalties) + 1
	# 	penalty_list_field_map = {
	# 		"1": "first_occurence",
	# 		"2": "second_occurence",
	# 		"3": "third_occurence",
	# 		"4": "fourth_occurence",
	# 		"5": "fifth_occurence"
	# 	}

	# 	occurence_count = "1"
	# 	if 0 < occurences <= 5:
	# 		occurence_count = cstr(occurences)
	# 	elif occurences > 5:
	# 		occurence_count = "5" 

	# 	return penalty_list_field_map[occurence_count], occurence_count

	def get_penalty_levied(self, occurence, penalty_type):
		field1 = "occurence_type"+cstr(occurence)
		field2 = "occurence"+cstr(occurence)
		
		penalty_levied = frappe.db.sql("""
			SELECT pd.{field1}, pd.{field2}
			FROM `tabPenalty Details` pd, `tabPenalty List` pl
			WHERE
				pd.parent=pl.name
			AND pl.active=1
			AND pd.penalty_description_english="{penalty_type}"
		""".format(field1=field1, field2=field2, penalty_type=penalty_type))
		return penalty_levied[0] if penalty_levied else False

@frappe.whitelist()
def get_current_penalty_location(location, penalty_occurence_time):
	latitude, longitude = location.split(",")
	site = frappe.db.sql("""
		SELECT
			(((acos(
				sin(( {latitude} * pi() / 180))
				*
				sin(( loc.latitude * pi() / 180)) + cos(( {latitude} * pi() /180 ))
				*
				cos(( loc.latitude  * pi() / 180)) * cos((( {longitude} - loc.longitude) * pi()/180))
			))
			* 180/pi()) * 60 * 1.1515 * 1.609344 * 1000
			)AS distance, os.name, os.site_location, os.project FROM `tabLocation` AS loc, `tabOperations Site` AS os
	WHERE os.site_location = loc.name ORDER BY distance ASC """.format(latitude=latitude, longitude=longitude), as_dict=1)

	site_name = site[0].name

	print(site[0])
	print(not site or (site and site[0].distance > 100))
	if not site or (site and site[0].distance > 100):
		frappe.throw(_("No active shift and site found matching current time and location. Please enter manually."))

	#Check for active shift at the closest site.
	active_shift = frappe.db.sql("""
		SELECT 
			name 
		FROM `tabOperations Shift`
		WHERE 
			site="{site_name}" AND
			CAST("{current_time}" as datetime) 
			BETWEEN
				CAST(start_time as datetime) 
			AND 
				IF(end_time < start_time, DATE_ADD(CAST(end_time as datetime), INTERVAL 1 DAY), CAST(end_time as datetime)) 
			
	""".format(current_time=penalty_occurence_time, site_name=site_name), as_dict=1)

	print(active_shift)
	if len(active_shift) > 0:
		return {
			'shift': active_shift[0].name,
			'site': site[0].name,
			'site_location': site[0].site_location,
			'project': site[0].project
		}
	else:
		return ''


@frappe.whitelist()
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	print("CALLED",filters)
	shift = filters.get('shift')
	time = filters.get('penalty_occurence_time')
	print("""
		SELECT employee, employee_name FROM `tabShift Assignment` WHERE shift="{shift}" AND date=DATE({date})
	""".format(shift=shift, date=time))
	return frappe.db.sql("""
		SELECT employee, employee_name
		FROM `tabShift Assignment`
		WHERE shift="{shift}" AND date=DATE("{date}")
	""".format(shift=shift, date=time))