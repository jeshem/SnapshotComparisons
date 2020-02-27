import csv
import openpyxl
from openpyxl import Workbook

class CSVToXLSX(object):
    
    
    def __init__(self, loc, csv_file, xlsx_file):
        self.location = loc
        self.csv_file = csv_file
        self.xlsx_file = xlsx_file

    def convert(self):
        csv_file = open(self.loc + self.csv_file)
        csv.register_dialect('commas', delimiter=',')
        reader = csv.reader(csv_file, dialect='commas')

        wb = Workbook()
        dest_filename = self.loc + self.xlsx_file

        ws = wb.worksheets[0]

        for row_index, row in enumerate(reader):
            for column_index, cell in enumerate(row):
                ws.cell((row_index + 1), (column_index + 1)).value = cell

        wb.save(filename = dest_filename)


    pass




