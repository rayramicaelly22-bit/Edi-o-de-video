import json
import sys

name = sys.argv[1]
lo, hi = float(sys.argv[2]), float(sys.argv[3])
for seg in json.load(open(f"{name}_v2.json", encoding="utf-8")):
    for w in seg["words"]:
        if lo <= w["s"] <= hi:
            print(f"{w['s']:6.2f}-{w['e']:6.2f} {w['w']}")
