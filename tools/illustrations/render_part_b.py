"""Part B scientific illustration suite for Physics by Construction.

All outputs are deterministic, based on transparent synthetic demonstration
problems.  No real agent was run; no benchmark results are represented as
measured. All figures are original and not copied from the cited literature.

Usage: python render_part_b.py [--output DIR]
Requires: numpy, scipy, matplotlib, pillow.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
from numpy.random import default_rng
from scipy.integrate import solve_ivp
from scipy.special import ndtr
from scipy.linalg import cho_factor, cho_solve
from matplotlib import pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, FancyArrowPatch
from matplotlib.path import Path as MPath
from PIL import Image

BG='#FAF8F3'; PAPER='#FFFDF8'; NAVY='#142941'; COBALT='#346BA8'; BLUE='#729DCC'; SOFT='#C5D9E7'; COPPER='#C16B40'; ORANGE='#DA8B58'; MUTE='#7B8790'; GRID='#D9DAD6'; RED='#B34B3C'; GREEN='#397C70'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','figure.facecolor':BG,'axes.facecolor':BG,'savefig.facecolor':BG})


def make_data():
    rng=default_rng(20261030)
    # R1: physical oscillator in a known toy world; independent numeric integration
    omega0=2*np.pi*0.72; gamma=.24
    t=np.linspace(0,7.5,85)
    def solve(g):
        sol=solve_ivp(lambda _,z:[z[1],-2*g*z[1]-omega0**2*z[0]],(0,7.5),[1.,0.],t_eval=t,rtol=1e-11,atol=1e-13)
        return sol.y[0]
    truth=solve(gamma)
    data=truth+rng.normal(0,.043,len(t))
    candidates={'No damping':solve(0.0),'Damped':truth,'Strong damping':solve(.64)}
    chi={k:float(np.mean(((v-data)/.043)**2)) for k,v in candidates.items()}
    # R2: inverse-square force law fitted on train, evaluated on holdout
    r=np.linspace(.9,3.6,42)
    force=1.38/r**2
    fobs=force + rng.normal(0,.035,len(r))
    train=(np.arange(len(r))%3!=0)
    powers=[1,2,3]
    fits={}
    for p in powers:
        basis=1/r**p
        coeff=float(np.dot(basis[train],fobs[train])/np.dot(basis[train],basis[train]))
        pred=coeff*basis
        fits[str(p)]={'coefficient':coeff,'heldout_rmse':float(np.sqrt(np.mean((pred[~train]-fobs[~train])**2))),'prediction':pred}
    # R3: illustrative agent configurations, deliberately unnamed
    costs=np.array([.28,.50,.80,1.20,1.85,2.65,3.25,4.10,5.6])
    probs=np.array([.28,.44,.40,.54,.56,.63,.59,.72,.67]); n=120
    successes=rng.binomial(n,probs); rate=successes/n
    z=1.959963984540054
    mid=(rate+z*z/(2*n))/(1+z*z/n)
    rad=z/(1+z*z/n)*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))
    lo=mid-rad; hi=mid+rad
    optimal=np.array([not np.any((costs<=costs[i])&(rate>=rate[i])&((costs<costs[i])|(rate>rate[i]))) for i in range(len(rate))])
    # R4: GP active learning on a deterministic 2D toy response surface
    def objective(X):
        xx=X[:,0]; yy=X[:,1]
        return (.22+1.05*np.exp(-((xx-.70)**2/.055+(yy-.66)**2/.085))+.47*np.exp(-((xx-.23)**2/.028+(yy-.31)**2/.043))-.14*(xx-.6)**2-.06*yy)
    grid_s=np.linspace(.035,.965,83)
    xx,yy=np.meshgrid(grid_s,grid_s)
    query=np.c_[xx.ravel(),yy.ravel()]
    points=np.array([[.1,.12],[.84,.12],[.14,.82],[.82,.86],[.45,.45],[.35,.74]],dtype=float)
    def gp_predict(X,y,P):
        ell=.225; sigma=1.12; noise=.025
        dist2=np.sum((X[:,None,:]-X[None,:,:])**2,axis=2)
        K=sigma*sigma*np.exp(-dist2/(2*ell**2))+np.eye(len(X))*noise**2
        fac=cho_factor(K,lower=True,check_finite=False)
        cross=sigma*sigma*np.exp(-np.sum((P[:,None,:]-X[None,:,:])**2,axis=2)/(2*ell**2))
        mu=cross@cho_solve(fac,y,check_finite=False)
        var=np.maximum(sigma*sigma-np.sum(cross*cho_solve(fac,cross.T,check_finite=False).T,axis=1),1e-12)
        return mu,np.sqrt(var)
    trace=[]
    for j in range(10):
        yy0=objective(points)
        mean,std=gp_predict(points,yy0,query)
        best=float(np.max(yy0))
        Z=(mean-best-.008)/std
        EI=(mean-best-.008)*ndtr(Z)+std*np.exp(-.5*Z*Z)/np.sqrt(2*np.pi)
        EI[np.min(np.sum((query[:,None,:]-points[None,:,:])**2,axis=2),axis=1)<.009**2]=0
        next_point=query[int(np.argmax(EI))]
        trace.append(best)
        if j<9: points=np.vstack([points,next_point])
    allpoints=points.copy()
    yy0=objective(allpoints)
    mean,std=gp_predict(allpoints,yy0,query)
    Z=(mean-max(yy0)-.008)/std
    EI=(mean-max(yy0)-.008)*ndtr(Z)+std*np.exp(-.5*Z*Z)/np.sqrt(2*np.pi)
    next_point=query[int(np.argmax(EI))]
    return dict(t=t,truth=truth,observed=data,candidates=candidates,chi=chi,
                r=r,force=force,force_obs=fobs,train=train,fits=fits,
                costs=costs,n=n,successes=successes,rate=rate,lo=lo,hi=hi,optimal=optimal,
                gp_x=xx,gp_y=yy,gp_mu=mean.reshape(xx.shape),gp_std=std.reshape(xx.shape),
                gp_ei=EI.reshape(xx.shape),points=allpoints,point_values=yy0,next_point=next_point,
                trace=np.asarray(trace),true_optimum=max(objective(query)))


def base_ax(ax):
    ax.set_facecolor(BG); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():sp.set_visible(False)

def txt(ax,x,y,s,size=12,color=NAVY,weight='regular',ha='left',va='center',alpha=1):
    return ax.text(x,y,s,fontsize=size,color=color,weight=weight,ha=ha,va=va,alpha=alpha,transform=ax.transAxes)

def rounded(ax,xy,w,h,fill=PAPER,edge=GRID,r=.022,lw=.8):
    p=FancyBboxPatch(xy,w,h,boxstyle=f'round,pad=0.006,rounding_size={r}',fc=fill,ec=edge,lw=lw,transform=ax.transAxes);ax.add_patch(p);return p

def arrow(ax,a,b,color=COBALT,lw=1.5,rad=0):
    p=FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,lw=lw,color=color,connectionstyle=f'arc3,rad={rad}',transform=ax.transAxes);ax.add_patch(p)

def normalize_x(x,a,b,c,d):return c+(x-a)/(b-a)*(d-c)

def draw_reasoning(ax,d,kind=0,small=False):
    base_ax(ax)
    if kind==0:
        # Branching review based on actual simulated traces.
        title_sz=12 if small else 16
        if not small:txt(ax,.075,.935,'HYPOTHESIS  /  TEST  /  VERDICT',12,MUTE,'bold')
        rounded(ax,(.038,.35),.16,.27,fill='#EDF3F6',edge='#BCD0E1')
        xx=np.linspace(.06,.176,80);yy=.485+.048*np.cos(np.linspace(0,5*np.pi,80))*np.exp(-np.linspace(0,2.4,80))
        ax.plot(xx,yy,c=COBALT,lw=2.4,transform=ax.transAxes)
        if not small:txt(ax,.118,.378,'Observed',11,NAVY,'bold',ha='center')
        cc=['No damping','Damped','Strong damping']; ys=[.72,.46,.20]
        for j,(name,yy0) in enumerate(zip(cc,ys)):
            c=COPPER if j==1 else COBALT
            rounded(ax,(.35,yy0-.085),.41,.17,fill=PAPER,edge='#CDD6DB')
            arrow(ax,(.202,.485),(.342,yy0),c,lw=1.7,rad=(-.15 if j==0 else (.15 if j==2 else 0)))
            u=d['t']; obs=d['observed']; pred=d['candidates'][name]
            xxp=normalize_x(u,u.min(),u.max(),.385,.725)
            sf=.055/(1.05)
            ax.plot(xxp,yy0-.018+sf*.72*pred,color=c,lw=1.8,transform=ax.transAxes)
            ax.scatter(xxp[::7],yy0-.018+sf*.72*obs[::7],s=9,c=NAVY,alpha=.6,zorder=3,transform=ax.transAxes)
            if not small:txt(ax,.385,yy0+.060,name,10,NAVY,'bold')
            rounded(ax,(.815,yy0-.042),.12,.083,fill=('#F4E8DC' if j==1 else '#EDF3F6'),edge=('#DDAF8C' if j==1 else '#BCD0E1'))
            txt(ax,.875,yy0,'RETAIN' if j==1 else 'REJECT',8 if small else 11,COPPER if j==1 else COBALT,'bold',ha='center')
            arrow(ax,(.765,yy0),(.811,yy0),c,lw=1.3)
        if not small:txt(ax,.05,.052,'Toy damped oscillator · independent physical tests',10,MUTE)
    elif kind==1:
        t=d['t'];o=d['observed'];pred=d['candidates']
        ax.plot(t,pred['No damping'],color=BLUE,ls='--',lw=1.9,alpha=.75)
        ax.plot(t,pred['Damped'],color=COPPER,lw=2.9)
        ax.scatter(t[::4],o[::4],s=12,color=NAVY,alpha=.75)
        ax.set_xlim(0,7.5);ax.set_ylim(-1.18,1.18);ax.axis('on')
        ax.spines[['top','right']].set_visible(False)
        ax.tick_params(labelsize=8,colors=MUTE)
        ax.set_xlabel('time',fontsize=9,color=NAVY)
    else:
        names=['Energy','Boundary','Residual','Units'];values=[.04,.02,.11,.01]
        for j,(n,v) in enumerate(zip(names,values)):
            y=.79-j*.19
            txt(ax,.08,y,n,12,NAVY)
            ax.plot([.38,.88],[y,y],color=GRID,lw=8,solid_capstyle='round')
            ax.plot([.38,.38+(.5*(1-v))],[y,y],color=COBALT if j!=2 else COPPER,lw=8,solid_capstyle='round')
        txt(ax,.08,.09,'Constraint audit',11,MUTE,'bold')

def draw_discovery(ax,d,kind=0,small=False):
    base_ax(ax)
    if kind==0:
        xx=np.linspace(.16,.70,100);rr=np.linspace(d['r'].min(),d['r'].max(),100)
        yrange=(0,1.9);lower=.18;upper=.82
        # scale physically meaningful observation plot
        def yi(y):return lower+np.asarray(y)/yrange[1]*(upper-lower)
        ax.plot([.16,.16],[lower,upper],color=NAVY,lw=1.1)
        ax.plot([.16,.73],[lower,lower],color=NAVY,lw=1.1)
        for p in [1,3,2]:
            f=d['fits'][str(p)];coef=f['coefficient']
            ax.plot(xx,yi(coef/rr**p),color=COPPER if p==2 else BLUE,lw=3 if p==2 else 1.5,ls='-' if p==2 else '--',alpha=1 if p==2 else .6,transform=ax.transAxes)
        ax.scatter(normalize_x(d['r'][d['train']],d['r'].min(),d['r'].max(),.16,.70),yi(d['force_obs'][d['train']]),s=19,c=COBALT,zorder=4,alpha=.75,transform=ax.transAxes)
        ax.scatter(normalize_x(d['r'][~d['train']],d['r'].min(),d['r'].max(),.16,.70),yi(d['force_obs'][~d['train']]),s=20,facecolors=BG,edgecolors=NAVY,zorder=5,linewidths=.85,transform=ax.transAxes)
        if not small:
            txt(ax,.17,.90,'OBSERVED  →  CANDIDATE LAWS',12,MUTE,'bold')
            txt(ax,.41,.095,'distance  r',11,NAVY,ha='center')
            txt(ax,.055,.57,'force',11,NAVY,ha='center')
            txt(ax,.77,.74,'F ∝ 1/r',12,BLUE)
            txt(ax,.77,.57,'F ∝ 1/r²',13,COPPER,'bold')
            txt(ax,.77,.40,'F ∝ 1/r³',12,BLUE)
            txt(ax,.77,.23,'held-out fit',10,MUTE)
            txt(ax,.77,.17,'not a proof',10,MUTE)
        else: txt(ax,.78,.53,'1/r²',16,COPPER,'bold')
    elif kind==1:
        names=['1','r','r²','1/r','1/r²','1/r³'];values=[.015,.05,.04,.16,.89,.14]
        for j,(name,v) in enumerate(zip(names,values)):
            x=.12+j*.13
            ax.bar(x,v*.73,width=.083,bottom=.13,color=COPPER if j==4 else SOFT,edgecolor=COBALT if j==4 else 'none')
            txt(ax,x+.04,.082,name,10,NAVY,ha='center')
        txt(ax,.11,.93,'Sparse physical terms',11,MUTE,'bold')
    else:
        x=np.linspace(.6,1.7,170);y=np.linspace(1.2,3.1,155);xx,yy=np.meshgrid(x,y)
        zz=np.exp(-((xx-1.35)**2/.022+(yy-2.12)**2/.10))
        ux=.10+.79*(xx-.6)/1.1;uy=.16+.68*(yy-1.2)/1.9
        ax.contourf(ux,uy,zz,levels=12,cmap=mcolors.LinearSegmentedColormap.from_list('pf',[BG,SOFT,COBALT]),transform=ax.transAxes)
        ax.contour(ux,uy,zz,levels=[.2,.5,.8],colors=COPPER,linewidths=[.6,.8,1.1],transform=ax.transAxes)
        ax.axis('off')
        txt(ax,.08,.07,'Parameter uncertainty',12,NAVY,'bold')

def draw_benchmark(ax,d,kind=0,small=False):
    base_ax(ax)
    if kind==0:
        cost=d['costs'];score=d['rate'];lo=d['lo'];hi=d['hi'];opt=d['optimal']
        mx=7;my=.92
        X=normalize_x(cost,0,mx,.14,.88);Y=normalize_x(score,0,my,.16,.82)
        #Pareto envelope: sorted efficient points, non-dominated ascending cost
        idx=np.where(opt)[0];idx=idx[np.argsort(cost[idx])]
        ax.plot(X[idx],Y[idx],color=COPPER,lw=2.2,alpha=.8,ls='--',transform=ax.transAxes)
        for i in range(len(cost)):
            yy1=normalize_x(lo[i],0,my,.16,.82);yy2=normalize_x(hi[i],0,my,.16,.82)
            clr=COPPER if opt[i] else COBALT
            ax.plot([X[i],X[i]],[yy1,yy2],color=clr,lw=1.2,alpha=.8,transform=ax.transAxes)
            ax.plot([X[i]-.011,X[i]+.011],[yy1,yy1],color=clr,lw=1,transform=ax.transAxes)
            ax.plot([X[i]-.011,X[i]+.011],[yy2,yy2],color=clr,lw=1,transform=ax.transAxes)
            ax.scatter([X[i]],[Y[i]],s=105 if opt[i] else 70,c=clr,edgecolors=PAPER,linewidths=1.2,zorder=5,transform=ax.transAxes)
        ax.plot([.14,.14],[.16,.85],color=NAVY,lw=1.25,transform=ax.transAxes)
        ax.plot([.14,.90],[.16,.16],color=NAVY,lw=1.25,transform=ax.transAxes)
        if not small:
            txt(ax,.12,.93,'ACCURACY  ×  COST',12,MUTE,'bold')
            txt(ax,.52,.085,'Cost per task',11,NAVY,ha='center')
            txt(ax,.12,.86,'Score',10,NAVY)
            txt(ax,.66,.77,'Pareto front',12,COPPER,'bold')
            txt(ax,.68,.32,'95% Wilson CI',10,MUTE)
            txt(ax,.16,.05,'Illustrative simulated runs · no real LLM evaluated',9,MUTE)
    elif kind==1:
        # illustrative failure taxonomy counts, not a real benchmark
        mat=np.array([[.75,.2,.4,.1,.32],[.4,.7,.2,.6,.38],[.25,.4,.8,.2,.48],[.32,.18,.4,.76,.53]])
        ax.imshow(mat,cmap=mcolors.LinearSegmentedColormap.from_list('hm',[BG,SOFT,COBALT]),vmin=0,vmax=1,extent=(.12,.89,.14,.84),aspect='auto')
        for x in np.linspace(.12,.89,6):ax.plot([x,x],[.14,.84],c=BG,lw=2)
        for y in np.linspace(.14,.84,5):ax.plot([.12,.89],[y,y],c=BG,lw=2)
        txt(ax,.11,.95,'Failure taxonomy',11,MUTE,'bold')
        txt(ax,.15,.08,'Reasoning     Code     Evidence',9,NAVY)
    else:
        xx=np.arange(1,19)
        for j,(a,b) in enumerate([(.55,2.8),(.70,4.2),(.48,1.5)]):
            yy=a*(1-np.exp(-xx/b))
            ax.plot(.14+.70*(xx-1)/17,.16+yy*.76,color=[COBALT,COPPER,BLUE][j],lw=2.1,transform=ax.transAxes)
        txt(ax,.11,.94,'Sample efficiency',11,MUTE,'bold')
        txt(ax,.34,.08,'Experiments run',10,NAVY)

def draw_research(ax,d,kind=0,small=False):
    base_ax(ax)
    if kind==0:
        xx=d['gp_x']; yy=d['gp_y']; z=d['gp_mu']
        cmap=mcolors.LinearSegmentedColormap.from_list('field',[BG,'#E2EBF0',SOFT,BLUE,COBALT,'#E0B392',COPPER])
        # map numerical area onto panel
        trans=lambda v:.10+.70*v
        ux=trans(xx);uy=.15+.70*yy
        ax.contourf(ux,uy,z,levels=16,cmap=cmap,alpha=.91,transform=ax.transAxes)
        ax.contour(ux,uy,z,levels=11,colors=NAVY,linewidths=.44,alpha=.36,transform=ax.transAxes)
        pt=d['points'];px=trans(pt[:,0]);py=.15+.70*pt[:,1]
        ax.plot(px[-6:],py[-6:],color=PAPER,lw=1.45,alpha=.65,transform=ax.transAxes,zorder=5)
        ax.scatter(px,py,s=39,c=PAPER,edgecolors=COBALT,lw=1.7,transform=ax.transAxes,zorder=6)
        if not small:
            txt(ax,.085,.935,'SEQUENTIAL EXPERIMENTS',12,MUTE,'bold')
            rounded(ax,(.83,.62),.13,.12,fill=PAPER,edge=GRID)
            txt(ax,.895,.682,'OBSERVE',8,COBALT,'bold',ha='center')
            rounded(ax,(.83,.44),.13,.12,fill=PAPER,edge=GRID)
            txt(ax,.895,.502,'UPDATE',8,COBALT,'bold',ha='center')
            rounded(ax,(.83,.26),.13,.12,fill=PAPER,edge=GRID)
            txt(ax,.895,.322,'SELECT',8,COPPER,'bold',ha='center')
            arrow(ax,(.896,.607),(.896,.569),color=COPPER)
            arrow(ax,(.896,.427),(.896,.389),color=COPPER)
            txt(ax,.43,.085,'GP posterior mean · synthetic search surface',9,MUTE,ha='center')
        # next suggested point from EI
        nxt=d['next_point'];ax.scatter([trans(nxt[0])],[.15+.70*nxt[1]],s=180,facecolors='none',edgecolors=COPPER,lw=2.6,zorder=8,transform=ax.transAxes)
    elif kind==1:
        points=[(.5,.80),(.83,.57),(.74,.21),(.25,.21),(.17,.57)]
        names=['Question','Choose','Run','Analyze','Check']
        for i,p in enumerate(points):
            rounded(ax,(p[0]-.095,p[1]-.058),.19,.11,fill=PAPER,edge=SOFT)
            txt(ax,*p,names[i],9,NAVY,'bold',ha='center')
            arrow(ax,(p[0]+.047,p[1]-.061),(points[(i+1)%5][0],points[(i+1)%5][1]+.06),color=COPPER,rad=.1)
        txt(ax,.16,.95,'Closed-loop research',11,MUTE,'bold')
    else:
        v=d['trace'];x=np.arange(1,len(v)+1);x1=.13+.75*(x-1)/(len(x)-1); y1=.18+.65*(v-v.min()+.05)/(1.2-v.min()+.1)
        ax.step(x1,y1,where='post',lw=2.7,c=COPPER,transform=ax.transAxes)
        ax.scatter(x1,y1,s=31,c=COBALT,zorder=3,transform=ax.transAxes)
        ax.plot([.13,.9],[.18,.18],lw=1,color=NAVY,transform=ax.transAxes)
        txt(ax,.12,.93,'Best observed result',11,MUTE,'bold')
        txt(ax,.35,.09,'Experiment budget',10,NAVY)

ROWS=[('Reasoning & scientific agents',draw_reasoning,['Hypotheses & falsification','Simulated model check','Physical constraint audit']),
      ('Scientific law discovery',draw_discovery,['Competing physical laws','Sparse equation terms','Parameter inference']),
      ('Physics agent benchmarking',draw_benchmark,['Cost–accuracy Pareto','Failure-mode heatmap','Sample efficiency']),
      ('Autonomous research',draw_research,['Adaptive search landscape','Closed research loop','Best result vs budget'])]

def setup_figure(ax,face=BG):base_ax(ax)

def render_board(d,out):
    fig,axs=plt.subplots(4,3,figsize=(16,18.6),facecolor=BG)
    fig.subplots_adjust(left=.065,right=.984,top=.900,bottom=.058,wspace=.18,hspace=.42)
    fig.text(.065,.992,'PART B  /  TWELVE VISUAL DIRECTIONS',fontsize=23,fontfamily='DejaVu Serif',color=NAVY,weight='bold',va='top')
    fig.text(.066,.961,'Research-informed concepts • synthetic / simulated data • warm scientific atelier',fontsize=10,color=MUTE,va='top')
    for i,(rowname,draw,opts) in enumerate(ROWS):
        for j in range(3):
            ax=axs[i,j]
            draw(ax,d,j,small=True)
            for spine in ax.spines.values(): spine.set_visible(False)
            ax.text(0,-.10,f'{j+1:02d}  {opts[j]}',color=NAVY,fontsize=11,weight='bold',ha='left',va='top',transform=ax.transAxes)
            if j==0:
                ax.text(0,1.095,f'{i+1:02d}  {rowname}',color=COPPER,fontsize=12,weight='bold',transform=ax.transAxes,va='bottom')
                ax.text(.98,1.095,'SELECTED',color=COPPER,fontsize=9,weight='bold',transform=ax.transAxes,va='bottom',ha='right')
            ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle='round,pad=0.002',facecolor='none',edgecolor=('#DCAB90' if j==0 else GRID),lw=1.4 if j==0 else .75,transform=ax.transAxes,clip_on=False))
    path=out/'part_b_4x3_option_board.png'
    fig.savefig(path,dpi=170,facecolor=BG)
    plt.close(fig)
    return path

def crop_card_master(d,draw,out,slug):
    fig=plt.figure(figsize=(4,3),facecolor=BG)
    ax=fig.add_axes([.015,.015,.97,.97]);draw(ax,d,0,small=True)
    for s in ax.spines.values():s.set_visible(False)
    fig.savefig(out/f'{slug}_atlas_card_master.png',dpi=400,facecolor=BG)
    plt.close(fig)

def render_single(d,draw,out,slug,title,subtitle):
    fig=plt.figure(figsize=(8,6),facecolor=BG)
    ax=fig.add_axes([.065,.135,.87,.76]);draw(ax,d,0,small=False)
    # Header and footer kept outside the scientific panel
    fig.text(.075,.965,title,color=NAVY,fontsize=20,fontfamily='DejaVu Serif',weight='bold',va='top')
    fig.text(.075,.921,subtitle,color=MUTE,fontsize=9.5,va='top')
    fig.text(.075,.038,'PHYSICS BY CONSTRUCTION   /   PART B',fontsize=9,color=MUTE,weight='bold')
    fig.text(.925,.038,'MODEL-BASED EXAMPLE  ·  NOT AGENT MEASUREMENTS',fontsize=7.6,color=MUTE,ha='right')
    fig.savefig(out/f'{slug}.png',dpi=300,facecolor=BG)
    fig.savefig(out/f'{slug}.svg',format='svg',facecolor=BG)
    plt.close(fig)
    im=Image.open(out/f'{slug}.png').convert('RGB')
    im.save(out/f'{slug}.webp',format='WEBP',quality=91,method=6)
    im.resize((800,600),Image.Resampling.LANCZOS).save(out/f'{slug}_atlas_panel.png')
    im.resize((200,150),Image.Resampling.LANCZOS).save(out/f'{slug}_atlas_panel_200px.png')
    crop_card_master(d,draw,out,slug)
    # Actual card uses illustration only, not long captions unreadable at 76px
    master=Image.open(out/f'{slug}_atlas_card_master.png').convert('RGB')
    master.resize((76,57),Image.Resampling.LANCZOS).save(out/f'{slug}_atlas_card_76px.png')
    # square is center crop, preserves major geometry
    side=min(master.size);dx=(master.width-side)//2;dy=(master.height-side)//2
    master.crop((dx,dy,dx+side,dy+side)).resize((76,76),Image.Resampling.LANCZOS).save(out/f'{slug}_atlas_card_76px_square.png')
    master.resize((608,456),Image.Resampling.LANCZOS).save(out/f'{slug}_atlas_card_preview_8x.png')

def validate(d):
    # Damped harmonic motion: numeric integration against exact closed-form
    t=d['t'];g=.24;w0=2*np.pi*.72;wd=np.sqrt(w0**2-g**2)
    exact=np.exp(-g*t)*(np.cos(wd*t)+g/wd*np.sin(wd*t))
    err=float(np.max(np.abs(exact-d['truth'])))
    assert err<1e-8
    assert min(d['chi'],key=d['chi'].get)=='Damped'
    # inverse-square power law selected on heldout, with effective independent noise
    best=min(d['fits'],key=lambda p:d['fits'][p]['heldout_rmse'])
    assert best=='2'
    # Wilson coverage and nondominated frontier as computed
    assert np.all(d['lo']<=d['rate']) and np.all(d['rate']<=d['hi'])
    assert d['optimal'].sum()>=2
    # BO objective measured values from deterministic known toy function, all domain bounded
    assert np.all((d['points']>=0)&(d['points']<=1))
    assert np.all(np.diff(d['trace'])>=-1e-10)
    assert np.isfinite(d['gp_mu']).all() and np.isfinite(d['gp_ei']).all()
    assert np.min(d['gp_std'])>0
    return {'physics_reasoning':{'model':'damped harmonic oscillator','reference_max_absolute_error':err,'normalized_mean_squared_residuals':d['chi'],'selected_hypothesis':'Damped'},
    'law_discovery':{'model':'synthetic 1/r^2 force observations','heldout_rmse_by_power':{k:v['heldout_rmse'] for k,v in d['fits'].items()},'selected_exponent':int(best)},
    'agent_benchmarking':{'model':'synthetic binomial successes, not real LLM evaluations','sample_size_per_configuration':int(d['n']),'frontier_count':int(d['optimal'].sum()),'successes':d['successes'].tolist(),'wilson_interval_verified':True},
    'autonomous_research':{'model':'synthetic 2D response surface with Gaussian process Bayesian optimisation','observed_points':int(len(d['points'])),'best_observed_response':float(max(d['point_values'])),'best_on_heldout_grid':float(d['true_optimum']),'nondecreasing_best_so_far':True,'positive_posterior_variance':True},
    'all_outputs':'synthetic/model-generated; no live agents, no laboratory measurements'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(Path(__file__).resolve().parent));args=ap.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    d=make_data();valid=validate(d)
    render_board(d,out)
    names=[('reasoning',ROWS[0][1],'Scientific reasoning','Hypotheses, experiments and falsification'),
      ('law_discovery',ROWS[1][1],'Scientific law discovery','Testing inverse-power laws against synthetic measurements'),
      ('benchmarking',ROWS[2][1],'Agent benchmarking','Illustrative cost–accuracy Pareto frontier with uncertainty'),
      ('autonomous_research',ROWS[3][1],'Autonomous scientific research','Gaussian-process-guided experiments on a synthetic response surface')]
    for slug,draw,title,subtitle in names:render_single(d,draw,out,f'pbc_part_b_{slug}',title,subtitle)
    with (out/'validation.json').open('w') as f:json.dump(valid,f,indent=2)
    np.savez_compressed(out/'simulation_data.npz',t=d['t'],oscillator=d['truth'],oscillator_observed=d['observed'],force_distance=d['r'],force_obs=d['force_obs'],train=d['train'],benchmark_costs=d['costs'],benchmark_successes=d['successes'],benchmark_lo=d['lo'],benchmark_hi=d['hi'],benchmark_frontier=d['optimal'],gp_mu=d['gp_mu'],gp_std=d['gp_std'],gp_ei=d['gp_ei'],bo_points=d['points'],bo_values=d['point_values'],bo_trace=d['trace'])
    print(json.dumps(valid,indent=2))
if __name__=='__main__':main()
