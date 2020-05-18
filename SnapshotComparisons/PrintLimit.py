from openpyxl import Workbook
import openpyxl
from datetime import datetime
from datetime import date
import os
import time

class limit_output_and_compare(object):
    date = datetime.now()
    today = date.strftime("%Y-%m-%d, %H-%M-%S")

    FRA_limits = []
    PHX_limits = []
    IAD_limits = []

    all_limits=[]

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
        'available'
        ]

    
    def __init__(self, location, limits):
        self.loc = location
        self.all_limits = limits
        pass

    def print_limits(self):
        wb = Workbook()
        current_region = ''
        test_ws = wb.active

        for limit in self.all_limits:

            #if a service is in a different region, create a new worksheet for that region
            if limit['region_name'] != current_region:
                print("changing regions!")
                current_region = limit['region_name']
                current_ws = wb.create_sheet(limit['region_name'])
                #reset where the list of services should begin in each worksheet
                row = 2


            #use keys to create column titles
            for key in range(len(self.keys)):
                current_ws.cell(1, key+1).value = self.keys[key]

            #if a row is already populated, go down one row
            if current_ws.cell(row, 1).value != None:
                row+=1

            #enter limit data into the row
            for col in range(len(self.keys)):
                key = self.keys[col]
                current_ws.cell(row,col+1).value = limit[key]

        sheet_to_remove = wb.get_sheet_by_name('Sheet')
        wb.remove_sheet(sheet_to_remove)
        wb.save(self.loc + "\\" + self.title + self.today + ".xlsx")

    #find new files and insert them into a list
    def find_new_files(self, loc):
        dirs = os.listdir(self.loc)
        found_a_file = False

        last_date = self.date


        for file in dirs:
            #if the file is a directory, go into it and check for more files
            if os.path.isdir(self.loc + "\\" + file):
                        list = self.find_new_files(loc + "\\" + file)

            #get the date the limits file was modified/created
            file_create_date = datetime.fromtimestamp(os.path.getctime(loc + "\\" + file))

            #if last_date is still today, set last date to the file's creation date
            if last_date == self.date:
                last_date = file_create_date
            #find the latest limits
            elif file_create_date < self.date and file_create_date > last_date:
                last_date = file_create_date
                self.latest_file = file

        if self.latest_file == '':
            print("No previous record of limits found")
        else:
            print(self.latest_file)
            self.compare_limits()

    def temp_name(self):
        last_wb = openpyxl.load_workbook(self.loc + "\\" + self.latest_file)
        current_region = ''

        for limit in self.all_limits:
            if limit['region_name'] != current_region:
                current_region = limit['region_name']
                current_ws = last_wb[current_region]

        pass

    #get the limits from the latest limits excel file and compare them to the current limits
    def compare_limits(self):
        last_wb = openpyxl.load_workbook(self.loc + "\\" + self.latest_file)
        last_FRA_ws = last_wb['FRA']
        last_PHX_ws = last_wb['PHX']
        last_IAD_ws = last_wb['IAD']

        last_FRA_limits = []
        last_PHX_limits = []
        last_IAD_limits = []

        FRA_dif = []
        PHX_dif = []
        IAD_dif = []

        #retrieve the limits from each region in the last limits file
        for row in range(last_FRA_ws.max_row-2):
            cell_value = last_FRA_ws.cell(row+2, 6).value
            last_FRA_limits.append(cell_value)
        for row in range(last_PHX_ws.max_row-2):
            cell_value = last_PHX_ws.cell(row+2, 6).value
            last_PHX_limits.append(cell_value)
        for row in range(last_IAD_ws.max_row-2):
            cell_value = last_IAD_ws.cell(row+2, 6).value
            last_IAD_limits.append(cell_value)

        #compare limits from last time it was retrieved to the current limits
        if len(last_FRA_limits)>1:
            for thing in range(len(last_FRA_limits)):
                difference = self.FRA_limits[thing]['value'] - last_FRA_limits[thing]
                val = {'region_name': self.FRA_limits[thing]['region_name'],
                       'availability_domain': self.FRA_limits[thing]['availability_domain'],
                       'name': self.FRA_limits[thing]['limit_name'],
                       'difference': difference}
                FRA_dif.append(val)
        if len(last_PHX_limits)>1:
            for thing in range(len(last_PHX_limits)):
                difference = self.PHX_limits[thing]['value'] - last_PHX_limits[thing]
                val = {'region_name': self.PHX_limits[thing]['region_name'],
                       'availability_domain': self.PHX_limits[thing]['availability_domain'],
                       'name': self.PHX_limits[thing]['limit_name'],
                       'difference': difference}
                PHX_dif.append(val)
        if len(last_IAD_limits)>1:
            for thing in range(len(last_PHX_limits)):
                difference = int(self.IAD_limits[thing]['value']) - int(last_IAD_limits[thing])
                val = {'region_name': self.IAD_limits[thing]['region_name'],
                       'availability_domain': self.IAD_limits[thing]['availability_domain'],
                       'name': self.IAD_limits[thing]['limit_name'],
                       'difference': difference}

        
        for thing in FRA_dif:
            if thing['difference'] != 0:
                print(str(thing))       
        for thing in PHX_dif:
            if thing['difference'] != 0:
                print(str(thing))
        for thing in IAD_dif:
            if thing['difference'] != 0:
                print(str(thing))


        pass

