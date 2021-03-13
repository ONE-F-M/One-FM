import frappe,calendar
import itertools
from dateutil.relativedelta import relativedelta
from datetime import date,timedelta,datetime
from calendar import monthrange
from frappe.utils import nowdate,getdate,cstr
from one_fm.one_fm.timesheet_custom import timesheet_automation,calculate_hourly_rate_of_monthly_working_days,days_of_month
#from frappe import _

def create_sales_invoice():
    today = date.today()
    day = today.day
    d = today
    month_and_year = today.strftime("%B - %Y")   
    #Get the first day of the month
    first_day = date(today.year,today.month,1)
    #Get the last day of the month
    last_day = first_day.replace(day = monthrange(first_day.year,first_day.month)[1])
    contacts_list = get_contracts_list(day,today,today)
    for contracts in contacts_list:
        sales_invoice = ''
        if contracts.invoice_frequency == 'Monthly':
            from_date = first_day
            to_date = today - timedelta(days = 1)
            #run timesheet automation for the project
            timesheet_automation(from_date,to_date,contracts.project)
            create_monthly_sales_invoice(sales_invoice,contracts,today,first_day,last_day,from_date,month_and_year)
        if contracts.invoice_frequency == 'Quarterly':
            time_difference = relativedelta(d,contracts.start_date)
            full_months = time_difference.years * 12 + time_difference.months + 1
            if full_months%3 == 0:
                from_date = first_day
                to_date = today - timedelta(days = 1)
                #run timesheet automation for the project
                timesheet_automation(from_date,to_date,contracts.project)
                create_quarterly_sales_invoice(sales_invoice,item,today,first_day,last_day,from_date,month_and_year)
            else:
                from_date = today - relativedelta(months = 1)
                to_date = today - timedelta(days = 1)
                #run timesheet automation for the project
                timesheet_automation(from_date,to_date,contracts.project)
    return

#Create monthly sales invoice
def create_monthly_sales_invoice(sales_invoice,contracts,today,first_day,last_day,from_date,month_and_year):
    sales_invoice = frappe.new_doc('Sales Invoice')
    sales_invoice.contracts = contracts.name
    sales_invoice.customer = contracts.client
    sales_invoice.set_posting_time = 1
    sales_invoice.project = contracts.project
    sales_invoice.selling_price_list = contracts.price_list
    sales_invoice.timesheets = ''
    project_details = frappe.get_doc('Project',contracts.project)
    cost_center = project_details.cost_center
    income_account = project_details.income_account
    #select contracts items and gets details from timesheet and add into the sales invoice item table
    contract_item_list = get_contract_item_list(contracts.name)
    if contract_item_list:
        if contracts.is_invoice_for_site:
            for contract_item in contract_item_list:
                sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                timesheet_billing_amt = 0
                if sitewise_timesheet_details:
                    for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                        #Add site wise detail
                        sales_invoice = add_site_wise_contracts_item_details_into_invoice(sales_invoice,group,contract_item,today,last_day,key,first_day,income_account,cost_center,month_and_year)
        else:
            for contract_item in contract_item_list:
                #add reference to the attendance
                timesheet_details = get_projectwise_timesheet_data(item.project,contract_item.item_code,from_date,today)
                sales_invoice = add_contracts_item_details_into_invoice(sales_invoice,timesheet_details,contract_item,today,last_day,first_day,income_account,cost_center,month_and_year)
    if contracts.frequency == 'Monthly':
        contract_asset_list = get_asset_items_from_contracts(contracts.name)                
        for asset in contract_asset_list:
            sales_invoice.append('items',{
                    'item_code': asset.item_code,
                    'qty': asset.qty,
                    'uom': asset.uom,
                    'income_account': income_account,
                    'cost_center': cost_center
            })
            
    else:
        delivery_note_start_date = today - relativedelta(months = 1)
        delivery_not_end_date = today - timedelta(days = 1)
        contract_asset_list = get_asset_items_from_delivery_note(contracts.project,contracts.client,delivery_note_start_date,delivery_not_end_date)
        sales_invoice = append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center)
    #insert into sales invoice
    add_into_sales_invoice(sales_invoice)

#Create quarterly sales invoice
def create_quarterly_sales_invoice(sales_invoice,contracts,today,first_day,last_day,from_date,month_and_year):
    sales_invoice = frappe.new_doc('Sales Invoice')
    sales_invoice.contracts = contracts.name
    sales_invoice.customer = contracts.client
    sales_invoice.set_posting_time = 1
    sales_invoice.project = contracts.project
    sales_invoice.selling_price_list = contracts.price_list
    sales_invoice.timesheets = ''
    project_details = frappe.get_doc('Project',contracts.project)
    cost_center = project_details.cost_center
    income_account = project_details.income_account
    contract_item_list = get_contract_item_list(contracts.name)
    if contract_item_list:
        if contracts.is_invoice_for_site:
            for contract_item in contract_item_list:
                from_date = (today - relativedelta(months = 2))
                from_date = date(from_date.year,from_date.month,1)
                to_date = today - timedelta(days = 1)
                sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                #adding timsheet details
                timesheet_billing_amt = 0
                if sitewise_timesheet_details:
                    for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                        #Add site wise detail
                        sales_invoice = add_site_wise_contracts_item_details_into_invoice(sales_invoice,group,contract_item,today,last_day,key,first_day,income_account,cost_center,month_and_year)
        else:
            for contract_item in contract_item_list:
                from_date = (today - relativedelta(months = 2))
                from_date = date(from_date.year,from_date.month,1)
                to_date = today - timedelta(days = 1)
                timesheet_details = get_projectwise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                sales_invoice = add_contracts_item_details_into_invoice(sales_invoice,timesheet_details,contract_item,today,last_day,first_day,income_account,cost_center,month_and_year)
    if contracts.frequency == 'Monthly':
        contract_asset_list = get_asset_items_from_contracts(contracts.name)
        
        for asset in contract_asset_list:
            sales_invoice.append('items',{
                    'item_code': asset.item_code,
                    'qty': asset.qty * 3,
                    'uom': asset.uom,
                    'income_account': income_account,
                    'cost_center': cost_center
            })
            
    else:
        delivery_note_start_date = (today - relativedelta(months = 3))
        delivery_not_end_date = today - timedelta(days = 1)
        contract_asset_list = get_asset_items_from_delivery_note(contracts.project,contracts.client,delivery_note_start_date,delivery_not_end_date)
        sales_invoice = append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center)
    #insert into sales invoice
    add_into_sales_invoice(sales_invoice)

#add into sales invoice
def add_into_sales_invoice(sales_invoice):
    try:
        sales_invoice.flags.ignore_permissions  = True
        sales_invoice.update({
            'customer': sales_invoice.customer,
            'set_posting_time': sales_invoice.set_posting_time,
            'project': sales_invoice.project,
            'contracts': sales_invoice.contracts,
            'selling_price_list': sales_invoice.selling_price_list,
            'items': sales_invoice.items,
            'timesheets': sales_invoice.timesheets,
        }).insert()
        create_todo(sales_invoice.name)
    except Exception as e:
        print(e)

#Get contracts list
def get_contracts_list(due_date,start_date,end_date):
    return frappe.db.sql("""select name,client,project,price_list,invoice_frequency,due_date,frequency,start_date,is_invoice_for_site 
            from tabContracts where due_date = %s and 
            start_date <= %s and end_date >= %s""",(due_date,start_date,end_date),as_dict = 1)

#Get contrcats item list
def get_contract_item_list(parent):
    return frappe.db.sql("""select ci.name,ci.item_code,ci.head_count as qty,ci.shift_hours,ci.unit_rate,
                        ci.type,ci.monthly_rate
                        from `tabContract Item` ci, `tabContracts` c
                        where c.name = ci.parent and ci.parenttype = 'Contracts'
                        and ci.parent = %s order by ci.idx asc""",(parent), as_dict=1)

#Get asset items from contracts
def get_asset_items_from_contracts(parent):
    return frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom,ca.unit_rate as rate
            from `tabContract Asset` ca, `tabContracts` c
            where c.name = ca.parent and ca.parenttype = 'Contracts'
            and ca.parent = %s order by ca.idx asc""",(parent), as_dict=1)

#Get asset items from delivery note
def get_asset_items_from_delivery_note(project,client,start_date,end_date):
    return frappe.db.sql("""select di.parent as delivery_note,di.name as dn_detail,di.against_sales_order,di.so_detail,
            di.item_code,di.qty,di.uom,di.rate
            from `tabDelivery Note Item` di, `tabDelivery Note` d
            where d.name = di.parent and di.parenttype = 'Delivery Note'
            and d.docstatus = 1 and status not in ("Stopped", "Closed")
            and d.project = %s and d.customer = %s and d.is_return = 0 and d.per_billed < 100
            and posting_date between %s and %s order by di.idx asc""",(project,client,start_date,end_date), as_dict=1)

#Add site wise details into invoice
def add_site_wise_contracts_item_details_into_invoice(sales_invoice,site_group,contract_item,start_date,end_date,key,first_day,income_account,cost_center,month_and_year):
    timesheet_billing_amt = site_amount = extra_amount = no_of_days_remaining = hourly_rate= 0
    sitewise_timesheet = list(site_group)
    description = frappe.db.get_value("Item",contract_item.item_code,'description')
    for st in sitewise_timesheet:
        #add site wise timesheet and item in sales invoice details
        sales_invoice.append('timesheets',{
                'time_sheet': st.parent,
                'billing_hours': st.billing_hours,
                'billing_amount': st.billing_amt,
                'timesheet_detail': st.name,
                'item': contract_item.item_code
        })
        site_amount += st.billing_amt
    timesheet_billing_amt += site_amount
    #Adding rate for service from current date to end date by taking values from contracts and add into amount
    date_list = get_timesheet_remaining_days(start_date,start_date)
    #find qty of item in a site
    item_qty = get_operations_post_in_site(key,sales_invoice.project,contract_item.item_code)
    if contract_item.type == 'Monthly':
        #calculate hourly rate
        hourly_rate = calculate_hourly_rate_of_monthly_working_days(sales_invoice.project,contract_item.item_code,contract_item.monthly_rate,contract_item.shift_hours,first_day)
    else:
        hourly_rate = contract_item.unit_rate
    
    for d in range(len(date_list)):
        day_of_week = calendar.day_name[date_list[d].weekday()]
        day_of_week = day_of_week.lower()
        is_day_off = frappe.db.get_value('Contract Item', {'name':contract_item.name ,'parent':sales_invoice.contracts}, day_of_week)
        if is_day_off == 0:
            no_of_days_remaining +=1
            extra_amount += (hourly_rate * contract_item.shift_hours)
    extra_amount = item_qty * extra_amount
    site_amount += extra_amount
    #adding description if any extra amount(amount for remaining days of month) for service item
    if extra_amount > 0:
        description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
    sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
    sales_invoice.append('items',{
        'item_code': contract_item.item_code,
        'description': description,
        'site': key,
        'qty': item_qty,
        'rate': site_amount/item_qty,
        'income_account': income_account,
        'cost_center': cost_center
    })

    return sales_invoice

#Add details into invoice
def add_contracts_item_details_into_invoice(sales_invoice,timesheet_details,contract_item,start_date,end_date,first_day,income_account,cost_center,month_and_year):
    description = frappe.db.get_value("Item",contract_item.item_code,'description')
    item_amount = timesheet_billing_amt = extra_amount = no_of_days_remaining = hourly_rate = 0
    if timesheet_details:
        for t in timesheet_details:
            item_amount += t.billing_amt
            sales_invoice.append('timesheets',{
                    'time_sheet': t.parent,
                    'billing_hours': t.billing_hours,
                    'billing_amount': t.billing_amt,
                    'timesheet_detail': t.name,
                    'item': contract_item.item_code
            })
        timesheet_billing_amt = item_amount
        #Adding rate for service from current date to end date by taking values from contracts and add into amount
        date_list = get_timesheet_remaining_days(start_date,end_date)
        if contract_item.type == 'Monthly':
            #calculate hourly rate
            hourly_rate = calculate_hourly_rate_of_monthly_working_days(sales_invoice.project,contract_item.item_code,contract_item.monthly_rate,contract_item.shift_hours,first_day)
        else:
            hourly_rate = contract_item.unit_rate
        for d in range(len(date_list)):
            day_of_week = calendar.day_name[date_list[d].weekday()]
            day_of_week = day_of_week.lower()
            is_day_off = frappe.db.get_value('Contract Item', {'name':contract_item.name ,'parent':sales_invoice.contracts}, day_of_week)
            if is_day_off == 0:
                no_of_days_remaining +=1
                extra_amount += (hourly_rate * contract_item.shift_hours)
        extra_amount = contract_item.qty * extra_amount
        item_amount += extra_amount
        #adding description if any extra amount(amount for remaining days of month) for service item
        if extra_amount > 0:
            description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
    sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
    sales_invoice.append('items',{
            'item_code': contract_item.item_code,
            'description': description,
            'qty': contract_item.qty,
            'rate': item_amount/contract_item.qty,
            'income_account': income_account,
            'cost_center': cost_center
    })

    return sales_invoice

#Append delivery note items into invoice
def append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center):
    for asset in contract_asset_list:
        sales_invoice.append('items',{
                'item_code': asset.item_code,
                'qty': asset.qty,
                'uom': asset.uom,
                'rate': asset.rate,
                'sales_order': asset.sales_order,
                'so_detail': asset.so_detail,
                'delivery_note': asset.delivery_note,
                'dn_detail': asset.dn_detail,
                'income_account': income_account,
                'cost_center': cost_center
        })
    return sales_invoice

    

@frappe.whitelist()
def get_projectwise_timesheet_data(project,item_code,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
        posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
        start_date = date(posting_date.year,posting_date.month,1)
        end_date = posting_date
    #end date should be current date
    return frappe.db.sql("""select t.name, t.parent,t.from_time,t.billing_hours, t.billing_amount as billing_amt
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)

# get site wise timesheet details
@frappe.whitelist()
def get_sitewise_timesheet_data(project,item_code,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
        posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
        start_date = date(posting_date.year,posting_date.month,1)
        end_date = posting_date
    #end date should be current date
    return frappe.db.sql("""select t.name,t.parent,t.site,t.from_time,t.billing_hours, t.billing_amount as billing_amt
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.site,t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)

#Get remaining amounts of services from contracts for remaining dates.
def get_timesheet_remaining_days(start_date, end_date):
    date_list = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        date_list.append(day)
    return date_list

#get operations post in site
def get_operations_post_in_site(site,project,item):
    return frappe.db.sql("""select count(post_name) from `tabOperations Post`
            where site = %s and project = %s and 
            post_template in (select post_name from `tabPost Type` where sale_item = %s)""",(site,project,item),as_dict=0)[0][0]

#refer support module ticketing system
def create_todo(name):
    if name:
        todo = frappe.new_doc('ToDo')
        todo.flags.ignore_permissions  = True
        todo.status = 'Open'
        todo.priority = 'Medium'
        todo.owner = 'saoud@one-fm.com'
        todo.description = name + ' has been created. '
        todo.reference_type = 'Sales Invoice'
        todo.reference_name = name
        todo.update({
                    'status': todo.status,
                    'priority': todo.priority,
                    'owner': todo.owner,
                    'description': todo.description,
                    'reference_type': todo.reference_type,
                    'reference_name': todo.reference_name
                }).insert()

def before_submit_sales_invoice(doc, method):
    if doc.contracts:
        is_po_for_invoice = frappe.db.get_value('Contracts', doc.contracts, 'is_po_for_invoice')
        if is_po_for_invoice == 1 and not doc.po:
            frappe.throw('Please Attach Customer Purchase Order')
