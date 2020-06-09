from GetSnapshots import get_snapshot
from PrintLimit import limit_output_and_compare

def main():
	limits = []
	
	#Local directory where the snapshots will be stored
	limit_location = r"C:\Users\shemchen\Desktop\NSOCI Limit"
	usage_location = r"C:\Users\shemchen\Desktop\NSOCI Usage"

	snapshot = get_snapshot()
	limits = snapshot.get_limit_data()

	if limits:
		compare = limit_output_and_compare(location, limits)
		compare.save_limits()
		compare.find_latest_file(location)


if __name__ == "__main__":
	main()