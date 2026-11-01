#!/usr/bin/env python3
"""Scientifically reproducible PBC Course Atlas illustration: odd Schrödinger-cat Wigner function.

Required: numpy, scipy, matplotlib, Pillow.

In dimensionless oscillator quadratures [x, p] = i and alpha real:
    |cat_-(alpha)> = N (|alpha> - |-alpha>),
    N = (2(1-exp(-2alpha**2)))**(-1/2)

Wigner function (normalized so integral W dx dp = 1):
    W(x,p) = N**2/pi * (exp(-(x-sqrt(2)*alpha)**2-p**2)
                         + exp(-(x+sqrt(2)*alpha)**2-p**2)
                         - 2 exp(-x**2-p**2) cos(2 sqrt(2)*alpha*p)).

Positive W: blue. Negative W: copper. This is a quasiprobability, not an image
of a physical density in ordinary space. The plotting overlay adds only
iso-value curves of W, not invented simulation traces.
"""

from pathlib import Path
import json
import numpy as np
from scipy.integrate import simpson
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from PIL import Image

HERE = Path(__file__).resolve().parent
BG = '#FAF8F3'
ALPHA = 2.0
SQ2 = np.sqrt(2.0)
N2 = 1.0 / (2.0 * (1.0 - np.exp(-2.0 * ALPHA**2)))
DISPLACEMENT = SQ2 * ALPHA
FRINGE_FREQ = 2.0 * SQ2 * ALPHA


def wigner(x, p):
    """Return Wigner quasiprobability density for odd cat; supports ndarray broadcasting."""
    x, p = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(p, dtype=float))
    common = np.exp(-p * p)
    return N2 / np.pi * common * (
        np.exp(-(x-DISPLACEMENT)**2)
        + np.exp(-(x+DISPLACEMENT)**2)
        - 2.0*np.exp(-x*x) * np.cos(FRINGE_FREQ*p)
    )


def checks():
    # Wide integration domain avoids image cropping bias.
    x = np.linspace(-7., 7., 1601)
    p = np.linspace(-6., 6., 1401)
    X, P = np.meshgrid(x, p)
    W = wigner(X, P)
    norm = float(simpson(simpson(W, x=x, axis=1), x=p))
    parity_at_origin = float(wigner(0., 0.))
    min_wigner = float(W.min())
    # Analytic marginal: position probability density |psi(x)|^2 for odd cat.
    marginal_x = simpson(W, x=p, axis=0)
    analytic_x = N2 / np.sqrt(np.pi) * (
        np.exp(-(x-DISPLACEMENT)**2)
        + np.exp(-(x+DISPLACEMENT)**2)
        - 2.0 * np.exp(-x*x-DISPLACEMENT**2)
    )
    mx_err = float(np.max(np.abs(marginal_x - analytic_x)))
    # Analytic marginal: momentum probability density |psi(p)|^2.
    marginal_p = simpson(W, x=x, axis=1)
    analytic_p = 2.0*N2 / np.sqrt(np.pi) * np.exp(-p*p) * (1.0-np.cos(FRINGE_FREQ*p))
    mp_err = float(np.max(np.abs(marginal_p - analytic_p)))
    neg_vol = float(simpson(simpson(np.maximum(-W, 0.), x=x, axis=1), x=p))
    assert abs(norm - 1.) < 1e-7, f'W normalization failed: {norm}'
    assert abs(parity_at_origin + 1./np.pi) < 1e-12, 'Odd-state parity failed'
    assert mx_err < 1e-7, f'x marginal failed: {mx_err}'
    assert mp_err < 1e-7, f'p marginal failed: {mp_err}'
    assert neg_vol > 0.15, 'Wigner negativity not present'
    report = {
        'state': 'normalized odd Schrodinger cat (|alpha> - |-alpha>)',
        'alpha_real': ALPHA, 'hbar': 1.0,
        'commutator': '[x,p]=i',
        'integrated_W': norm,
        'absolute_normalization_error': abs(norm - 1.),
        'W_at_origin': parity_at_origin,
        'expected_W_at_origin': -1/np.pi,
        'min_W_on_grid': min_wigner,
        'negative_volume_integral': neg_vol,
        'max_position_marginal_error': mx_err,
        'max_momentum_marginal_error': mp_err,
        'color_encoding': 'blue positive W; copper-orange negative W; paper is W approximately zero',
        'plot': 'no physical trajectories; only analytic W and its level sets'
    }
    (HERE/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return x, p, W


def plot_artwork():
    # x and p ranges approximately match the 4:3 aspect of the finished page.
    x = np.linspace(-5.5, 5.5, 1376)
    p = np.linspace(-4.125, 4.125, 1032)
    X,P = np.meshgrid(x,p)
    W = wigner(X,P)

    # Diverging blue/copper color system, with exact background at W=0.
    # Color values encode the SIGN of the quasiprobability as well as intensity.
    color_points = [
        (0.00, '#913918'), (0.14, '#B85A30'), (0.28, '#E99F6D'),
        (0.40, '#F6DDC9'), (0.485, BG), (0.50, BG), (0.515, BG),
        (0.60, '#D9E7F0'), (0.73, '#73AED2'), (0.85, '#276BAA'), (1.0, '#112E62'),
    ]
    cmap = LinearSegmentedColormap.from_list('pbc_wigner_blue_copper', color_points, N=512)
    norm = TwoSlopeNorm(vmin=-1/np.pi, vcenter=0, vmax=1/np.pi)

    fig = plt.figure(figsize=(12,9), dpi=200, facecolor=BG)
    ax = fig.add_axes([0.018,0.028,0.964,0.944], facecolor=BG)
    ax.imshow(W, extent=(x[0], x[-1], p[0], p[-1]), origin='lower', cmap=cmap,
              norm=norm, interpolation='bicubic', rasterized=True, zorder=1)
    # All decorative contours are genuine Wigner isocurves.
    negatives = [-0.24,-0.18,-0.13,-0.09,-0.06,-0.037,-0.020,-0.009]
    positives = [0.008,0.018,0.035,0.060,0.095,0.14,0.19,0.25]
    ax.contour(X, P, W, levels=negatives, colors=['#9E512F'], linewidths=.68, alpha=.39, zorder=2)
    ax.contour(X, P, W, levels=positives, colors=['#184D89'], linewidths=.68, alpha=.38, zorder=2)
    # One transparent node near the deep interference region? No: data only.
    ax.set(xlim=(-5.5,5.5), ylim=(-4.125,4.125))
    ax.set_aspect('equal')
    ax.axis('off')
    base = HERE/'pbc_quantum_physics_wigner_cat'
    fig.savefig(base.with_suffix('.png'), dpi=200, facecolor=BG, pad_inches=0)
    fig.savefig(base.with_suffix('.svg'), dpi=200, facecolor=BG, pad_inches=0)
    plt.close(fig)
    img = Image.open(base.with_suffix('.png')).convert('RGB')
    assert img.size==(2400,1800), img.size
    img.save(base.with_suffix('.webp'), format='WEBP', quality=94, method=6)

    # Panel: crop slightly closer but keep all 3 features (two lobes and fringes).
    # Rather than distorting, retain physical aspect ratio with central crop.
    panel=img.crop((96,110,2304,1690))
    panel.save(HERE/'pbc_quantum_physics_atlas_panel.png')
    card=img.crop((110,250,2290,1550)).resize((76,58), Image.Resampling.LANCZOS)
    card.save(HERE/'pbc_quantum_physics_atlas_card_76px.png')
    card.resize((760,580), Image.Resampling.NEAREST).save(HERE/'pbc_quantum_physics_atlas_card_enlarged.png')
    print('Generated:',base)


def plot_diagnostics(x,p,W):
    fig,ax=plt.subplots(1,2,figsize=(13,4.5),dpi=140)
    im=ax[0].imshow(W,extent=[x[0],x[-1],p[0],p[-1]],origin='lower',cmap='RdBu',
                    vmin=-1/np.pi,vmax=1/np.pi,aspect='auto')
    ax[0].set(xlabel='x (dimensionless quadrature)',ylabel='p (dimensionless quadrature)',
              title='Calculated odd-cat Wigner function (sign convention shown)')
    fig.colorbar(im,ax=ax[0],label='W(x,p)')
    margx=simpson(W,x=p,axis=0)
    analyticx=N2/np.sqrt(np.pi)*(np.exp(-(x-DISPLACEMENT)**2)+np.exp(-(x+DISPLACEMENT)**2)-2*np.exp(-x*x-DISPLACEMENT**2))
    ax[1].plot(x,margx,label='Wigner marginal',lw=2)
    ax[1].plot(x,analyticx,'--',label='Analytic |ψ(x)|²',lw=1.7)
    ax[1].set(xlabel='x',ylabel='Probability density',title='Position marginal validation')
    ax[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(HERE/'pbc_quantum_physics_diagnostic.png',facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    x,p,W=checks()
    plot_artwork()
    plot_diagnostics(x,p,W)
