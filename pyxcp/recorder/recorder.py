
import rekorder as rec

print(dir(rec))
#print(rec.add(47,11))
reader = rec.XcpLogFileReader("test_logger")
print(reader.run())
hdr = reader.get_header()
print(hdr)
