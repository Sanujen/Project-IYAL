import csv
from unicode2encode import unicode2bamini

input = """திருவள்ளுவர் அருளிய திருக்குறள்"""
output = unicode2bamini(input)

with open("legacy.csv", "w", newline="", encoding="utf-8") as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["Initial Unicode", "Converted Text"])
    csvwriter.writerow([input, output])

print("End of process")
