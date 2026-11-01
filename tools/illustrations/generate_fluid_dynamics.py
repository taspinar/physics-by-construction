#!/usr/bin/env python3
"""PBC Fluid Dynamics: 2-D cylinder wake, reproducible scientific illustration.

A D2Q9 lattice-Boltzmann BGK calculation at Reynolds number Re=112.
The cylinder uses on-link no-slip bounceback, y is periodic, x has a
fixed-velocity inlet and approximately zero-gradient outlet. A single
small, localized transverse impulse at t=8500 breaks exact mirror
symmetry; the self-sustained alternating vortex street is visualized
at t=19000. These are a numerical model and plotting choices, not an
experimental measurement or a high-fidelity CFD benchmark.

Use: python generate_fluid_dynamics.py
Requires numpy, scipy, numba, matplotlib, pillow.
Runtime on a CPU can be a few minutes due to 19000 LBM steps.
"""

from pathlib import Path
import numpy as np
import numba as nb
from scipy.ndimage import gaussian_filter
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, Rectangle
from PIL import Image

OUT = Path(__file__).resolve().parent
NX, NY = 480, 170
DIAMETER, U0, REYNOLDS = 22., .086, 112.
XC, YC = 75., NY / 2 + .5
NU = U0 * DIAMETER / REYNOLDS
TAU = 3 * NU + .5
OMEGA = 1 / TAU
CX = np.array([0, 1, 0, -1, 0, 1, -1, -1, 1], dtype=np.int64)
CY = np.array([0, 0, 1, 0, -1, 1, 1, -1, -1], dtype=np.int64)
OPP = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6], dtype=np.int64)
W = np.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36])
Y, X = np.mgrid[:NY, :NX]
SOLID = (X-XC)**2 + (Y-YC)**2 <= (DIAMETER/2)**2
PAPER = "#FAF8F3"

@nb.njit
def equilibrium_init(ny, nx, u, cy, cx, w):
    f = np.empty((9, ny, nx), dtype=np.float64)
    for y in range(ny):
        for x in range(nx):
            uy = .0006 * np.sin(2*np.pi*y/ny*2) * (.5+.5*np.sin(2*np.pi*x/nx))
            us = u*u + uy*uy
            for k in range(9):
                cu = 3*(cx[k]*u+cy[k]*uy)
                f[k,y,x] = w[k]*(1+cu+.5*cu*cu-1.5*us)
    return f

@nb.njit
def lbm_step(f, fn, solid, cx, cy, opp, weights, omega, u0, step):
    ny,nx = solid.shape
    for y in range(ny):
        for x in range(1,nx-1):
            if solid[y,x]:
                continue
            rho=jx=jy=0.
            for k in range(9):
                a=f[k,y,x]
                rho+=a
                jx+=a*cx[k]
                jy+=a*cy[k]
            ux,uy=jx/rho,jy/rho
            us=ux*ux+uy*uy
            for k in range(9):
                cu=3*(cx[k]*ux+cy[k]*uy)
                feq=weights[k]*rho*(1+cu+.5*cu*cu-1.5*us)
                post=f[k,y,x]+omega*(feq-f[k,y,x])
                xd,yd=x+cx[k],y+cy[k]
                if yd<0: yd=ny-1
                if yd>=ny: yd=0
                if solid[yd,xd]:
                    fn[opp[k],y,x]=post
                elif 0<xd<nx-1:
                    fn[k,yd,xd]=post
    for y in range(ny):
        uy=.0018*np.sin(2*np.pi*y/ny)*min(1.,max(0.,(1200-step)/1200.))
        us=u0*u0+uy*uy
        for k in range(9):
            cu=3*(cx[k]*u0+cy[k]*uy)
            fn[k,y,0]=weights[k]*(1+cu+.5*cu*cu-1.5*us)
            fn[k,y,nx-1]=fn[k,y,nx-2]

@nb.njit
def macroscopic(f, solid, cx, cy):
    ny,nx=solid.shape
    ux=np.zeros((ny,nx)); uy=np.zeros_like(ux);rho=np.zeros_like(ux)
    for y in range(ny):
        for x in range(nx):
            if solid[y,x]:
                continue
            r=jx=jy=0.
            for k in range(9):
                a=f[k,y,x]
                r+=a
                jx+=a*cx[k]
                jy+=a*cy[k]
            ux[y,x]=jx/r;uy[y,x]=jy/r;rho[y,x]=r
    return ux,uy,rho

def add_small_wake_impulse(f):
    ux,uy,rho=macroscopic(f,SOLID,CX,CY)
    impulse=.024*np.exp(-((X-112)/15)**2-((Y-(YC+8))/13)**2)
    for k in range(9):
        old_cu=3*(CX[k]*ux+CY[k]*uy)
        new_cu=3*(CX[k]*ux+CY[k]*(uy+impulse))
        old=W[k]*rho*(1+old_cu+.5*old_cu**2-1.5*(ux**2+uy**2))
        new=W[k]*rho*(1+new_cu+.5*new_cu**2-1.5*(ux**2+(uy+impulse)**2))
        f[k,~SOLID]+=(new-old)[~SOLID]

def simulate():
    f=equilibrium_init(NY,NX,U0,CY,CX,W)
    fn=f.copy()
    probe = []
    for t in range(19000):
        if t==8500:
            add_small_wake_impulse(f)
        lbm_step(f,fn,SOLID,CX,CY,OPP,W,OMEGA,U0,t)
        f,fn=fn,f
        if 13200 <= t < 19000 and t % 20 == 0:
            vals=f[:,int(YC),int(XC+45)]
            probe.append((t, (vals*CY).sum()/vals.sum()))
    ux,uy,rho=macroscopic(f,SOLID,CX,CY)
    vorticity=np.gradient(uy,axis=1)-np.gradient(ux,axis=0)
    return ux,uy,rho,vorticity,np.asarray(probe)

def render(ux,uy,vorticity,filename,xlim=(2,451),ylim=(0,170),size=(12,9),dpi=200):
    field=vorticity.copy()
    field[SOLID]=0  # display-only neutral pixels; the cylinder is not fluid
    field=gaussian_filter(field,sigma=1.15)  # smooth only for rasterization
    # Monotone nonlinear contrast enhancement shows weak downstream vortices;
    # colour values are NOT linearly proportional to vorticity.
    tone=np.sign(field)*np.minimum(np.abs(field)/.032,1)**.56
    cm=LinearSegmentedColormap.from_list("pbc",[
        (0.,"#173E73"),(.20,"#397AB1"),(.40,"#B4CCDD"),
        (.50,PAPER),(.60,"#E8C3A8"),(.80,"#DD844B"),(1.,"#A74621")])
    fig=plt.figure(figsize=size,facecolor=PAPER)
    # Atlas panel occupies more of the 4:3 frame than the full wake image.
    panel_mode = (size == (8,6))
    ax=fig.add_axes([0,0,1,1] if panel_mode else [.025,.065,.95,.87],
                    facecolor=PAPER)
    ax.imshow(tone,origin="lower",cmap=cm,vmin=-1,vmax=1,extent=[0,NX,0,NY],
              interpolation="bicubic",zorder=2)
    # Streamlines are integrated from the computed velocity; no hand-drawn swirls.
    clip=Rectangle((0,0),144,NY,facecolor="none",edgecolor="none")
    ax.add_patch(clip)
    masked=SOLID | (np.hypot(ux,uy)<.003)
    vy=np.ma.array(uy,mask=masked)
    vx=np.ma.array(ux,mask=masked)
    seeds=np.linspace(20,150,22)
    streams=ax.streamplot(np.arange(NX),np.arange(NY),vx,vy,color="#2D5A88",
        start_points=np.column_stack([np.full_like(seeds,12.),seeds]),
        integration_direction="forward",linewidth=.5 if panel_mode else .47,arrowsize=0,
        density=2.8,broken_streamlines=False,zorder=4)
    streams.lines.set_alpha(.35 if panel_mode else .37)
    streams.lines.set_clip_path(clip)
    for j in range(36,0,-1):
        fraction=j/36
        gray=int(32+105*(1-fraction))
        ax.add_patch(Circle((XC,YC),DIAMETER/2*fraction,facecolor=(
            gray/255,(gray+8)/255,(gray+21)/255),edgecolor="none",zorder=8))
    ax.add_patch(Circle((XC,YC),DIAMETER/2,facecolor="none",
                        edgecolor="#1C324A",lw=1.2,zorder=9))
    ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_aspect("equal");ax.axis("off")
    fig.savefig(filename,dpi=dpi,facecolor=PAPER)
    plt.close(fig)

def main():
    ux,uy,rho,vort,probe=simulate()
    assert np.isfinite(ux).all() and np.isfinite(uy).all()
    assert .95 < np.min(rho[~SOLID]) and np.max(rho[~SOLID]) < 1.06
    peaks,_=find_peaks(probe[:,1],prominence=.02,distance=25)
    assert len(peaks)>=3, "Unsteady periodic vortex shedding did not develop"
    shedding_period=np.median(np.diff(probe[peaks,0]))
    st=DIAMETER/(U0*shedding_period)
    assert .13 < st < .24, "Implausible Strouhal number; inspect CFD run"
    print(f"Computed shedding Strouhal number: {st:.3f}")
    np.savez_compressed(OUT/"pbc_fluid_dynamics_fields.npz",
        ux=ux.astype("f4"),uy=uy.astype("f4"),rho=rho.astype("f4"),
        vorticity=vort.astype("f4"),solid=SOLID,
        Re=np.array(REYNOLDS),tau=np.array(TAU),u_inlet=np.array(U0),
        diameter=np.array(DIAMETER),xc=np.array(XC),yc=np.array(YC),
        time_step=np.array(19000),transverse_probe=probe.astype("f4"))
    render(ux,uy,vort,OUT/"pbc_fluid_dynamics_vortex_street.png")
    Image.open(OUT/"pbc_fluid_dynamics_vortex_street.png").convert("RGB").save(
        OUT/"pbc_fluid_dynamics_vortex_street.webp",quality=93,method=6)
    render(ux,uy,vort,OUT/"pbc_fluid_dynamics_atlas_panel.png",
           xlim=(35,270),ylim=(0,176),size=(8,6))
    Image.open(OUT/"pbc_fluid_dynamics_atlas_panel.png").convert("RGB").resize(
        (76,57),Image.Resampling.LANCZOS).save(
            OUT/"pbc_fluid_dynamics_atlas_card_76px.png")
    print(f"Re={REYNOLDS:.0f}, tau={TAU:.5f}. Saved figure and data.")

if __name__=="__main__":
    main()
