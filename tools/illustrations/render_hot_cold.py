#!/usr/bin/env python3
"""Reproducible PBC illustration: hot-to-cold particle box.

Numerical physics:
    Heat diffusion PDE dT/dt = D d²T/dx² on x in [0,1], with isothermal walls.
    Solve using backward Euler and tridiagonal banded linear solves until near steady state.
    Spatial temperature determines locally Maxwellian THREE-DIMENSIONAL ideal-gas
    velocity samples: (vx,vy,vz) ~ Normal(0, k_B T/m).

Important scope: the temperature field comes from the Fourier continuum model.
Particles are statistical *local-equilibrium illustrations*, not a particle-
collisional heat-transport / molecular-dynamics simulation. Trails are short
instantaneous velocity indicators, not integrated trajectories.

Outputs: 2400x1800 PNG, WebP, hybrid SVG, panel and thumbnails, diagnostic,
validation.json, sampling_data.npz. All randomness fixed by SEED.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, PathPatch
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.path import Path as MplPath
import numpy as np
from PIL import Image, ImageOps
from scipy.linalg import solve_banded
from scipy.integrate import quad
from scipy.stats import maxwell

OUT = Path(__file__).resolve().parent
SEED=20261030
HOT=3.4
COLD=0.72
DIFFUSIVITY=0.12
CONDUCTIVITY=1.6
K_B=1.0
MASS=1.0
NX=321
DT=0.04
STEPS=320
N_PARTICLES=550
BG='#FAF8F3'
INK='#254667'
COPPER='#D36B3C'
BLUE='#2C6CA8'
MIDDLE='#DAA06F'


def temperature_solution():
    """Implicit Euler heat equation with fixed hot/cold reservoirs."""
    x=np.linspace(0,1,NX)
    dx=x[1]-x[0]
    r=DIFFUSIVITY*DT/(dx*dx)
    u=np.full(NX,0.5*(HOT+COLD))
    u[0],u[-1]=HOT,COLD
    band=np.zeros((3,NX-2))
    band[0,1:]=-r
    band[1,:]=1+2*r
    band[2,:-1]=-r
    for _ in range(STEPS):
        right=u[1:-1].copy()
        right[0]+=r*HOT
        right[-1]+=r*COLD
        u[1:-1]=solve_banded((1,1),band,right,overwrite_ab=False,overwrite_b=True,check_finite=False)
    return x,u


def maxwell_pdf(v,T):
    """3D Maxwell speed PDF, with k_B=m=1: v>=0."""
    v=np.asarray(v,dtype=float)
    sigma=np.sqrt(K_B*T/MASS)
    return np.sqrt(2/np.pi)*v**2/sigma**3*np.exp(-v*v/(2*sigma*sigma))


def particles_from_local_equilibrium(x,u):
    rng=np.random.default_rng(SEED)
    xyz=rng.random((N_PARTICLES,3))
    T=np.interp(xyz[:,0],x,u)
    v=rng.normal(size=(N_PARTICLES,3))*np.sqrt(T*K_B/MASS)[:,None]
    return xyz,T,v


def validate(x,u,xyz,localT,v):
    exact=HOT+(COLD-HOT)*x
    err=float(np.max(np.abs(u-exact)))
    grad=np.gradient(u,x)
    flux=-CONDUCTIVITY*grad
    mid=flux[15:-15]
    flux_error=float(np.max(np.abs(mid-CONDUCTIVITY*(HOT-COLD)))/ (CONDUCTIVITY*(HOT-COLD)))
    diffs=np.diff(u)
    pdf_norm={str(T):float(quad(lambda speed:float(maxwell_pdf(speed,T)),0,np.inf,epsabs=1e-10)[0]) for T in (COLD,(HOT+COLD)/2,HOT)}
    # More extensive independent Monte Carlo checks, not used as the illustrated sample.
    gen=np.random.default_rng(SEED+1)
    stats={}
    for T in (COLD, (HOT+COLD)/2, HOT):
        vel=gen.normal(0,np.sqrt(T),size=(18000,3))
        speed=np.linalg.norm(vel,axis=1)
        estimated=float(np.mean(speed**2))
        expected=3*T
        stats[str(T)]={'mean_squared_speed':estimated,'expected':expected,
                       'relative_error':abs(estimated-expected)/expected}
    tests={
        'hot_to_cold_temperature_monotonic':bool(np.all(diffs<1e-8)),
        'heat_equation_steady_reference_max_error_less_1e-4':bool(err<1e-4),
        'fourier_flux_relative_uniformity_less_1e-3':bool(flux_error<1e-3),
        'maxwell_pdf_normalisation_below_1e-8':bool(all(abs(z-1)<1e-8 for z in pdf_norm.values())),
        'sampled_velocity_mean_squared_relative_error_below_3pct':bool(all(z['relative_error']<.03 for z in stats.values())),
        'sampled_all_particle_temperatures_in_bounds':bool(np.all((localT>=COLD-1e-8)&(localT<=HOT+1e-8))),
        'correct_dirichlet_wall_temperatures':bool(u[0]==HOT and u[-1]==COLD),
        'particles_within_box':bool(np.all((xyz>=0)&(xyz<=1))),
    }
    assert all(tests.values()), (tests,err,flux_error)
    return {
        'method':'backward Euler, 1D heat diffusion with Dirichlet walls; local 3D Maxwellian ideal-gas velocities',
        'seed':SEED,'nx':NX,'time':DT*STEPS,'temperature_left':HOT,'temperature_right':COLD,
        'temperature_field_max_abs_error_vs_linear_steady':err,
        'dimensionless_fourier_heat_flux':float(CONDUCTIVITY*(HOT-COLD)),
        'relative_heat_flux_nonuniformity_interior':flux_error,
        'maxwell_pdf_integrals':pdf_norm,'velocity_squared_mean_monte_carlo':stats,
        'particle_count':N_PARTICLES,'checks':tests,
        'limitations':'No molecular collisions or kinetic heat transport are simulated; local Maxwellians assume local equilibrium and particle trails are velocity indicators.'
    }


def temp_color(frac):
    """Red hot at left, icy blue cold at right; no particle speed encoded by hue."""
    cm=LinearSegmentedColormap.from_list('hotcold',['#C95028','#F09355','#DABF99','#7BB4D7','#2266A8'])
    return cm(frac)


def projection(x,y,z):
    return 1.18+12.95*x+.66*z,6.35+3.22*y+.55*z-.065*x


def temperature_box(ax, xyz, T, v, simplified=False):
    # Far face at z=1 and side; transparent acrylic-like 3D geometry.
    v0=[projection(a,b,c) for a,b,c in [(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
    v1=[projection(a,b,c) for a,b,c in [(0,0,0),(1,0,0),(1,1,0),(0,1,0)]]
    far=Polygon(v0,facecolor='#C9DAE3',alpha=.10,edgecolor=INK,lw=1)
    ax.add_patch(far)
    top=Polygon([v0[3],v0[2],v1[2],v1[3]],facecolor='#EEF5F5',alpha=.42,edgecolor='none')
    side=Polygon([v0[1],v0[2],v1[2],v1[1]],facecolor='#B4D7E7',alpha=.25,edgecolor='none')
    ax.add_patch(top);ax.add_patch(side)
    # A very transparent 2D thermal colour wash on the transparent main face.
    front=Polygon(v1,facecolor='#EADBC8',alpha=.10,edgecolor='none')
    ax.add_patch(front)
    w,h=1024,180
    colors=temp_color(np.linspace(0,1,w))
    rgba=np.tile(colors[None,:,:],(h,1,1))
    rgba[:,:,3]=.30
    image=ax.imshow(rgba,extent=(1.02,14.92,6.22,10.28),origin='lower',zorder=1,interpolation='bilinear')
    clip_verts=np.array([*v0,*v1])
    hull=np.array([v1[0],v1[1],v0[1],v0[2],v0[3],v1[3]])
    image.set_clip_path(Polygon(hull,closed=True,transform=ax.transData))
    # Physical particle velocity v determines length/direction of each short trail.
    # Draw back particles first for mild optical depth ordering.
    inds=np.argsort(xyz[:,2])[::-1]
    if simplified:
        # Pick a reproducible 110-particle subset evenly spaced along the x coordinate.
        srng=np.random.default_rng(SEED+13)
        picks=[]
        for k in range(11):
            binids=np.where((xyz[:,0]>=k/11)&(xyz[:,0]<(k+1)/11))[0]
            picks.extend(srng.choice(binids,size=min(10,len(binids)),replace=False).tolist())
        inds=np.array(sorted(picks,key=lambda i:xyz[i,2],reverse=True))
    for idx in inds:
        x,y,z=xyz[idx]
        sx,sy=projection(x,y,z)
        # View projected 3D velocity: x along length, y vertical, z perspective.
        tx= .062*v[idx,0]+.014*v[idx,2]
        ty= .065*v[idx,1]+.015*v[idx,2]
        col=temp_color(x)
        alpha=.34 if z>0.55 else .47
        ax.plot([sx-tx*1.25,sx],[sy-ty*1.25,sy],color=col,alpha=alpha,lw=1.2 if not simplified else 1.4,zorder=3)
        s=(31 if not simplified else 68)*(0.73+0.3*(1-z))
        ax.scatter([sx],[sy],s=s*1.85,color='white',alpha=.35,edgecolors='none',zorder=4)
        ax.scatter([sx],[sy],s=s,color=col,alpha=.94,edgecolors='#FFFFFF',linewidths=.23,zorder=5)
        ax.scatter([sx-.018],[sy+.019],s=s*.12,color='white',alpha=.7,edgecolors='none',zorder=6)
    # Box frame over particles; physical box edges from projected corners.
    for face,opacity in ((v0,.34),(v1,.60)):
        closed=face+[face[0]]
        ax.plot(*np.array(closed).T,color=INK,lw=1.30 if not simplified else 1.6,alpha=opacity,zorder=9)
    for a,b in zip(v0,v1):
        ax.plot([a[0],b[0]],[a[1],b[1]],color=INK,lw=1.15,alpha=.32,zorder=9)


def draw_details(ax, xyz, v, centers):
    pick=np.random.default_rng(SEED+22)
    r=.96
    for j,(xc,Tc) in enumerate(zip(centers,[HOT-(HOT-COLD)*.17,HOT-(HOT-COLD)*.5,HOT-(HOT-COLD)*.83])):
        cx=2.9+5.1*j
        cy=4.31
        col=temp_color([.16,.5,.84][j])
        circ=Circle((cx,cy),r,edgecolor=col,facecolor=to_rgba(col,.08),lw=1.8,zorder=11)
        ax.add_patch(circ)
        near=np.flatnonzero(np.abs(xyz[:,0]-xc)<.16)
        pick.shuffle(near)
        selected=near[:32]
        for idx in selected:
            py=(xyz[idx,1]-.5)*1.60
            pz=(xyz[idx,2]-.5)*1.60
            if py*py+pz*pz>(r-.08)**2:
                continue
            px2=cx+py; py2=cy+pz
            vv=v[idx]
            trail_len=.064*np.hypot(vv[0],vv[1])
            angle=np.arctan2(vv[1],vv[0])
            trailx=trail_len*np.cos(angle)
            traily=trail_len*np.sin(angle)
            ax.plot([px2-trailx,px2],[py2-traily,py2],color=col,alpha=.30,lw=1.3,zorder=12)
            ax.scatter([px2],[py2],s=46,color=temp_color(xyz[idx,0]),edgecolors='white',linewidths=.25,zorder=13)
        sample_sx,_=projection(xc,0,0)
        ax.plot([sample_sx,cx],[6.27,cy+r+.03],ls=(0,(2.3,4.5)),color=col,lw=1.20,alpha=.65,zorder=10)
        ax.scatter([sample_sx],[6.27],s=25,color=col,edgecolors='white',zorder=14)


def distribution_sparklines(ax,u,x):
    speed=np.linspace(0,8.0,550)
    selected=[.17,.50,.83]
    xmax=8.
    peak=maxwell_pdf(speed,np.interp(.83,x,u)).max()
    for j,xc in enumerate(selected):
        Tx=float(np.interp(xc,x,u))
        pdf=maxwell_pdf(speed,Tx)
        x0=1.35+5.12*j
        w=3.1
        y0=.90
        height=1.70
        xx=x0+speed/xmax*w
        yy=y0+pdf/peak*height
        col=temp_color(xc)
        ax.plot([x0,x0+w],[y0,y0],lw=.9,color=INK,alpha=.4,zorder=10)
        # faint layered fills
        for a in np.linspace(.30,.03,16):
            ax.fill_between(xx,y0,yy,where=yy>=y0,color=col,alpha=.0105,zorder=1)
        ax.plot(xx,yy,color=col,lw=2.0,zorder=11)


def full_render(x,u,xyz,T,v):
    fig,ax=plt.subplots(figsize=(16,12),dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_position((0,0,1,1))
    ax.set_xlim(0,16);ax.set_ylim(0,12);ax.set_aspect('equal');ax.axis('off')
    # Global subtle atmosphere behind large rectangular experiment box.
    xx=np.linspace(0,16,1200)
    yy=np.linspace(0,12,900)
    X,Y=np.meshgrid(xx,yy)
    light=np.exp(-((Y-8.2)/2.0)**2)*np.exp(-((X-8)/9.4)**6)
    bg_rgba=np.zeros((*light.shape,4))
    bg_rgba[:,:,:3]=np.array([0.92,0.85,0.74])
    bg_rgba[:,:,3]=.028*light
    ax.imshow(bg_rgba,extent=(0,16,0,12),origin='lower',zorder=-5)
    temperature_box(ax,xyz,T,v)
    draw_details(ax,xyz,v,[.17,.5,.83])
    distribution_sparklines(ax,u,x)
    main=OUT/'pbc_thermodynamics_hot_cold.png'
    fig.savefig(main,dpi=150,facecolor=BG,pad_inches=0)
    plt.close(fig)
    return main


def detail_diagnostic(x,u,xyz,T,v):
    fig,axs=plt.subplots(1,2,figsize=(12.5,4.5),dpi=170)
    fig.set_facecolor(BG)
    for a in axs:a.set_facecolor(BG)
    axs[0].plot(x,u,color=COPPER,lw=2.3,label='numerical heat equation')
    axs[0].plot(x,HOT+(COLD-HOT)*x,color=BLUE,lw=1.5,ls='--',label='steady Fourier reference')
    axs[0].set(xlabel='position x/L',ylabel='temperature (normalised units)',title='Heat conduction')
    axs[0].legend(frameon=False,fontsize=8)
    vv=np.linspace(0,8,550)
    for xc in [.17,.50,.83]:
        tx=np.interp(xc,x,u)
        axs[1].plot(vv,maxwell_pdf(vv,tx),color=temp_color(xc),lw=2,label=f'x/L={xc:.2f}, T={tx:.2f}')
    axs[1].set(xlabel='particle speed (normalised units)',ylabel='probability density',title='Three-dimensional Maxwell speed distributions')
    axs[1].legend(frameon=False,fontsize=8)
    for a in axs:
        a.spines[['top','right']].set_visible(False)
        a.grid(alpha=.12)
    fig.tight_layout()
    path=OUT/'pbc_thermodynamics_hot_cold_diagnostic.png'
    fig.savefig(path,facecolor=BG,bbox_inches='tight');plt.close(fig)
    return path


def custom_card(xyz,T,v):
    # A simplified independent layout using EXACTLY the same calculated particle state.
    fig,ax=plt.subplots(figsize=(8,6),dpi=120)
    fig.patch.set_facecolor(BG);ax.set_facecolor(BG)
    ax.set_position((0,0,1,1));ax.set_xlim(.50,15.45);ax.set_ylim(5.45,10.38)
    ax.axis('off');ax.set_aspect('auto')
    temperature_box(ax,xyz,T,v,simplified=True)
    out=OUT/'pbc_thermodynamics_hot_cold_card_master.png'
    fig.savefig(out,dpi=120,facecolor=BG,pad_inches=0)
    plt.close(fig)
    return out


def make_svg_embed(png_path,svg_path):
    raw=png_path.read_bytes()
    img=Image.open(png_path)
    payload=base64.b64encode(raw).decode('ascii')
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{img.width}" height="{img.height}" '
         f'viewBox="0 0 {img.width} {img.height}">' 
         f'<image width="{img.width}" height="{img.height}" href="data:image/png;base64,{payload}"/>'
         '</svg>')
    svg_path.write_text(svg,encoding='utf8')


def outputs():
    x,u=temperature_solution()
    xyz,T,v=particles_from_local_equilibrium(x,u)
    validations=validate(x,u,xyz,T,v)
    OUT.joinpath('validation.json').write_text(json.dumps(validations,indent=2),encoding='utf8')
    np.savez_compressed(OUT/'computed_data.npz',position_grid=x,temperature=u,
                        particle_xyz=xyz,particle_local_T=T,particle_velocity=v)
    img=full_render(x,u,xyz,T,v)
    detail_diagnostic(x,u,xyz,T,v)
    card=custom_card(xyz,T,v)
    full=Image.open(img).convert('RGB')
    full.save(OUT/'pbc_thermodynamics_hot_cold.webp','WEBP',quality=92,method=6)
    make_svg_embed(img,OUT/'pbc_thermodynamics_hot_cold.svg')
    panel=full.resize((800,600),Image.Resampling.LANCZOS)
    panel.save(OUT/'pbc_thermodynamics_hot_cold_atlas_panel.png')
    panel.resize((200,150),Image.Resampling.LANCZOS).save(OUT/'pbc_thermodynamics_hot_cold_atlas_panel_200px.png')
    # Tight crop of the same physically sampled particles, adjusted for 76px legibility.
    c=Image.open(card).convert('RGB')
    c.resize((76,57),Image.Resampling.LANCZOS).save(OUT/'pbc_thermodynamics_hot_cold_atlas_card_76px.png')
    # Square: still the same simple box, crop central area without distorting aspect ratio.
    cw,ch=c.size
    square=ImageOps.fit(c,(76,76),method=Image.Resampling.LANCZOS,centering=(.5,.5))
    square.save(OUT/'pbc_thermodynamics_hot_cold_atlas_card_76px_square.png')
    c.resize((608,456),Image.Resampling.LANCZOS).save(OUT/'pbc_thermodynamics_hot_cold_atlas_card_preview_8x.png')
    square.resize((456,456),Image.Resampling.NEAREST).save(OUT/'pbc_thermodynamics_hot_cold_atlas_card_square_preview_6x.png')
    return validations

if __name__=='__main__':
    print(json.dumps(outputs(),indent=2))
