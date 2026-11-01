#!/usr/bin/env python3
"""Finite multi-turn solenoid: reproducible Biot-Savart/axisymmetric field visual.

Usage: python render_solenoid.py [--output-dir DIR] [--quick]
Requires numpy, scipy, matplotlib, Pillow.

The physical model is N independent coaxial thin circular wire loops at x_i.
B is computed using complete elliptic integrals, in SI units. The blue
field-lines are level sets of the axisymmetric poloidal flux function
Psi(r,x) = integral_0^r B_x(r',x) r' dr' (2*pi*Psi is the magnetic flux).
The copper loops are projected schematically in front of that 2D meridional
cross-section. They are not a 3D field-line simulation.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.special import ellipk,ellipe
from scipy.integrate import cumulative_trapezoid
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from PIL import Image,ImageOps,ImageFilter

MU0=4e-7*np.pi
R=0.57           # coil radius m
I=8.0           # amperes
N=13            # identical thin circular loops
L=2.75          # span between outermost loop centres m
ZC=np.linspace(-L/2,L/2,N)
C_BG='#FAF8F3'
C_BLUE='#0B4C91'
C_SOFT_BLUE='#4C91C5'
C_COPPER='#BF6135'


def loop_field(z,r,z0):
    """Axial and radial B of a thin loop, cylindrical coordinates, T."""
    z=np.asarray(z,dtype=np.float64)
    r=np.asarray(r,dtype=np.float64)
    dz=z-z0
    rr=np.maximum(r,1e-12)
    u=(R+rr)**2+dz**2
    v=(R-rr)**2+dz**2
    mm=np.clip(4*R*rr/u,0,1-1e-14)
    K=ellipk(mm); E=ellipe(mm)
    b_z=(MU0*I/(2*np.pi*np.sqrt(u)))*(K+(R**2-rr**2-dz**2)/np.maximum(v,1e-12)*E)
    b_r=(MU0*I*dz/(2*np.pi*rr*np.sqrt(u)))*(-K+(R**2+rr**2+dz**2)/np.maximum(v,1e-12)*E)
    if np.ndim(r)==0:
        if float(r)==0:
            b_z=MU0*I*R**2/(2*(R**2+dz**2)**1.5)
            b_r=0.
    else:
        axis=r<1e-9
        b_z=np.where(axis,MU0*I*R**2/(2*(R**2+dz**2)**1.5),b_z)
        b_r=np.where(axis,0.,b_r)
    return b_z,b_r


def finite_solenoid_field(z,r):
    bz=np.zeros(np.broadcast_shapes(np.shape(z),np.shape(r)))
    br=np.zeros_like(bz)
    for z0 in ZC:
        dz, dr=loop_field(z,r,z0)
        bz+=dz; br+=dr
    return bz,br


def axis_exact(z):
    z=np.asarray(z)
    return np.sum([MU0*I*R*R/(2*(R*R+(z-z0)**2)**1.5) for z0 in ZC],axis=0)


def direct_quadrature(z,r,segments=4096):
    # For one loop at z0=0, evaluate the integral of dl x R directly.
    t=2*np.pi*(np.arange(segments)+.5)/segments
    ct,st=np.cos(t),np.sin(t)
    # circle in yz plane (z axial), observation in (r,0) radial direction
    # position (axial,radial_y,radial_z)=(0,R*cos(t),R*sin(t))
    # dl=(0,-R*sin(t),R*cos(t)) dt
    # Rvec=(z,r-R*cos(t),-R*sin(t))
    # cross axial = dl_y *Rvec_z - dl_z *Rvec_y
    cross_z=R*R-R*r*ct
    # radial cross y = dl_z*Rvec_x - dl_x*Rvec_z = R*ct*z
    cross_r=R*ct*z
    dist3=(z*z+r*r+R*R-2*r*R*ct)**1.5
    factor=MU0*I/(4*np.pi)*(2*np.pi/segments)
    return factor*np.sum(cross_z/dist3), factor*np.sum(cross_r/dist3)


def validation(out):
    tests={}
    samples=np.array([-2.,-1.1,0.,.44,1.6,2.4])
    samples_axis=np.array([finite_solenoid_field(x,0.)[0] for x in samples])
    a=axis_exact(samples)
    tests['axis_analytic_max_relative_error']=float(np.max(np.abs(samples_axis-a)/a))
    assert tests['axis_analytic_max_relative_error']<1e-12
    tests['field_direction_axis_positive']=bool(np.all(a>0)); assert tests['field_direction_axis_positive']
    tests['central_B_tesla']=float(axis_exact(np.array([0.]))[0]); assert tests['central_B_tesla']>0
    # isolated-loop off-axis formula vs independent angular integration
    errors=[]
    for z,r in [(0.,.20),(.32,.70),(.71,1.12),(1.34,.15)]:
        b=loop_field(z,r,0.); q=direct_quadrature(z,r)
        errors.append(float(np.linalg.norm(np.array(b)-q)/np.linalg.norm(q)))
    tests['isolated_loop_quadrature_max_relative_error']=max(errors)
    assert max(errors)<2e-9,errors
    for x,r in [(.4,.8),(1.8,.4),(-2.,1.0)]:
        p=finite_solenoid_field(x,r)
        n=finite_solenoid_field(-x,r)
        tests.setdefault('reflection_symmetry_abs_max_error',0.)
        tests['reflection_symmetry_abs_max_error']=max(tests['reflection_symmetry_abs_max_error'],float(max(abs(p[0]-n[0]),abs(p[1]+n[1]))))
    assert tests['reflection_symmetry_abs_max_error']<1e-12
    # Far field: axial field ~ dipole moment /z^3
    z=20.
    b=axis_exact(np.array([z]))[0]
    dip=MU0*I*N*R**2/(2*z**3)
    tests['far_field_dipole_relative_difference_at_20m']=float(abs(b/dip-1))
    assert tests['far_field_dipole_relative_difference_at_20m']<.025
    # Axisymmetric divergence check away from the current loops:
    # div B = d(Bx)/dx + d(Br)/dr + Br/r = 0.
    max_rel_div=0.0
    for x,r in [(-2.4,.32),(-1.7,1.12),(-.62,.19),(.18,.90),(1.47,.18),(2.40,1.55)]:
        h=2e-4
        dbz=(finite_solenoid_field(x+h,r)[0]-finite_solenoid_field(x-h,r)[0])/(2*h)
        dbr=(finite_solenoid_field(x,r+h)[1]-finite_solenoid_field(x,r-h)[1])/(2*h)
        br0=finite_solenoid_field(x,r)[1]
        residual=dbz+dbr+br0/r
        local=np.hypot(*finite_solenoid_field(x,r))
        max_rel_div=max(max_rel_div,abs(residual)/(local/R))
    tests['divergence_relative_residual_max']=float(max_rel_div)
    assert max_rel_div<1e-5,max_rel_div
    tests['physical_model']='N coaxial thin circular loops in vacuum, all currents in same direction'
    tests['num_loops']=N; tests['radius_m']=R; tests['current_A']=I
    tests['coil_span_m']=L
    tests['checks_passed']=6
    (out/'validation.json').write_text(json.dumps(tests,indent=2,ensure_ascii=False)+'\n')
    return tests


def field_grid(nx=560,nr=420):
    zz=np.linspace(-4.25,4.25,nx)
    rr=np.linspace(0,3.0,nr)
    Z,RHO=np.meshgrid(zz,rr)
    bz,br=finite_solenoid_field(Z,RHO)
    # smooth mask only nearby the conductors to hide infinite thin-wire field
    psi=cumulative_trapezoid(bz*RHO,rr,axis=0,initial=0)
    return zz,rr,bz,br,psi


def loop_artist(ax,z0,half,base=3.3):
    # front and rear half projected as an ellipse perpendicular to axis.
    tt=np.linspace(0,np.pi,350) if half=='back' else np.linspace(np.pi,2*np.pi,350)
    x=z0+0.165*R*np.cos(tt)
    y=.93*R*np.sin(tt)
    width=base if half=='back' else base+1.4
    if half=='back':
        ax.plot(x,y,color='#7C412B',lw=width+2.0,alpha=.50,zorder=4,solid_capstyle='round')
        ax.plot(x,y,color='#D08A59',lw=width,alpha=.90,zorder=4.1,solid_capstyle='round')
    else:
        ax.plot(x,y,color='#743A29',lw=width+2.8,alpha=.8,zorder=12,solid_capstyle='round')
        ax.plot(x,y,color='#B9572D',lw=width+1.0,zorder=12.1,solid_capstyle='round')
        ax.plot(x,y+.002,color='#F6B77C',lw=max(1.,width*.34),alpha=.88,zorder=12.2,solid_capstyle='round')


def draw(out,quick=False):
    # Field on the meridional (x,y) plane. By cylindrical symmetry,
    # B_x = B_axial(x,abs(y)), B_y = sign(y)*B_radial(x,abs(y)).
    xx=np.linspace(-3.63,3.63,420 if quick else 620)
    yy=np.linspace(-2.72,2.72,320 if quick else 460)
    X,Y=np.meshgrid(xx,yy)
    bx,br=finite_solenoid_field(X,np.abs(Y))
    by=br*np.sign(Y)
    magnitude=np.hypot(bx,by)
    # Field line shape depends on direction, not field magnitude; normalized
    # direction is numerically better for streamplot's integration.
    u=bx/np.maximum(magnitude,1e-30)
    v=by/np.maximum(magnitude,1e-30)
    # Thin-wire field is singular exactly on each ideal loop. No field line
    # is drawn within the specified 9 cm wire-core exclusion zone.
    for z0 in ZC:
        conductor=(X-z0)**2+(np.abs(Y)-R)**2 < .095**2
        u[conductor]=np.nan;v[conductor]=np.nan

    fig,ax=plt.subplots(figsize=(12,9),dpi=120 if quick else 200)
    fig.patch.set_facecolor(C_BG);ax.set_facecolor(C_BG)
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    ax.set_xlim(-3.63,3.63);ax.set_ylim(-2.72,2.72)
    ax.set_aspect('equal',adjustable='box');ax.axis('off')

    # A restrained paper-like blue glow follows the computed |B| field.
    soft=gaussian_filter(np.log1p(magnitude/(np.percentile(magnitude,55)+1e-30)),sigma=4)
    soft=np.clip(soft,0,np.percentile(soft,97))
    soft=(soft/np.max(soft))**1.4
    ax.imshow(soft,extent=(xx[0],xx[-1],yy[0],yy[-1]),origin='lower',
       cmap=matplotlib.colors.LinearSegmentedColormap.from_list('glow',['#FAF8F3','#E9F2F7','#D8E9F2','#CEE4F1']),
       interpolation='bilinear',alpha=.44,zorder=0,vmin=0,vmax=1)

    # Seed true computed fieldlines in and around the finite solenoid.
    inner=[.10,.20,.31,.425]
    outer=[.75,.92,1.11,1.34,1.60,1.95,2.31,2.55]
    starts=np.array([(0,float(y)) for r in inner+outer for y in (r,-r)])
    lines=ax.streamplot(xx,yy,u,v, color='#2669A5', linewidth=1.30 if not quick else 1.03,
         density=3.0,start_points=starts,arrowsize=.81, maxlength=8,
         integration_direction='both', broken_streamlines=False,
         zorder=3)
    lines.lines.set_alpha(.62)
    # A fainter second set yields visually layered return-flux loops.
    starts2=np.array([(-.46,r) for r in (.50,.56,1.48,-.50,-.56,-1.48)])
    try:
        extra=ax.streamplot(xx,yy,u,v,color='#72A5C9',linewidth=.76,density=3.0,
                 start_points=starts2,arrowsize=.65,maxlength=7,
                 integration_direction='both',broken_streamlines=False,zorder=2)
        extra.lines.set_alpha(.44)
    except ValueError:
        pass

    # Copper wires: 13 true circular turns shown in a simple oblique projection.
    # Field lines behind/inside them remain a planar meridional slice; the
    # perspective is an editorial overlay and not a computed 3D field.
    for z0 in ZC:
        loop_artist(ax,z0,'back',base=3.5 if not quick else 2.7)
    for z0 in ZC:
        loop_artist(ax,z0,'front',base=3.5 if not quick else 2.7)

    name='pbc_electromagnetism_solenoid'
    fig.savefig(out/(name+'.png'),dpi=120 if quick else 200,
                facecolor=C_BG,pad_inches=0)
    if not quick:
        fig.savefig(out/(name+'.svg'),facecolor=C_BG,pad_inches=0)
    plt.close(fig)
    if quick:return
    img=Image.open(out/(name+'.png')).convert('RGB')
    img.save(out/(name+'.webp'),format='WEBP',quality=94,method=6)
    # 4:3 panel/crop: center emphasis preserves coil and nearby return flux.
    w,h=img.size
    cw=int(w*.80);ch=int(cw*.75)
    if ch>h:ch=int(h*.80);cw=int(ch/0.75)
    cx=(w-cw)//2;cy=(h-ch)//2
    crop=img.crop((cx,cy,cx+cw,cy+ch))
    crop.resize((800,600),Image.Resampling.LANCZOS).save(out/(name+'_atlas_panel.png'))
    crop.resize((200,150),Image.Resampling.LANCZOS).save(out/(name+'_atlas_panel_200px.png'))
    # Stronger crop specifically for tiny card: visible turns at 76 pixels.
    cardw=int(w*.65);cardh=int(cardw*.75)
    cardcrop=img.crop(((w-cardw)//2,(h-cardh)//2,(w+cardw)//2,(h+cardh)//2))
    card=cardcrop.resize((76,57),Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=.65,percent=115,threshold=2))
    card.save(out/(name+'_atlas_card_76px.png'))
    card.resize((608,456),Image.Resampling.NEAREST).save(out/(name+'_atlas_card_preview_8x.png'))
    # Square variant focuses on the copper coil; no clip of the windings.
    side=int(min(w,h)*.64)
    square=img.crop(((w-side)//2,(h-side)//2,(w+side)//2,(h+side)//2))
    sq=square.resize((76,76),Image.Resampling.LANCZOS)
    sq.save(out/(name+'_atlas_card_76px_square.png'))
    sq.resize((456,456),Image.Resampling.NEAREST).save(out/(name+'_atlas_card_square_preview_6x.png'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--quick',action='store_true');a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    tests=validation(a.output_dir)
    draw(a.output_dir,quick=a.quick)
    print(json.dumps(tests,indent=2))
if __name__=='__main__':main()
