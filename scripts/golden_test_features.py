import sys
import numpy as np
sys.path.insert(0, "backend")

from app.db import db
from app import features as F

con = db()
teams = F.build_team_frame(con)
matches = F.build_match_frame(con)
print(f"{len(matches)} matches, {len(F.FEATURE_COLS)} features")

sample = matches
worst, bad = {}, 0
for _, r in sample.iterrows():
    X, ctx = F.build_features(
        con, r["home_team"], r["away_team"],
        as_of=r["date"], league=r["league"], year=int(r["year"]), teams=teams,
    )
    got = X.iloc[0].to_numpy(dtype=float)
    exp = r[F.FEATURE_COLS].to_numpy(dtype=float)
    ok = np.isclose(got, exp, atol=1e-9, equal_nan=True)
    if not ok.all():
        bad += 1
        for c in np.array(F.FEATURE_COLS)[~ok]:
            worst[str(c)] = worst.get(str(c), 0) + 1
print(f"replay parity: {bad}/{len(sample)} rows differ")
if worst:
    print("columns that differ:", dict(sorted(worst.items(), key=lambda kv: -kv[1])))