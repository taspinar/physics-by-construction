#!/usr/bin/env python3
"""Physics by Construction — reproducible diatomic square-lattice phonon figures.

Usage:
    python render_phonons.py --output-dir /path/to/output

Physical model: a planar checkerboard crystal with two masses m_A, m_B.
Each site is connected to its four nearest neighbours by harmonic springs
with energy K/2*(u_i-u_j)^2, for scalar out-of-plane displacement u.
A linearised transverse-wave/effective-harmonic model, not a microscopic
central-force theory of a free-standing 3D crystal. This is a 2D crystalline
sheet visualised in perspective. Its dispersion is obtained from a 2x2
mass-weighted dynamical matrix. Everything drawn as displacement is calculated.

Requirements: numpy, matplotlib, Pillow.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import to_rgb
from PIL import Image, ImageFilter, ImageOps

BG = '#FAF8F3'
NAVY='#143858'; BLUE='#336E9C'; BLUE_HI='#83B3D0'
COPPER='#B75C2F'; COPPER_HI='#E7A271'; BOND='#647B85'
NX, NY = 24, 12  # periodic computational cell, both even
A = 1.0    # lattice spacing (model units)
MA, MB = 1.0, 2.0
K = 1.0    # harmonic spring coefficient (model units)
WAVE_NUMBER = 2  # exactly two periods across the periodic cell
KX = 2*np.pi*WAVE_NUMBER/(NX*A)
KY = 0.0
AMPLITUDE = 0.43*A
PHASE_OFFSET = -0.10


def mode_matrix(kx, ky):
    """Mass-weighted dynamical matrix for the bipartite square lattice.

    D_AA=4K/m_A; D_BB=4K/m_B; the four neighbours of every A are B.
    D_AB= -2K(cos(kx*a)+cos(ky*a))/sqrt(m_A*m_B).
    """
    c = 2*K*(np.cos(kx*A)+np.cos(ky*A))/np.sqrt(MA*MB)
    return np.array([[4*K/MA,-c],[-c,4*K/MB]],float)


def eigensystem(kx=KX,ky=KY):
    vals,vec=np.linalg.eigh(mode_matrix(kx,ky))
    vals=np.maximum(vals,0.0)
    vec=vec/np.sqrt(np.array([MA,MB]))[:,None]
    for col in range(2):
        if vec[0,col]<0:vec[:,col]*=-1
        vec[:,col]/=np.max(np.abs(vec[:,col]))
    return np.sqrt(vals),vec


def mode_fields(branch='acoustic', t=0.0):
    freqs,pols=eigensystem()
    b=0 if branch=='acoustic' else 1
    om=freqs[b]
    ii,jj=np.meshgrid(np.arange(NX),np.arange(NY),indexing='ij')
    species=(ii+jj)%2
    a=AMPLITUDE*pols[species,b]
    phase=KX*ii*A+KY*jj*A-om*t+PHASE_OFFSET
    u=a*np.cos(phase)
    v=a*om*np.sin(phase)
    return u,v,om,pols[:,b]


def bond_energy(u):
    return 0.5*K*np.sum((np.roll(u,-1,axis=0)-u)**2+(np.roll(u,-1,axis=1)-u)**2)


def kinetic(v):
    ii,jj=np.indices((NX,NY))
    mass=np.where((ii+jj)%2==0,MA,MB)
    return 0.5*np.sum(mass*v*v)


def forces(u):
    return K*(np.roll(u,1,axis=0)+np.roll(u,-1,axis=0)+np.roll(u,1,axis=1)+np.roll(u,-1,axis=1)-4*u)


def validate(outdir):
    result={'model':'2D diatomic square lattice; scalar transverse harmonic displacement; periodic boundaries',
            'parameters':{'Nx':NX,'Ny':NY,'m_A':MA,'m_B':MB,'K':K,'a':A,'kx':KX,'ky':KY,'amplitude':AMPLITUDE,'mode_wave_number':WAVE_NUMBER},
            'tests':{}}
    tests=result['tests']
    f0,p0=eigensystem(0,0)
    tests['acoustic_gap_at_Gamma']=float(f0[0])
    assert abs(f0[0])<1e-7
    tests['optical_gap_at_Gamma']=float(f0[1])
    assert np.isclose(f0[1],np.sqrt(4*K*(1/MA+1/MB)),rtol=1e-12)
    freqs,pols=eigensystem()
    tests['frequencies_at_illustrated_wavevector']={'acoustic':float(freqs[0]),'optical':float(freqs[1])}
    assert freqs[0]>0 and freqs[1]>freqs[0]
    tests['acoustic_same_sign']=bool(pols[0,0]*pols[1,0]>0)
    tests['optical_opposite_sign']=bool(pols[0,1]*pols[1,1]<0)
    assert tests['acoustic_same_sign'] and tests['optical_opposite_sign']
    tests['dispersion_reciprocity_max_err']=float(max(abs(eigensystem(k,0)[0]-eigensystem(-k,0)[0]).max() for k in np.linspace(-np.pi/(2*A),np.pi/(2*A),31)))
    assert tests['dispersion_reciprocity_max_err']<1e-12
    residuals={};energy_drift={}; sums={}
    ii,jj=np.indices((NX,NY)); mass=np.where((ii+jj)%2==0,MA,MB)
    for branch in ['acoustic','optical']:
        observed=[]; r=[]
        omega=eigensystem()[0][0 if branch=='acoustic' else 1]
        for t in np.linspace(0,2*np.pi/omega,13):
            u,v,_,_=mode_fields(branch,t)
            force=forces(u)
            residual=np.linalg.norm(force+mass*(omega**2)*u)/max(np.linalg.norm(force),1e-15)
            r.append(residual)
            observed.append(bond_energy(u)+kinetic(v))
        residuals[branch]=float(np.max(r))
        energy_drift[branch]=float((max(observed)-min(observed))/np.mean(observed))
        assert residuals[branch]<1e-12
        assert energy_drift[branch]<1e-12
        u,v,om,p=mode_fields(branch)
        sums[branch]={'mean_displacement':float(u.mean()),'max_displacement':float(abs(u).max()),'energy_model_units':float(bond_energy(u)+kinetic(v)),'sublattice_displacement_amplitudes':[float(x) for x in AMPLITUDE*p]}
    tests['equation_residual_relative_max']=residuals
    tests['energy_conservation_relative_max']=energy_drift
    tests['atomic_displacements']=sums
    tests['periodic_seams_even_lattice']=bool((NX%2==0) and (NY%2==0))
    assert tests['periodic_seams_even_lattice']
    tests['passed']=8
    (outdir/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result


def blend(c1,c2,t):
    x,y=np.array(to_rgb(c1)),np.array(to_rgb(c2))
    return tuple((1-t)*x+t*y)


def project(ii,jj,zz=0.0):
    """One consistent isometric view of the lattice and its displacements."""
    return 0.46*ii-0.34*jj, -0.18*ii-0.36*jj+1.50*zz


def draw_mode(branch,outfile,with_dispersion=True):
    u,_,omega,pol=mode_fields(branch)
    fig=plt.figure(figsize=(10,7.5),dpi=240,facecolor=BG)
    ax=fig.add_axes([0.012,0.035,0.976,0.94]);ax.set_facecolor(BG)
    ax.axis('off');ax.set_aspect('equal')
    ii,jj=np.indices((NX,NY))
    X,Y=project(ii,jj,u)
    # lattice projection extent, with room for an inset on top-right
    xmn,xmx=X.min(),X.max();ymn,ymx=Y.min(),Y.max()
    ax.set_xlim(xmn-0.75,xmx+0.75)
    ax.set_ylim(ymn-0.8,ymx+0.8)
    # smooth scientific tint: each cell represents the average out-of-plane displacement
    polys=[];cols=[]
    for i in range(NX-1):
        for j in range(NY-1):
            pts=np.array([[X[i,j],Y[i,j]],[X[i+1,j],Y[i+1,j]],
                          [X[i+1,j+1],Y[i+1,j+1]],[X[i,j+1],Y[i,j+1]]])
            polys.append(pts)
            # color of displacement, not a different field
            disp=np.mean(u[i:i+2,j:j+2])/(AMPLITUDE+1e-12)
            col=blend(BG,COPPER if disp>0 else BLUE, min(0.52,abs(disp)*0.50))
            cols.append(col)
    ax.add_collection(PolyCollection(polys,facecolors=cols,edgecolors='none',alpha=.80,zorder=0.8))
    # subtle traces marking the *undeformed* reference geometry for a line of atoms
    ghost_j=NY//2
    for i in range(0,NX,2):
        gx,gy=project(i,ghost_j,0)
        ax.add_patch(Circle((gx,gy),.048,fill=False,edgecolor='#C2C8C4',lw=.5,alpha=.5,zorder=2))
        ax.plot([gx,X[i,ghost_j]],[gy,Y[i,ghost_j]],color='#AEB8B6',lw=.7,alpha=.40,zorder=2)
    # 2d bonds connect nearest neighbours in the actual displaced lattice
    bonds=[]
    for i in range(NX):
        for j in range(NY):
            if i<NX-1:bonds.append([[X[i,j],Y[i,j]],[X[i+1,j],Y[i+1,j]]])
            if j<NY-1:bonds.append([[X[i,j],Y[i,j]],[X[i,j+1],Y[i,j+1]]])
    ax.add_collection(LineCollection(bonds,colors='#526B73',linewidths=.9,alpha=.56,zorder=1.8))
    # visual ripples / displacements are the interpolated physical mode
    # translucent, restrained highlights on one row, same analytic u_i values
    for j0,alpha in [(3,.24),(NY-4,.18)]:
        t=np.linspace(0,NX-1,420)
        colidx=int(j0%2)
        # interpolate actual discrete displacements (no fictitious long-wave overlay)
        uu=np.interp(t,np.arange(NX),u[:,j0])
        px,py=project(t,j0,uu)
        ax.plot(px,py,color=COPPER if j0==3 else BLUE,lw=2,alpha=alpha,zorder=2.0,solid_capstyle='round')
    # Draw rounded atoms with a directional highlight. Species is genuine A/B mass parity.
    points=[(Y[i,j],i,j) for i in range(NX) for j in range(NY)]
    points.sort(reverse=True) # far atoms first; visual overlap remains modest
    for _,i,j in points:
        x,y=X[i,j],Y[i,j]
        ca=BLUE if (i+j)%2==0 else COPPER
        light=BLUE_HI if (i+j)%2==0 else COPPER_HI
        rr=.118
        ax.add_patch(Circle((x+.013,y-.022),rr*1.12,facecolor='#B9BBB6',edgecolor='none',alpha=.16,zorder=3))
        ax.add_patch(Circle((x,y),rr,facecolor=ca,edgecolor=NAVY if (i+j)%2==0 else '#8C482C',linewidth=.55,zorder=4))
        ax.add_patch(Circle((x-.027,y+.035),rr*.50,facecolor=light,edgecolor='none',alpha=.61,zorder=5))
        ax.add_patch(Circle((x-.04,y+.05),rr*.22,facecolor='#FFFFFF',edgecolor='none',alpha=.52,zorder=6))
    # scientific miniature of two branches, placed in whitespace; no artificial data.
    if with_dispersion:
        # place panel by figure coords; actual frequency scale is physical eigenproblem
        inset=fig.add_axes([.752,.75,.184,.143],facecolor='none')
        kk=np.linspace(0,np.pi/(2*A),190)
        ff=np.array([eigensystem(k,0)[0] for k in kk])
        inset.plot(kk*A,ff[:,0],color=BLUE,lw=1.55)
        inset.plot(kk*A,ff[:,1],color=COPPER,lw=1.55)
        f=eigensystem(KX,0)[0]
        idx=0 if branch=='acoustic' else 1
        inset.scatter([KX*A],[f[idx]],s=22,c=[BLUE if idx==0 else COPPER],zorder=6,edgecolor=BG,lw=.5)
        inset.spines[['top','right']].set_visible(False)
        for side in ['left','bottom']:
            inset.spines[side].set_color('#9CA9A7');inset.spines[side].set_linewidth(.65)
        inset.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)
        inset.set_xlim(0,np.pi/2);inset.set_ylim(0,ff.max()*1.04)
    fig.savefig(outfile,dpi=240,facecolor=BG,pad_inches=0)
    plt.close(fig)


def draw_diagnostics(outpath):
    kk=np.linspace(0,np.pi/(2*A),240)
    om=np.array([eigensystem(k,0)[0] for k in kk])
    fig,ax=plt.subplots(figsize=(8.5,5.6),facecolor=BG)
    ax.set_facecolor(BG)
    ax.plot(kk*A,om[:,0],color=BLUE,lw=2.2,label='Acoustic mode')
    ax.plot(kk*A,om[:,1],color=COPPER,lw=2.2,label='Optical mode')
    for idx,c in [(0,BLUE),(1,COPPER)]:
        ax.plot(KX*A,eigensystem()[0][idx],'o',ms=8,color=c)
    ax.axvline(KX*A,linestyle=':',color='#79939B',lw=1)
    ax.set_xlabel(r'$k_x a$ (dimensionless)')
    ax.set_ylabel(r'$\omega\sqrt{m_A/K}$')
    ax.set_title('Diatomic square-lattice phonon dispersion (along $k_y=0$)')
    ax.legend(frameon=False)
    ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(outpath,dpi=170,facecolor=BG);plt.close(fig)


def draw_card_focus(branch, outdir, stem):
    """Independent zoomed-in scientific rendering for a 76px Atlas card.

    Uses exact atomic coordinates from the same mode, not retouched art.
    The card deliberately shows fewer atoms to remain legible at 76 pixels.
    """
    u,_,_,_=mode_fields(branch)
    xs=list(range(6,18)); ys=list(range(2,9))
    fig=plt.figure(figsize=(4,3),dpi=240,facecolor=BG)
    ax=fig.add_axes([.03,.06,.94,.88]);ax.set_aspect('equal');ax.axis('off');ax.set_facecolor(BG)
    i0,j0=np.meshgrid(xs,ys,indexing='ij');X,Y=project(i0,j0,u[np.ix_(xs,ys)])
    ax.set_xlim(X.min()-.42,X.max()+.42);ax.set_ylim(Y.min()-.38,Y.max()+.38)
    polys=[];cols=[]
    for ii in range(len(xs)-1):
        for jj in range(len(ys)-1):
            p=np.array([[X[ii,jj],Y[ii,jj]],[X[ii+1,jj],Y[ii+1,jj]],
                        [X[ii+1,jj+1],Y[ii+1,jj+1]],[X[ii,jj+1],Y[ii,jj+1]]])
            polys.append(p)
            d=np.mean(u[np.ix_(xs[ii:ii+2],ys[jj:jj+2])])/AMPLITUDE
            cols.append(blend(BG,COPPER if d>0 else BLUE,min(.45,abs(d)*.44)))
    ax.add_collection(PolyCollection(polys,facecolors=cols,edgecolors='none',alpha=.9))
    edges=[]
    for ii in range(len(xs)):
        for jj in range(len(ys)):
            if ii+1<len(xs):edges.append([[X[ii,jj],Y[ii,jj]],[X[ii+1,jj],Y[ii+1,jj]]])
            if jj+1<len(ys):edges.append([[X[ii,jj],Y[ii,jj]],[X[ii,jj+1],Y[ii,jj+1]]])
    ax.add_collection(LineCollection(edges,colors='#657883',linewidths=1.7,alpha=.70))
    for ii in range(len(xs)):
        for jj in range(len(ys)):
            ca=BLUE if (xs[ii]+ys[jj])%2==0 else COPPER
            hi=BLUE_HI if ca==BLUE else COPPER_HI
            x,y=X[ii,jj],Y[ii,jj]
            rr=.17
            ax.add_patch(Circle((x,y),rr,facecolor=ca,edgecolor=NAVY if ca==BLUE else '#7C432A',lw=.6))
            ax.add_patch(Circle((x-.05,y+.06),rr*.43,facecolor=hi,edgecolor='none',alpha=.8))
    temp=outdir/(stem+'_atlas_card_focused.png')
    fig.savefig(temp,dpi=240,facecolor=BG,pad_inches=0)
    plt.close(fig)
    with Image.open(temp) as im:
        im=im.convert('RGB')
        im.resize((76,57),Image.Resampling.LANCZOS).save(outdir/(stem+'_atlas_card_76px.png'))
        im.resize((76,57),Image.Resampling.LANCZOS).resize((608,456),Image.Resampling.NEAREST).save(outdir/(stem+'_atlas_card_preview_8x.png'))
        ImageOps.fit(im,(76,76),method=Image.Resampling.LANCZOS).save(outdir/(stem+'_atlas_card_76px_square.png'))
        ImageOps.fit(im,(76,76),method=Image.Resampling.LANCZOS).resize((456,456),Image.Resampling.NEAREST).save(outdir/(stem+'_atlas_card_square_preview_6x.png'))


def crop_and_resize(inp,outdir,stem):
    with Image.open(inp) as src:
        full=src.convert('RGB')
        full.save(outdir/(stem+'.webp'),format='WEBP',quality=91,method=6)
        w,h=full.size
        # the original is 4:3; variant focal crop zooms slightly for cards
        # better legibility: enlarged central lattice rather than empty margins/inset
        panel=ImageOps.fit(full,(800,600),method=Image.Resampling.LANCZOS,centering=(.49,.51))
        panel.save(outdir/(stem+'_atlas_panel.png'))
        panel.resize((200,150),Image.Resampling.LANCZOS).save(outdir/(stem+'_atlas_panel_200px.png'))
        # crop to remove inset & negative space; science remains computed without alteration
        c=full.crop((int(w*.14),int(h*.18),int(w*.85),int(h*.75)))
        card=ImageOps.fit(c,(76,57),method=Image.Resampling.LANCZOS)
        card=card.filter(ImageFilter.UnsharpMask(radius=.6,percent=85,threshold=2))
        card.save(outdir/(stem+'_atlas_card_76px.png'))
        card.resize((608,456),Image.Resampling.NEAREST).save(outdir/(stem+'_atlas_card_preview_8x.png'))
        square=ImageOps.fit(c,(76,76),method=Image.Resampling.LANCZOS)
        square.save(outdir/(stem+'_atlas_card_76px_square.png'))
        square.resize((456,456),Image.Resampling.NEAREST).save(outdir/(stem+'_atlas_card_square_preview_6x.png'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=Path(__file__).parent)
    args=parser.parse_args();out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    val=validate(out)
    for branch in ['acoustic','optical']:
        stem=f'pbc_condensed_matter_{branch}'
        img=out/(stem+'.png')
        draw_mode(branch,img,with_dispersion=True)
        crop_and_resize(img,out,stem)
        draw_card_focus(branch,out,stem)
        # The vector figure mirrors the exact geometry of the PNG.
        # Matplotlib saves high-resolution geometry as SVG paths, not a raster wrapper.
        # In order not to redraw all the numerical field a second time manually,
        # the existing draw function can be reused with an SVG suffix.
        draw_mode(branch,out/(stem+'.svg'),with_dispersion=True)
    draw_diagnostics(out/'pbc_condensed_matter_dispersion.png')
    print('OK:',val['tests'])

if __name__=='__main__':main()
