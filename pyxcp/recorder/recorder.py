
import rekorder as rec

print(dir(rec))
#print(rec.add(47,11))
print("Before c-tor()")
reader = rec.XcpLogFileReader("test_logger")
print("After c-tor()")
res = reader.run()
print(res)
hdr = reader.get_header()
print(hdr)
print("Finished.")
