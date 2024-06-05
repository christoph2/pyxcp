import argparse
import sys
from pprint import pprint

from pyxcp.recorder import XcpLogFileReader, XcpLogFileUnfolder
from pyxcp.utils import hexDump


parser = argparse.ArgumentParser(description="Dump .xmraw files.")
parser.add_argument("xmraw_file", help=".xmraw file")
# parser.add_argument("-l", help = "loglevel [warn | info | error | debug]", dest = "loglevel", type = str, default = "warn")
args = parser.parse_args()

print(args.xmraw_file)


class Unfolder(XcpLogFileUnfolder):

    def on_daq_list(self, daq_list_num, timestamp0, timestamp1, measurement):
        print(daq_list_num, timestamp0, timestamp1, measurement)


lfr = Unfolder(args.xmraw_file)
print("-" * 80)
print(lfr.get_header())
print("-" * 80)
lfr.run()
# print(lfr.parameters)
print("=" * 80)
print("=" * 80)
print("=" * 80)
print(lfr.daq_lists)
sys.exit()

reader = XcpLogFileReader(args.xmraw_file)
hdr = reader.get_header()  # Get file information.
print("\nRecording file header")
print("=====================\n")
pprint(hdr)

print("\nRecorded frames")
print("===============\n")
print("CAT         CTR  TS                  PAYLOAD")
print("-" * 80)
for category, counter, timestamp, payload in reader:
    print(f"{category.name:8} {counter:6}  {timestamp:7.7f} {hexDump(payload)}")
    # pass
print("-" * 80)
reader.reset_iter()  # reader acts as an Python iterator -- can be reseted with this non-standard method.
