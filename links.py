from misc import book_name_mapping as books

base = "http://ibibles.net/quote.php?niv-"
raw = input('Enter Verses Seperated by Commas: ')

raw = [x.strip() for x in raw.split(",")]
res = "" if len(raw) == 1 else "~"
for i in raw:
    book_name, ref = ' '.join(i.split()[:-1]), i.split()[-1]
    book_key = books[book_name] if book_name != "Psalm" else "psa"
    add = base+book_key+"/"+ref + ","
    res += add
print(res[:-1])
