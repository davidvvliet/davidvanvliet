# Project Lyra reconstructions

## Project Lyra 2 (`lyra.py`, `public/missions/lyra2.json`)

Produces the spacecraft segment of `public/missions/lyra2.json` from Table 2 of Hibberd, Hein, Eubanks & Kennedy (2022),
"Project Lyra: a mission to 1I/'Oumuamua without solar Oberth manoeuvre" (Acta Astronautica 199; arXiv:2201.04240):
launch 2028 Mar 07, Venus 2028 Jul 06, Earth 2029 Mar 13, deep space manoeuvre at 2.2 au 2030 Feb 12, Earth 2031 Feb 15,
Jupiter 2032 Mar 22, 'Oumuamua 2054 Mar 01.

Method
- Each leg is a Lambert arc (Sun only) between JPL Horizons heliocentric positions of the two bodies on the paper's dates,
  which is how the paper's own tool (OITS) models the transfer.
- The deep space manoeuvre's direction is not published; it is fitted at 2.2 au so that the Earth departure speed,
  the manoeuvre size and the Earth arrival speed match the table (all within 0.02 km/s).
- Check: every arrival and departure hyperbolic excess speed reproduces the table to within 0.12 km/s.
- Inputs: `earth.csv`, `venus.csv`, `jupiter.csv`, `oumuamua.csv` are Horizons VECTORS tables (Sun centre, ecliptic J2000,
  AU and days). 'Oumuamua's own path (JPL#16 solution) is written as a static segment.

## Project Lyra 1a (`lyra1.py`, `public/missions/lyra1a.json`)

Scenario A of Hibberd, Hein & Eubanks (2020), "Project Lyra: catching 1I/'Oumuamua, mission opportunities after 2024"
(Acta Astronautica 170; arXiv:1902.04935), Table 2: launch 2033 May 08 with C3 121 km²/s², unpowered Jupiter flyby
2034 Jul 30, solar Oberth manoeuvre at 6 solar radii, 'Oumuamua 2052 Dec 09, 18.2 km/s in total.
- Earth to Jupiter is a Lambert arc between Horizons positions (Earth departure 10.96 km/s against the paper's 11.0).
- The post-flyby velocity and the size of the tangential perihelion burn are solved by shooting so that the perihelion is
  at 6 solar radii and the craft reaches Horizons' 'Oumuamua position on the arrival date. The solution reproduces the
  paper's unpowered flyby (14.10 km/s in, 14.09 out, a 65° turn at 7.6 Jupiter radii) and a 7.3 km/s burn against 7.2.
  Perihelion falls on 2036 Aug 04; the paper gives no date for it.
The file `lyra2.json` is the 2028 mission described above (the paper's Table 2), renamed.

## Project Lyra 1b (`lyra1b.py`, `public/missions/lyra1b.json`)

Scenario B of the same 2020 paper, E-DSM-E-J-6SR-1I: launch 2030 Jun 09 with C3 50 km²/s², deep space manoeuvre at
3.2 au, Earth flyby, Jupiter 2034 Jul 12, solar Oberth manoeuvre at 6 solar radii, 'Oumuamua 2052 Jul 29; 8.0 km/s up to
and including Jupiter and 7.3 after, 15.3 in total.
- The manoeuvre's date and direction and the Earth flyby date are not published. They are fitted (Nelder–Mead over the
  four numbers, Lambert arcs between) so the launch C3 matches and the manoeuvre plus flyby ΔV is smallest:
  manoeuvre 2031 Nov 29 (0.68 km/s), Earth flyby 2033 Apr 14 at the 200 km floor (0.30 km/s), C3 50.5.
- The Jupiter flyby and solar dive are shot as for 1a; among the converged solutions the smallest burn is taken:
  perihelion 2036 Jun 11, burn 7.36 km/s against the paper's 7.3, Jupiter 0.10 km/s. Total 15.55 against 15.3.
