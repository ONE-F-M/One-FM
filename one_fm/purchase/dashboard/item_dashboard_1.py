from __future__ import unicode_literals

import frappe
from frappe.model.db_query import DatabaseQuery

@frappe.whitelist()
def get_data(item_code=None, warehouse=None, item_group=None,
	start=0, sort_by='', sort_order='desc'):
	'''Return data to render the item dashboard'''
	filters = []
	if item_code:
		filters.append(['item_code', '=', item_code])
	if warehouse:
		filters.append(['warehouse', '=', warehouse])
	if item_group:
		lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
		items = frappe.db.sql_list("""
			select i.name from `tabItem` i
			where exists(select name from `tabItem Group`
				where name=i.item_group and lft >=%s and rgt<=%s)
		""", (lft, rgt))
		filters.append(['item_code', 'in', items])
	try:
		# check if user has any restrictions based on user permissions on warehouse
		if DatabaseQuery('Warehouse', user=frappe.session.user).build_match_conditions():
			filters.append(['warehouse', 'in', [w.name for w in frappe.get_list('Warehouse')]])
	except frappe.PermissionError:
		# user does not have access on warehouse
		return []

	# items = frappe.db.get_all('Bin', fields=['item_code', 'warehouse', 'projected_qty',
	# 		'reserved_qty', 'reserved_qty_for_production', 'reserved_qty_for_sub_contract', 'actual_qty', 'valuation_rate'],
	# 	or_filters={
	# 		'projected_qty': ['!=', 0],
	# 		'reserved_qty': ['!=', 0],
	# 		'reserved_qty_for_production': ['!=', 0],
	# 		'reserved_qty_for_sub_contract': ['!=', 0],
	# 		'actual_qty': ['!=', 0],
	# 	},
	# 	filters=filters,
	# 	order_by=sort_by + ' ' + sort_order,
	# 	limit_start=start,
	# 	limit_page_length='21')
	filters.append(['docstatus', '<', 2])
	items = frappe.db.get_all('Request for Material', fields=['name'],
		filters=filters,
		limit_start=start,
		limit_page_length='21')

	for item in items:
		exists_rfp = frappe.db.exists('Request for Purchase', {'request_for_material': item.name})
		item.update({'rfp': ''})
		item.update({'po': ''})
		item.update({'po_workflow': ''})
		item.update({'pr': ''})
		item.update({'pi': ''})
		item.update({'pi_status': ''})
		item.update({'progress': 20})
		item.update({'progress_bgc': '00FF00;'})
		item.update({'rfm_status': frappe.db.get_value('Request for Material', item.name, 'docstatus')})
		item.update({'rfp_status': ''})
		item.update({'po_status': ''})
		item.update({'pr_status': ''})
		if exists_rfp:
			item.update({'rfp': exists_rfp})
			item.update({'progress': 40})
			item.update({'rfp_status': frappe.db.get_value('Request for Purchase', exists_rfp, 'docstatus')})
			exists_po = frappe.db.exists('Purchase Order', {'one_fm_request_for_purchase': exists_rfp})
			if exists_po:
				item.update({'progress': 60})
				item.update({'po': exists_po})
				item.update({'po_status': frappe.db.get_value('Purchase Order', exists_po, 'docstatus')})
				item.update({'po_workflow': frappe.db.get_value('Purchase Order', exists_po, 'workflow_state')})
				# exists_pr = frappe.db.exists('Purchase Receipt', {'purchase_order': exists_po})
				query = """
					select
						distinct pr.name, pr.docstatus
					from
						`tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
					where
						pri.parent=pr.name and pri.purchase_order=%s
				"""
				pr_list = frappe.db.sql(query, (exists_po), as_dict=True)
				if pr_list:
					item.update({'progress': 80})
					i = 1
					for pr in pr_list:
						if i == 1:
							item.update({'pr': pr.name})
							item.update({'pr_status': pr.docstatus})
							query = """
								select
									distinct pi.name, pi.docstatus
								from
									`tabPurchase Invoice` pi, `tabPurchase Invoice Item` pii
								where
									pii.parent=pi.name and pii.purchase_receipt=%s
							"""
							pi_list = frappe.db.sql(query, (pr.name), as_dict=True)
							if pi_list:
								item.update({'progress': 100})
								item.update({'progress_bgc': 'blue;'})
								j = 1
								for pi in pi_list:
									if j == 1:
										item.update({'pi': pi.name})
										item.update({'pi_status': pi.docstatus})
									j += 1
						i += 1



	return items
