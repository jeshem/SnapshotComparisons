from GetSnapshots import get_snapshot
from PrintLimit import limit_output_and_compare

def main():
	limits = []
	
	location = r"C:\Users\shemchen\Desktop\OCI API Calls"

	snapshot = get_snapshot()
	limits = snapshot.get_limit_data()

	snapshot.get_compartment_data()

	compare = limit_output_and_compare(location, limits)
	compare.print_limits()
	compare.find_new_files(location)

	wait = input("PRESS ENTER TO CONTINUE.")


if __name__ == "__main__":
	main()