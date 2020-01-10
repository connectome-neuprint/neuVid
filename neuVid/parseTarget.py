import sys

if len(sys.argv) < 2:
    print("Usage: python {} '<neuPrint URL>'".format(sys.argv[0]))
    exit()

url = sys.argv[1]

i1 = url.find("coordinates")
i2 = url.find("=", i1)
i3 = url.find("&", i2)
c1 = url[i2:i3]
c2 = c1.split("%2C")

print("[{}, {}, {}]".format(round(float(c2[3])), round(float(c2[4])), round(float(c2[5]))))
