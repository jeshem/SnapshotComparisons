from openpyxl import Workbook

def print_limits(data):
    wb = Workbook()
    FRA_ws = wb.create_sheet('FRA')
    PHX_ws = wb.create_sheet('PHX')
    IAD_ws = wb.create_sheet('IAD')

    FRA_limits = []
    PHX_limits = []
    IAD_limits = []

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

    print(wb.sheetnames)


    for things in data:
        if things['region_name'] == 'eu-frankfurt-1':
            FRA_limits.append(things)
        elif things['region_name'] == 'us-phoenix-1':
            PHX_limits.append(things)
        elif things['region_name'] == 'us-ashburn-1':
           IAD_limits.append(things)

    for row in range(len(FRA_limits)):
        thing = FRA_limits[row]
        for col in range(len(keys)):
            key = keys[col]
            FRA_limits.cell(row, col).value = thing[key]


