import CSVToXLSX

'''
To do list:
	1. create class/functions to find latest csv files
	2. convert the latest csv files into excel files with CSVToXLSX
	3. take information out of the excel file and put them into libraries based on their regions
	4. take information out of the request overview excel file and put them into libraries based on their regions
	5. compare the libraries
	6. output comparisons
	7. ???
	8. profit

Note:
	May be able to skip step 1-3 if I can figure out how to make the api calls directly to OCI
'''

def main():
	location = r"insert directory here"
	original = "insert name of csv file here.csv"
	created = "insert name of xlsx file here.xlsx"

	convert = CSVToXLSX.CSVToXLSX(loc, original, created)
	convert.convert()

if __name__ == "__main__":
	main()