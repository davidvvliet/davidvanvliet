# Apollo 13/15/16/17 and Mariner 4 trajectory reconstruction

Produces `public/missions/apollo13.json` (`apollo13.py`, burn to burn from mission report MSC-02680 Table 4-II, Moon orientation fitted from the 15-17 archives), `apollo15.json`, `apollo16.json`, `apollo17.json`.

Sources
- Lunar orbit: metric-camera state vectors from the Apollo Image Archive (ASU),
  `AS15_Metric_SV.csv`, `AS16_Metric_SV.csv`, `AS17_Metric_SV.csv`
  (Moon-centred, B1950 equatorial, km, one vector per photograph).
- Translunar injection, lunar orbit insertion, transearth injection, entry interface
  and splashdown: NASA mission reports, Table 3-III (MSC-05161, MSC-07230, JSC-07904).
- Moon/Sun positions: JPL DE432s via astropy.

Method
- The legs between the Moon and Earth are integrated (Earth, Moon and Sun point masses)
  from the tabulated injection state, with the injection velocity adjusted by shooting so
  the leg lands on the tabulated arrival point (adjustments were 7-20 m/s; the real
  midcourse corrections were of that order).
- Gaps between photographs are bridged by propagating the neighbouring vectors and blending.
- The reports' lunar heading angle is measured from Earth's equatorial pole for Apollo 15 and
  from the Moon's pole for 16 and 17 (each checked against the archive vectors).
- Output: one Earth-centred trail (ecliptic J2000, AU); the lunar-orbit part is placed with the site's own lunar theory (`lunar.py`) so it sits on the scene's Moon.

Run: `python -m venv venv && venv/bin/pip install numpy scipy astropy jplephem && venv/bin/python apollo.py`
with the three CSV files in the same directory.

## Mariner 4
`mariner4.py`: injection state (JPL TR 32-740 Table 90, equatorial of date; the printed sign of Zdot is wrong and is taken from the report's own spherical set), trimmed onto the report's pre-midcourse encounter prediction; the 5 Dec 1964 midcourse burn shot onto Table 92 (closest approach time, altitude, B-plane angle; T in the ecliptic, R = S x T). Resulting burn 17.1 m/s against the report's 16.70.
