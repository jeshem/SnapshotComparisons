from GetSnapshots import get_snapshot
from PrintLimit import print_limit
from PrintUsage import print_usage

def main():
	#Local directory where the snapshots will be stored
	limit_location = r"C:\Users\shemchen\Desktop\NSOCI Limit"
	usage_location = r"C:\Users\shemchen\Desktop\NSOCI Usage"

	snapshot = get_snapshot()
	limits = snapshot.get_limit_data()
	usages = snapshot.get_usage_data()

	if limits:
		print_limit(limit_location, limits)

	if usages:
		print_usage(usage_location, usages)


if __name__ == "__main__":
	main()