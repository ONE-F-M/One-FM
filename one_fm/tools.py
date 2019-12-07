# -*- coding:utf-8 -*-
# encoding: utf-8

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe, os
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file
from frappe.utils.password import update_password as _update_password
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate



def get_website_info_data():

    # about_us_info = frappe.client.get_list("Website Info", fields=['section_title','section_header','section_subject'])
    about_us_info = frappe.db.get_single_value("Website Info", "section_subject")
    print(about_us_info)


