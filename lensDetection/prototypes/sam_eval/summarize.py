import csv
import sys

rows = list(csv.DictReader(open(sys.argv[1])))
cols = sys.argv[2].split(",") if len(sys.argv) > 2 else ["iou_fill", "bnd_mean_px", "bnd_p95_px", "ring", "snap"]
filt = dict(a.split("=") for a in sys.argv[3:])
rows = [r for r in rows if all(r[k] == v for k, v in filt.items())]
for r in rows:
    print(f"{r['model']:6} {r['photo']} {r['variant']:8} {r['prompt']:14} " + " ".join(f"{c}={r[c]:>6}" for c in cols))
