from GetSnapshots import get_snapshot
from PrintLimit import print_limit
from PrintUsage import print_usage

def main():
	#Local directory where the snapshots will be stored 
	limit_location = r"/Users/edwardcheng/Desktop/NSOCI limits"
	usage_location = r"/Users/edwardcheng/Desktop/NSOCI usages"

	#For Windows, use \\. For Mac/Linux, use /
	path_separator = "/"

	snapshot = get_snapshot()
	limits = snapshot.get_limit_data()

	if limits:
		print_limit(limit_location, limits, path_separator)


if __name__ == "__main__":
	main()