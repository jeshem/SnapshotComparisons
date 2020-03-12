from GetSnapshots import get_snapshot
from PrintLimitOutput import limit_output_and_compare

def main():
	limits = []
	
	location = "path"

	snapshot = get_snapshot()
	limits = snapshot.get_data_list()

	compare = limit_output_and_compare(location, limits)
	compare.print_limits()


if __name__ == "__main__":
	main()