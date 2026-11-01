#!/usr/bin/env python3
"""PBC Course Atlas — coherent two-source interference, computed not invented.

Run: python render_waves.py
Requirements: numpy, scipy, matplotlib, pillow.

The monochromatic field for a 2D line source is the outgoing Helmholtz Green's
function H_0^(1)(k r). Sources are identical, in phase. The displayed
interference contrast C=(|u1+u2|²-|u1|²-|u2|²)/(|u1|²+|u2|²) is between -1,1.
C=+1 -> constructive interference; C=-1 -> destructive interference.
The real, time-averaged intensity at the detector is |u1+u2|².

All physical curves and wavefronts are numerically generated. Color grading,
opacity, glow, and the two source identities are purely graphical choices.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy.special import hankel1
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
LAMBDA=0.49  # arbitrary consistent spatial length units
K=2*np.pi/LAMBDA
SOURCES=[(-2.70, +1.04),(-2.70, -1.04)]
SCREEN_X=4.05
PAPER='#FAF8F3'
BLUE='#17548E'
COPPER='#B66B3F'

def source_field(x:np.ndarray,y:np.ndarray,source):
    r=np.hypot(x-source[0], y-source[1])
    return hankel1(0, K*np.maximum(r,1.0e-8))

def fields(x,y):
    a=source_field(x,y,SOURCES[0]); b=source_field(x,y,SOURCES[1]);
    return a,b,a+b

def contrast(a,b):
    denominator=np.abs(a)**2 + np.abs(b)**2
    return 2*np.real(a*np.conj(b))/denominator

def sample():
    xs=np.linspace(-4.55,4.62,1450)
    ys=np.linspace(-3.45,3.45,1090)
    x,y=np.meshgrid(xs,ys)
    a,b,u=fields(x,y)
    c=contrast(a,b)
    # source disk mask solely for display (line source is singular)
    disks=(np.hypot(x-SOURCES[0][0],y-SOURCES[0][1])<.12)|(np.hypot(x-SOURCES[1][0],y-SOURCES[1][1])<.12)
    return xs,ys,x,y,c,disks

def render():
    xs,ys,x,y,c,disks=sample()
    fig=plt.figure(figsize=(12,9),dpi=200,facecolor=PAPER)
    ax=fig.add_axes([0,0,1,1]);ax.set_aspect('equal');ax.axis('off')
    ax.set_xlim(-4.58,4.58);ax.set_ylim(-3.43,3.43);ax.set_facecolor(PAPER)
    cmap=LinearSegmentedColormap.from_list('fringes',[
        (0.0,'#B36D48'), (0.21,'#E8BEA3'), (0.50,'#F7F4EC'),
        (0.76,'#8DB7D3'), (1.0,'#17558B')],N=512)
    # Cinematic ink map, with no invented intensity structures.
    # The physical contrast is the only image-driving field.
    light = np.clip(c, -1,1)
    rgba=cmap((light+1)/2)
    # soft edges only in alpha (never changes the physical c-values)
    distance_from_center=np.hypot((x+0.4)/7.5, y/6.2)
    fade=np.clip((1.2-distance_from_center)/0.85,0,1)
    rgba[:,:,3]=0.69*fade
    rgba[disks,3]=0
    ax.imshow(rgba,origin='lower',extent=(xs[0],xs[-1],ys[0],ys[-1]),
        interpolation='bicubic',zorder=1,aspect='auto')
    # A few physical wavefronts (distance r_n from each coherent source).
    # The equal-phase lines of each wave are circular away from the source.
    theta=np.linspace(0,2*np.pi,1200)
    for i,((sx,sy),ink) in enumerate(zip(SOURCES,[BLUE,COPPER])):
        for n in range(1,16):
            radius=(n+0.40)*LAMBDA
            px=sx+radius*np.cos(theta)
            py=sy+radius*np.sin(theta)
            ax.plot(px,py,color=ink,alpha=0.085 if n%2 else 0.055,
                    linewidth=0.9,zorder=2)
    # Fine contours of computed interference contrast, no arbitrary curves.
    xx=x[::4,::4]; yy=y[::4,::4]; cc=c[::4,::4]
    ax.contour(xx,yy,cc,levels=[-.87,-.45],colors=[COPPER,COPPER],
               linewidths=[0.7,0.4],alpha=.22,zorder=3)
    ax.contour(xx,yy,cc,levels=[.45,.87],colors=[BLUE,BLUE],
               linewidths=[.4,.7],alpha=.28,zorder=3)
    # Faint axes of symmetry and connecting double-source vertical.
    ax.plot([-3.5,3.95],[0,0],color='#9BB0C1',linewidth=.5,alpha=.19,zorder=5,ls=(0,(2,8)))
    ax.plot([SOURCES[0][0]]*2,[SOURCES[1][1],SOURCES[0][1]],
            color='#A5B2B9',linewidth=1,alpha=.40,zorder=5)
    for i,(sx,sy) in enumerate(SOURCES):
        ink=BLUE if i==0 else COPPER
        for radius,alpha in ((.19,.035),(.155,.12),(.129,.12)):
            ax.add_patch(plt.Circle((sx,sy),radius,facecolor=ink,edgecolor='none',alpha=alpha,zorder=8))
        ax.add_patch(plt.Circle((sx,sy),.115,facecolor='#193A5D' if i==0 else '#A65731',
                                edgecolor=PAPER,linewidth=1.5,zorder=10))
        ax.add_patch(plt.Circle((sx-.025,sy+.036),.029,facecolor='#D1E6ED' if i==0 else '#F5C3A0',
                                edgecolor='none',alpha=.78,zorder=11))
    # A single right-side observation screen with directly computed I(y).
    yd=np.linspace(-3.13,3.13,900)
    a,b,u=fields(np.full_like(yd,SCREEN_X),yd)
    intensity=np.abs(u)**2
    ref=np.abs(a)**2+np.abs(b)**2
    relative=intensity/ref
    assert np.max(relative)<=2+1e-8 and np.min(relative)>=-1e-8
    rgb=np.array([int(BLUE[i:i+2],16) for i in (1,3,5)])/255
    paper=np.array([250,248,243])/255
    strip=np.empty((yd.size,16,4),float)
    # Screen depicts normalized enhancement, so brightness is readable from both sources.
    value=np.clip((relative/2)**0.9,0,1)
    for j in range(3): strip[:,:,j]=paper[j]*(1-value[:,None]*0.75)+rgb[j]*(value[:,None]*0.75)
    strip[:,:,3]=1
    ax.imshow(strip,origin='lower',extent=(4.21,4.41,-3.13,3.13),
              interpolation='bilinear',aspect='auto',zorder=6)
    ax.plot([4.21,4.21],[-3.13,3.13],color=COPPER,lw=1.35,alpha=.82,zorder=8)
    ax.plot([4.42,4.42],[-3.13,3.13],color=BLUE,lw=.65,alpha=.38,zorder=8)
    # tiny separation from vertical screen border
    ax.plot([4.05,4.05],[-3.13,3.13],color=BLUE,lw=.5,alpha=.17,zorder=5)
    base=ROOT/'pbc_waves_optics_interference'
    fig.savefig(str(base)+'.png',dpi=200,facecolor=PAPER,pad_inches=0)
    # True vector path waves and contours on top of a raster-computed contrast field.
    fig.savefig(str(base)+'.svg',dpi=150,facecolor=PAPER,pad_inches=0)
    plt.close(fig)
    im=Image.open(str(base)+'.png').convert('RGB')
    im.save(str(base)+'.webp',format='WEBP',quality=92,method=6)
    # Full panel 800x600 and actual displayed panel 200x150
    im.resize((800,600),Image.Resampling.LANCZOS).save(ROOT/'pbc_waves_optics_atlas_panel.png')
    im.resize((200,150),Image.Resampling.LANCZOS).save(ROOT/'pbc_waves_optics_atlas_panel_200px.png')
    card=im.resize((76,57),Image.Resampling.LANCZOS)
    # At display resolution, emphasize *actual* source locations with small
    # graphic dots, not new/fabricated patterns. The scientific field is unchanged.
    draw=ImageDraw.Draw(card)
    for (sx,sy),color in zip(SOURCES,(BLUE,COPPER)):
        px=(sx+4.58)/9.16*76
        py=(3.43-sy)/6.86*57
        draw.ellipse((px-2.5,py-2.5,px+2.5,py+2.5),fill=PAPER)
        draw.ellipse((px-1.5,py-1.5,px+1.5,py+1.5),fill=color)
    card.save(ROOT/'pbc_waves_optics_atlas_card_76px.png')
    # Square crop focused on the sources and the near-field pattern.
    square=im.crop((160,0,1960,1800)).resize((76,76),Image.Resampling.LANCZOS)
    d2=ImageDraw.Draw(square)
    for (sx,sy),color in zip(SOURCES,(BLUE,COPPER)):
        px= ((sx+4.58)/9.16*2400-160)/1800*76
        py= ((3.43-sy)/6.86*1800)/1800*76
        d2.ellipse((px-2.5,py-2.5,px+2.5,py+2.5),fill=PAPER)
        d2.ellipse((px-1.5,py-1.5,px+1.5,py+1.5),fill=color)
    square.save(ROOT/'pbc_waves_optics_atlas_card_76px_square.png')
    Image.open(ROOT/'pbc_waves_optics_atlas_card_76px.png').resize((608,456),Image.Resampling.NEAREST).save(ROOT/'pbc_waves_optics_atlas_card_preview_8x.png')
    square.resize((456,456),Image.Resampling.NEAREST).save(ROOT/'pbc_waves_optics_atlas_card_square_preview_6x.png')
    return yd,relative,ref,intensity

def check(yd,relative,ref,intensity):
    from scipy.signal import find_peaks
    # Check self-consistency of interference in complex field and equal source amplitude.
    rng=np.random.default_rng(20261030)
    xp=rng.uniform(-.5,3.8,100)
    yp=rng.uniform(-2.3,2.3,100)
    a,b,u=fields(xp,yp)
    identity_err=float(np.max(np.abs(np.abs(u)**2 -
        (np.abs(a)**2+np.abs(b)**2+2*np.real(a*np.conj(b))))))
    assert identity_err<1e-12
    xx=np.linspace(-.15,2.5,150);yy=np.linspace(-2.,2.,150)
    A,B,U=fields(xx[None,:],yy[:,None]);
    mirror_err=float(np.max(np.abs(U-np.flipud(U))))
    assert mirror_err<1e-12
    mid_idx=int(np.argmin(abs(yd)))
    central_ratio=float(relative[mid_idx])
    assert abs(central_ratio-2)<0.002
    # The 2D outgoing cylindrical Green function solves (Laplace+k²)u=0 away from sources.
    hx=0.003
    x0,y0=1.5,1.1
    f=lambda dx,dy: fields(np.array([x0+dx]),np.array([y0+dy]))[2][0]
    value=f(0,0)
    lap=(f(hx,0)+f(-hx,0)+f(0,hx)+f(0,-hx)-4*value)/hx**2
    residual=float(abs(lap+K*K*value)/(K*K*abs(value)))
    assert residual<0.0006, residual
    # Far field: intensity is proportional to cos^2(k d sin(theta)/2).
    theta=np.linspace(-.37,.37,301)
    dist=70.0
    xfar=70*np.cos(theta)+SOURCES[0][0]
    yfar=70*np.sin(theta)
    fa,fb,fu=fields(xfar,yfar)
    far_ref=np.abs(fa)**2+np.abs(fb)**2
    model=np.abs(fu)**2/far_ref
    analytic=2*np.cos(np.pi*(SOURCES[0][1]-SOURCES[1][1])*np.sin(theta)/LAMBDA)**2
    far_err=float(np.max(np.abs(model-analytic)))
    assert far_err<0.035,far_err
    # On screen show fringe count and max/min using physically computed source waves
    peaks,prop=find_peaks(relative,prominence=.18,distance=20)
    troughs,_=find_peaks(-relative,prominence=.18,distance=20)
    assert len(peaks)>=3 and len(troughs)>=3,(len(peaks),len(troughs))
    stats={
      'model':'Two coherent in-phase cylindrical outgoing Helmholtz Green functions H0^(1)(k r)',
      'wavelength_units':LAMBDA,
      'source_separation_units':SOURCES[0][1]-SOURCES[1][1],
      'screen_x_units':SCREEN_X,
      'superposition_identity_max_abs_error':identity_err,
      'mirror_symmetry_max_abs_error':mirror_err,
      'constructive_center_ratio_to_incoherent':central_ratio,
      'helmholtz_relative_residual':residual,
      'farfield_cosine_squared_max_absolute_error':far_err,
      'screen_local_maxima_count':int(len(peaks)),
      'screen_local_minima_count':int(len(troughs)),
      'all_tests_passed':True,
    }
    (ROOT/'validation.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
    return stats

def explainer(yd,relative):
    fig,ax=plt.subplots(figsize=(11,5),dpi=180,facecolor=PAPER)
    ax.set_facecolor(PAPER)
    ax.plot(yd,relative,color=BLUE,lw=2.2,label='Coherent intensity / incoherent baseline')
    ax.plot(yd,2-relative,color=COPPER,alpha=.0)  # intentionally not displayed
    ax.fill_between(yd,relative,1,where=relative>=1,color=BLUE,alpha=.14)
    ax.fill_between(yd,relative,1,where=relative<1,color=COPPER,alpha=.13)
    ax.axhline(1,color='#97A6B5',lw=.9,ls='--')
    ax.axvline(0,color='#97A6B5',lw=.7,alpha=.7)
    ax.set_xlabel('Detector position y (arbitrary length units)',fontsize=11)
    ax.set_ylabel(r'$I_\mathrm{coh}/(I_1+I_2)$',fontsize=12)
    ax.set_title('Coherent two-source interference — detector intensity',fontsize=15,color='#203A52',pad=16)
    ax.spines[['top','right']].set_visible(False)
    for s in ('left','bottom'): ax.spines[s].set_color('#B4C0C4')
    ax.grid(alpha=.10)
    ax.set_ylim(0,2.1)
    fig.tight_layout(pad=2.2)
    fig.savefig(ROOT/'pbc_waves_optics_diagnostic.png',dpi=180,facecolor=PAPER)
    plt.close(fig)

def main():
    yd,rel,ref,intensity=render()
    stats=check(yd,rel,ref,intensity)
    explainer(yd,rel)
    print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
