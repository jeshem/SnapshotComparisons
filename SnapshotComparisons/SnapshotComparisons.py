from GetSnapshots import get_snapshot
from PrintLimit import limit_output_and_compare

'''
we have usage on a regional level
WE NEED IT ON A COMPARTMENT LEVEL
Get quota on AD level
'''

def main():
	limits = []
	
	location = r"C:\Users\shemchen\Desktop\OCI API Calls"

	snapshot = get_snapshot()
	limits = snapshot.get_limit_data()

	compare = limit_output_and_compare(location, limits)
	compare.print_limits()
	compare.find_new_files(location)

	wait = input("PRESS ENTER TO CONTINUE.")


if __name__ == "__main__":
	main()