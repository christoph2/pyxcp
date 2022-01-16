
import rekorder as rec

#print(rec.add(47,11))
print("Before c-tor()")
reader = rec.XcpLogFileReader("test_logger")
print("After c-tor()")
res = reader.run()
print(res)
hdr = reader.get_header()
print(hdr)

while True:
    frames = reader.next()
    if frames is None:
        break
    for category, counter, timestamp, length, payload in frames:
        pass # print(category, counter, timestamp, payload)
print("Finished.")
