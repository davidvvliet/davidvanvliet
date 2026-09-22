# Scenario B of Hibberd, Hein & Eubanks 2020 (arXiv 1902.04935, Table 2): E-DSM-E-J-6SR-1I.
# Given: launch 2030 JUN 09 (C3 50 km2/s2), DSM at 3.2 au, Earth return, Jupiter 2034 JUL 12, solar Oberth at 6 SR,
# 1I 2052 JUL 29; dV 8.0 km/s up to and including Jupiter, 7.3 after. The DSM date/direction and the Earth flyby date
# are not published: fitted so the launch C3 matches and the DSM + Earth-flyby + Jupiter dV is smallest.
import numpy as np, json
from scipy.optimize import least_squares, minimize
from scipy.integrate import solve_ivp
from datetime import datetime, timedelta
exec(open('lyra.py').read().split('# Table 2 schedule')[0])
E,J=load('earth.csv'),load('jupiter.csv')
T0,TJ,T1=jd('2030-06-09'),jd('2034-07-12'),jd('2052-07-29')
rE0,vE0=at(E,T0); rJ,vJ=at(J,TJ); r1,_=at(O,T1)
RP=6*695700/149597870.7
muJ=MU/1047.3486; muE=MU/332946.05; RJ=71492/149597870.7; RE=6378.137/149597870.7
def flyby_dv(vin,vout,mu,rmin):
    # powered flyby at periapsis rmin: dV needed to turn vin (excess) into vout (excess) at that periapsis
    a,b=np.linalg.norm(vin),np.linalg.norm(vout)
    d=np.arccos(np.clip(np.dot(vin,vout)/a/b,-1,1))
    # max turn from unpowered flybys of each speed at rmin
    e1=1+rmin*a*a/mu; e2=1+rmin*b*b/mu; dmax=np.arcsin(1/e1)+np.arcsin(1/e2)
    vp1=np.sqrt(a*a+2*mu/rmin); vp2=np.sqrt(b*b+2*mu/rmin)
    excess=max(0,d-dmax)
    return abs(vp2-vp1)+excess*max(vp1,vp2), np.degrees(d), np.degrees(dmax)
def inner(x):
    td,lon,lat,te=x
    if not (T0+200<td<te-200 and te<TJ-200): return None
    rd=3.2*np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
    rE1,vE1=at(E,te)
    try:
        v0,vd1=lambert(rE0,rd,td-T0); vd2,ve1=lambert(rd,rE1,te-td); ve2,vj1=lambert(rE1,rJ,TJ-te)
    except Exception: return None
    return dict(rd=rd,td=td,te=te,rE1=rE1,vE1=vE1,v0=v0,vd1=vd1,vd2=vd2,ve1=ve1,ve2=ve2,vj1=vj1)
def cost(x):
    L=inner(x)
    if L is None: return 1e3
    c3=(np.linalg.norm(L['v0']-vE0)*AUD)**2
    dsm=np.linalg.norm(L['vd2']-L['vd1'])*AUD
    fe,_,_=flyby_dv(L['ve1']-L['vE1'],L['ve2']-L['vE1'],muE,RE+200/149597870.7)
    return (c3-50)**2/25+dsm+fe*AUD
import os
best=None
if os.path.exists('lyra1b_inner.json'):
    class R: pass
    best=R(); best.x=np.array(json.load(open('lyra1b_inner.json'))); best.fun=cost(best.x)
for td0 in ([] if best is not None else (T0+450,T0+550,T0+650)):
    for lon0 in np.linspace(0,2*np.pi,12,endpoint=False):
        for te0 in (jd('2033-04-01'),jd('2033-07-01'),jd('2033-10-01')):
            r=minimize(cost,[td0,lon0,0.0,te0],method='Nelder-Mead',options={'xatol':1e-6,'fatol':1e-8,'maxiter':3000})
            if best is None or r.fun<best.fun: best=r
json.dump(list(map(float,best.x)),open('lyra1b_inner.json','w'))
L=inner(best.x); td,te=L['td'],L['te']
D=lambda t:(datetime(2000,1,1,12)+timedelta(days=t-2451545.0)).date()
c3=(np.linalg.norm(L['v0']-vE0)*AUD)**2; dsm=np.linalg.norm(L['vd2']-L['vd1'])*AUD
fe,turn,tmax=flyby_dv(L['ve1']-L['vE1'],L['ve2']-L['vE1'],muE,RE+200/149597870.7)
print('launch C3 %.1f (paper 50); DSM %s at %.2f au, %.3f km/s; Earth flyby %s v_inf in %.2f out %.2f, turn %.1f (max %.1f) dV %.3f km/s'%(c3,D(td),np.linalg.norm(L['rd']),dsm,D(te),np.linalg.norm(L['ve1']-L['vE1'])*AUD,np.linalg.norm(L['ve2']-L['vE1'])*AUD,turn,tmax,fe*AUD))
vJin=L['vj1']; print('Jupiter arrival v_inf %.2f km/s'%(np.linalg.norm(vJin-vJ)*AUD))
# Jupiter -> 6 SR -> 1I by shooting (as lyra1.py)
def rhs(t,y): r=y[:3]; return np.concatenate([y[3:],-MU*r/np.linalg.norm(r)**3])
def perihelion(y0):
    ev=lambda t,y: np.dot(y[:3],y[3:]); ev.terminal=True; ev.direction=1
    s=solve_ivp(rhs,(0,3000),y0,events=ev,rtol=1e-11,atol=1e-14,method='DOP853',max_step=20)
    if not s.t_events[0].size: return None
    return s.t_events[0][0], s.y_events[0][0]
def resid(x):
    vout=x[:3]; dv=x[3]; p=perihelion(np.concatenate([rJ,vout]))
    if p is None: return np.array([10,10,10,10.])
    tp,yp=p; rp,vp=yp[:3],yp[3:]; v2=vp+dv*vp/np.linalg.norm(vp)
    s=solve_ivp(rhs,(0,T1-TJ-tp),np.concatenate([rp,v2]),rtol=1e-11,atol=1e-14,method='DOP853')
    return np.concatenate([[(np.linalg.norm(rp)-RP)/RP],(s.y[:3,-1]-r1)/10.0])
hJ=np.cross(rJ,vJ); hn=hJ/np.linalg.norm(hJ); rn=rJ/np.linalg.norm(rJ); tn=np.cross(hn,rn)
bs=None; sols=[]
for vt in (0.3,0.7,1.0,1.5,2.0):
    for vr in (-1.5,-0.7,0.0,0.7,1.5):
        for dv in (5.0,7.0,9.0):
            try: r=least_squares(resid,np.concatenate([(vt*tn+vr*rn)/AUD,[dv/AUD]]),xtol=1e-12,ftol=1e-12,max_nfev=300)
            except Exception: continue
            if r.cost<1e-12:
                pp=perihelion(np.concatenate([rJ,r.x[:3]])); sols.append((r.x[3]*AUD,pp[0] if pp else None,r))
                if bs is None or r.x[3]<bs.x[3]: bs=r
print('converged solutions (burn km/s, days Jupiter->perihelion):',sorted((round(a,2),round(b) if b else None) for a,b,_ in sols))
x=bs.x; vout=x[:3]; tp,yp=perihelion(np.concatenate([rJ,vout])); rp,vp=yp[:3],yp[3:]
fj,turnj,tmaxj=flyby_dv(vJin-vJ,vout-vJ,muJ,RJ*1.05)
print('shoot cost %.2g; Jupiter v_inf in %.2f out %.2f, turn %.1f (max %.1f) dV %.2f; perihelion %.2f SR on %s, burn %.2f km/s (paper 7.3)'%(bs.cost,np.linalg.norm(vJin-vJ)*AUD,np.linalg.norm(vout-vJ)*AUD,turnj,tmaxj,fj*AUD,np.linalg.norm(rp)/(695700/149597870.7),D(TJ+tp),x[3]*AUD))
print('dV to and incl. Jupiter: %.2f (paper 8.0); total %.2f (paper 15.3)'%(np.sqrt(c3)+dsm+fe*AUD+fj*AUD, np.sqrt(c3)+dsm+fe*AUD+fj*AUD+x[3]*AUD))
pts=[]
def add(r0,v0,t0,dur,dts):
    s=solve_ivp(rhs,(0,dur),np.concatenate([r0,v0]),t_eval=dts,rtol=1e-11,atol=1e-14,method='DOP853',**({'max_step':20} if t0==TJ else {}))
    for t,r in zip(dts,s.y[:3].T): pts.append([round(t0+t,3)]+[round(v,5) for v in r])
    return s.y[:3,-1]
add(rE0,L['v0'],T0,td-T0,np.arange(0,td-T0,2)); add(L['rd'],L['vd2'],td,te-td,np.arange(0,te-td,2)); add(L['rE1'],L['ve2'],te,TJ-te,np.arange(0,TJ-te,2))
add(rJ,vout,TJ,tp,np.concatenate([np.arange(0,tp-5,1.0),np.arange(tp-5,tp,0.05)]))
v2=vp+x[3]*vp/np.linalg.norm(vp); dur=T1-TJ-tp
end=add(rp,v2,TJ+tp,dur,np.concatenate([np.arange(0,5,0.05),np.arange(5,200,1.0),np.arange(200,dur,30)]))
pts.append([round(T1,3)]+[round(v,5) for v in r1]); print('end error %.3f au, %d points'%(np.linalg.norm(end-r1),len(pts)))
json.dump({'td':td,'te':te,'tp':TJ+tp,'pts':pts},open('lyra1b_points_tdb.json','w'))
