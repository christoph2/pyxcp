import argparse

from pyxcp.recorder.converter import convert_xmraw


parser = argparse.ArgumentParser(description="Convert .xmraw files.")

parser.add_argument(
    "target_type",
    help="target file type",
    choices=[
        "arrow",
        "csv",
        "excel",
        "hdf5",
        "mdf",
        "sqlite3",
    ],
)


def main():
    parser.add_argument("xmraw_file", help=".xmraw file")
    parser.add_argument("-t", "--taget-file-name", dest="target_file_name", help="target file name")
    args = parser.parse_args()

    convert_xmraw(args.target_type, args.xmraw_file, args.target_file_name)


if __name__ == "__main__":
    main()
