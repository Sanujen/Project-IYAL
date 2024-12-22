from encode2unicode import bamini2unicode

input = """jpUts;Stu; mUspa jpUf;Fws;"""
output = bamini2unicode(input)
f = open("unicode-result.txt", "w", encoding="utf-8")
f.write(output)
f.close()

print("converted unicode stored in 'unicode-result.txt' file")
