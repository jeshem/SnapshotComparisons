from openpyxl import Workbook
from datetime import datetime
import os

class limit_output_and_compare(object):
    date = datetime.date(datetime.now())

    FRA_limits = []
    PHX_limits = []
    IAD_limits = []

    title = 'NS-OCI Limits '
    latest_file = ''

    keys = [
	    'name',
        'description',
        'limit_name',
        'availability_domain',
        'scope_type',
        'value',
        'used',
        'available',
        'region_name'
    ]

    
    def __init__(self, location, limits):
        self.loc = location

        for things in limits:
            if things['region_name'] == 'eu-frankfurt-1':
                self.FRA_limits.append(things)
            elif things['region_name'] == 'us-phoenix-1':
                self.PHX_limits.append(things)
            elif things['region_name'] == 'us-ashburn-1':
               self.IAD_limits.append(things)

        pass

    def print_limits(self):
        wb = Workbook()
        FRA_ws = wb.active
        FRA_ws.title = 'FRA'
        PHX_ws = wb.create_sheet('PHX')
        IAD_ws = wb.create_sheet('IAD')
        
        for row in range(len(FRA_limits)):
            thing = self.FRA_limits[row]
            for col in range(len(keys)):
                self.key = keys[col]
                FRA_ws.cell(row, col).value = thing[key]

        for row in range(len(PHX_limits)):
            thing = self.PHX_limits[row]
            for col in range(len(keys)):
                self.key = keys[col]
                PHX_ws.cell(row, col).value = thing[key]

        for row in range(len(IAD_limits)):
            thing = self.IAD_limits[row]
            for col in range(len(keys)):
                self.key = keys[col]
                IAD_ws.cell(row, col).value = thing[key]

        wb.save(self.title + self.date + ".xlsx")

    #find new files and insert them into a list
    def find_new_files(self):
        dirs = os.listdir(self.loc)

        last_date = self.date

        for file in dirs:
            #if the file is a directory, go into it and check for more files
            if os.path.isdir(loc + "\\" + file):
                        list = self.find_new_files(loc + "\\" + file, list)

            #get the date the limits file was modified/created
            file_create_date = os.stat(self.loc + "\\" + file).st_ctime
            
            #find the latest limits
            if file_create_date > last_date:
                last_date = file_create_date
                self.latest_file = file

    def compare_limits(self):

        pass

