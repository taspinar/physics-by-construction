"""Physics by Construction — reproducible double-pendulum atlas artwork.

This is calculated with the exact (non-small-angle) equations of motion for
an ideal planar double pendulum (two point masses, rigid massless rods, no
friction). Two initial conditions differ by only 2e-4 radians in theta_2.

Dependencies: numpy, scipy, matplotlib, pillow.
Usage: python double_pendulum_atlas.py

Produces the full-size visual, a 76-pixel atlas thumbnail, a 200-pixel atlas
panel, and an independently informative diagnostic chart.
"""
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from PIL import Image

HERE = Path(__file__).resolve().parent
G = 9.81
M1 = M2 = 1.0  # kg
L1 = L2 = 1.0  # m
T_END = 17.0  # seconds
DELTA_THETA_2 = 2e-4  # radians = 0.01146 degrees
SAMPLES = 3601
PAPER = '#FAF8F3'
COBALT = '#1255A5'
INK = '#172C43'
COPPER = '#BB532B'
STEEL = '#95AFC6'


def deriv(t, state):
    theta1, theta2, omega1, omega2 = state
    difference = theta1 - theta2
    s = np.sin(difference)
    c = np.cos(difference)
    denominator = 2*M1 + M2 - M2*np.cos(2*difference)
    alpha1 = (
        -G*(2*M1+M2)*np.sin(theta1)
        - M2*G*np.sin(theta1-2*theta2)
        - 2*s*M2*(omega2**2*L2 + omega1**2*L1*c)
    )/(L1*denominator)
    alpha2 = 2*s*(
        omega1**2*L1*(M1+M2)
        + G*(M1+M2)*np.cos(theta1)
        + omega2**2*L2*M2*c
    )/(L2*denominator)
    return np.array([omega1, omega2, alpha1, alpha2])


def mechanical_energy(states):
    th1, th2, w1, w2 = states
    kinetic = (
        0.5*(M1+M2)*L1**2*w1**2
        + 0.5*M2*L2**2*w2**2
        + M2*L1*L2*w1*w2*np.cos(th1-th2)
    )
    potential = -(M1+M2)*G*L1*np.cos(th1) - M2*G*L2*np.cos(th2)
    return kinetic + potential


def positions(states):
    t1, t2 = states[0], states[1]
    x1 = L1*np.sin(t1)
    y1 = -L1*np.cos(t1)
    x2 = x1 + L2*np.sin(t2)
    y2 = y1 - L2*np.cos(t2)
    return x1,y1,x2,y2


def solve(y0, time):
    res = solve_ivp(
        deriv, (time[0], time[-1]), y0, method='DOP853',
        rtol=2e-13, atol=2e-14, t_eval=time,
    )
    if not res.success:
        raise RuntimeError(res.message)
    return res.y


def segments(ax, x, y, color, width=1.7, alpha_low=0.024, alpha_high=0.63,
             stride=2, zorder=3):
    # Time is encoded only by transparency and stroke weight: older faint,
    # newer stronger. Coordinates themselves are exactly simulated.
    points = np.column_stack([x[::stride], y[::stride]])
    xy = np.stack([points[:-1],points[1:]], axis=1)
    num = len(xy)
    q = np.linspace(0,1,num)
    from matplotlib.colors import to_rgba
    rgba = np.empty((num,4))
    rgba[:,:3] = to_rgba(color)[:3]
    rgba[:,3] = alpha_low + (alpha_high-alpha_low)*q**2.3
    widths = width*(0.85+0.45*q**2)
    line = LineCollection(xy, colors=rgba, linewidths=widths,
                          capstyle='round', joinstyle='round', zorder=zorder)
    ax.add_collection(line)


def bob(ax, xy, radius, color, zorder=9, faint=False):
    x,y=xy
    # Painterly glows are cosmetic; the center is the computed bob position.
    if not faint:
        for mul, a in [(2.5,.026),(1.9,.045),(1.4,.065)]:
            ax.add_patch(Circle((x,y), radius*mul, facecolor=color,
                                edgecolor='none', alpha=a, zorder=zorder-2))
    ax.add_patch(Circle((x,y), radius, facecolor=color, edgecolor=PAPER,
                        linewidth=.7 if not faint else .4,
                        alpha=0.85 if faint else 1,zorder=zorder))
    if not faint:
        ax.add_patch(Circle((x-radius*.31,y+radius*.34), radius*.23,
                            facecolor='white', alpha=.2, edgecolor='none',zorder=zorder+1))


def draw_rods(ax, coords, color, ghost=False):
    x1,y1,x2,y2 = (float(p[-1]) for p in coords)
    a = .44 if ghost else 1.
    lw = 1.5 if ghost else 3.3
    ax.plot([0,x1,x2],[0,y1,y2], color=color, alpha=a,
            linewidth=lw, solid_capstyle='round', zorder=7 if ghost else 10)
    if not ghost:
        # Central fine highlight makes the rods legible on the trajectory field.
        ax.plot([0,x1,x2],[0,y1,y2],color=PAPER,alpha=.28,
                linewidth=.75, solid_capstyle='round',zorder=11)
    bob(ax,(x1,y1), .066 if not ghost else .048, color, zorder=12 if not ghost else 8,faint=ghost)
    bob(ax,(x2,y2), .095 if not ghost else .071,color,zorder=12 if not ghost else 8,faint=ghost)


def run():
    time = np.linspace(0,T_END,SAMPLES)
    y0 = np.array([np.deg2rad(120.0), np.deg2rad(-80.0), 0.0, 0.0])
    y1 = y0.copy()
    y1[1] += DELTA_THETA_2
    base = solve(y0,time)
    perturbed = solve(y1,time)
    p0 = positions(base)
    p1 = positions(perturbed)

    e0 = mechanical_energy(base)
    e1 = mechanical_energy(perturbed)
    drift0 = np.max(np.abs(e0-e0[0]))/max(abs(e0[0]),1)
    drift1 = np.max(np.abs(e1-e1[0]))/max(abs(e1[0]),1)
    l1_err = max(np.max(np.abs(np.hypot(p[0],p[1])-L1)) for p in [p0,p1])
    l2_err = max(np.max(np.abs(np.hypot(p[2]-p[0],p[3]-p[1])-L2)) for p in [p0,p1])
    distance = np.hypot(p0[2]-p1[2],p0[3]-p1[3])
    initial_distance=float(distance[0]); final_distance=float(distance[-1])
    # Compare against a tighter solve as an independent numerical convergence
    # check; chaos limits long-horizon pointwise agreement.
    r1 = solve_ivp(deriv,(0,T_END),y0,method='DOP853',rtol=5e-14,
                   atol=5e-15,t_eval=[T_END]);
    final_endpoint_error=float(np.linalg.norm(base[:,-1]-r1.y[:,-1]))

    assert drift0 < 1e-8 and drift1 < 1e-8, f'Energy drift {drift0}, {drift1}'
    assert l1_err < 1e-12 and l2_err < 1e-12
    assert final_distance > .6 and initial_distance < .001
    assert final_endpoint_error < 2e-5

    fig = plt.figure(figsize=(12,9), facecolor=PAPER)
    ax=fig.add_axes([.035,.035,.93,.93]);ax.set_facecolor(PAPER)
    ax.set_xlim(-2.55,2.55);ax.set_ylim(-2.32,1.47)
    ax.set_aspect('equal',adjustable='box');ax.axis('off')

    # Faint construction arcs: reference circles and a tiny pivot halo.
    ax.add_patch(Circle((0,0),1,fill=False,edgecolor=STEEL,alpha=.18,
                        linewidth=.7,linestyle=(0,(1.7,5.5)),zorder=1))
    ax.add_patch(Circle((0,0),2,fill=False,edgecolor=STEEL,alpha=.12,
                        linewidth=.6,linestyle=(0,(1,8)),zorder=1))
    ax.plot([0,0],[-2.15,1.20],color=STEEL,linewidth=.65,alpha=.10,zorder=1)
    ax.plot([-2.3,2.3],[0,0],color=STEEL,linewidth=.65,alpha=.08,zorder=1)

    # First bob is restricted to a circle of radius L1 (faint paths).
    segments(ax,p0[0],p0[1],COBALT,width=.9,alpha_low=.006,alpha_high=.20,zorder=2)
    segments(ax,p1[0],p1[1],COPPER,width=.9,alpha_low=.006,alpha_high=.21,zorder=2)

    # Lower-bob trajectories from nearly identical initial conditions.
    # The separation is genuinely caused by chaotic dynamics.
    segments(ax,p1[2],p1[3],COPPER,width=1.40,alpha_low=.015,alpha_high=.51,zorder=4)
    segments(ax,p0[2],p0[3],COBALT,width=1.50,alpha_low=.018,alpha_high=.57,zorder=5)

    # Highlight the final trajectory segment: never extrapolate beyond the run.
    last=np.searchsorted(time,T_END-0.23)
    ax.plot(p1[2][last:],p1[3][last:],color=COPPER,alpha=.92,lw=2.3,
            zorder=6,solid_capstyle='round')
    ax.plot(p0[2][last:],p0[3][last:],color=COBALT,alpha=.98,lw=2.5,
            zorder=6,solid_capstyle='round')

    # Same physical time for both illustrated configurations.
    draw_rods(ax,p1,COPPER,ghost=True)
    draw_rods(ax,p0,COBALT,ghost=False)
    bob(ax,(0,0),.052,INK,zorder=14)
    fig.savefig(HERE/'pbc_classical_mechanics_double_pendulum.png',dpi=240,
                facecolor=PAPER,pad_inches=0)
    fig.savefig(HERE/'pbc_classical_mechanics_double_pendulum.svg',
                facecolor=PAPER,pad_inches=0)
    plt.close(fig)

    main=Image.open(HERE/'pbc_classical_mechanics_double_pendulum.png').convert('RGB')
    main.save(HERE/'pbc_classical_mechanics_double_pendulum.webp',format='WEBP',quality=91,method=6)
    # Produce a purpose-built 76-px crop centered on the two real slingers,
    # rather than shrinking the entire composition. No data are recomputed.
    # Crop coordinates are in the full-size PNG's 2880x2160 raster grid.
    cx,cy=1500,1265
    w,h=1690,1267
    box=(int(cx-w/2),int(cy-h/2),int(cx+w/2),int(cy+h/2))
    detail=main.crop(box)
    detail.save(HERE/'pbc_classical_mechanics_atlas_card_detail.png')
    from PIL import ImageEnhance
    card=detail.resize((76,57),Image.Resampling.LANCZOS)
    card=ImageEnhance.Contrast(card).enhance(1.16)
    card.save(HERE/'pbc_classical_mechanics_atlas_card_76px.png')
    main.resize((800,600),Image.Resampling.LANCZOS).save(
        HERE/'pbc_classical_mechanics_atlas_panel.png')
    np.savez_compressed(HERE/'double_pendulum_simulation.npz',
                        t=time, initial_a=y0, initial_b=y1,
                        states_a=base,states_b=perturbed,
                        bob1_a=np.stack(p0[:2]), bob2_a=np.stack(p0[2:]),
                        bob1_b=np.stack(p1[:2]), bob2_b=np.stack(p1[2:]),
                        lower_bob_distance=distance)

    fig,ax=plt.subplots(figsize=(10,4.4),facecolor=PAPER)
    ax.set_facecolor(PAPER)
    ax.semilogy(time,np.maximum(distance,1e-6),color=COBALT,lw=1.75)
    ax.axhline(1,color=COPPER,ls='--',lw=.9,alpha=.50)
    ax.set(xlabel='Time (s)',ylabel='Separation between lower bobs (m)',
           title='Sensitivity to initial conditions: $\\Delta\\theta_2=2\\times10^{-4}$ rad')
    ax.grid(alpha=.15)
    for side in ('top','right'):ax.spines[side].set_visible(False)
    fig.tight_layout();fig.savefig(HERE/'pbc_classical_mechanics_diagnostic.png',dpi=190,
                                   facecolor=PAPER)
    plt.close(fig)

    txt=(f'Double pendulum PBC visualization — validated numerical integration\n'
         f'Model: ideal planar, point masses on massless rigid rods; g={G} m/s².\n'
         f'Parameters: m1=m2={M1} kg; L1=L2={L1} m; no drag.\n'
         f'Initial condition A: theta1=120°, theta2=-80°, omega1=omega2=0 rad/s.\n'
         f'Initial condition B: theta1=120°, theta2=-80°+{DELTA_THETA_2}rad, omega1=omega2=0 rad/s.\n'
         f'Duration: {T_END} s; solver: DOP853; rtol=2e-13 atol=2e-14.\n'
         f'Energy drift A (relative to |E(0)|): {drift0:.3e}\n'
         f'Energy drift B (relative to |E(0)|): {drift1:.3e}\n'
         f'Max rod-length error: first {l1_err:.3e} m; second {l2_err:.3e} m.\n'
         f'Lower-bob separation: at t=0, {initial_distance:.6f} m; at t={T_END}s, {final_distance:.4f} m.\n'
         f'Endpoint convergence vs tighter integrator: {final_endpoint_error:.3e} (state norm).\n'
         f'Colors: cobalt=original initial condition; copper=perturbed.\n'
         f'Faint arcs and gradients are design-only; no trajectory point is invented.\n'
         f'The lines and current rods are obtained from the very same simulation data.\n'
         f'No closed-form chaos/Lyapunov exponent is inferred from this finite run.\n')
    (HERE/'VALIDATION.txt').write_text(txt,encoding='utf8')
    print(txt)

if __name__=='__main__':run()
