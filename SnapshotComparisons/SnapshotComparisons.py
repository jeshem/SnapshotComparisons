from GetSnapshots import get_snapshot
from PrintLimitOutput import print_limits

def main():
	limits = []

	snapshot = get_snapshot()
	limits = snapshot.get_data_list()

	print_limits(limits)


if __name__ == "__main__":
	main()