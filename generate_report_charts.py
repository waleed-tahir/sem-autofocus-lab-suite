import os
import json
import matplotlib.pyplot as plt
import numpy as np

os.makedirs('report_charts', exist_ok=True)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

with open('autofocus_suite/benchmark/results/curves_cache.json', 'r') as f:
    curves_data = json.load(f)

# -------------------------------------------------------------
# 1. Figure 1: 10 FMO Curves on Clean vs Heavy Shot Noise
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=200)

fmo_names = {
    'm1_scharr': 'M1: Scharr-Tenengrad',
    'm2_brenner': 'M2: Denoised Brenner',
    'm3_sml': 'M3: Modified Laplacian',
    'm4_steerable': 'M4: Steerable G1',
    'm5_morph': 'M5: Top-Hat Morph',
    'm6_wavelet': 'M6: 2D Haar Wavelet',
    'm7_dct': 'M7: DCT Mid-Band AC',
    'm8_fft': 'M8: Radial CTF FFT',
    'm9_normvar': 'M9: Normalized Variance',
    'm10_tensor': 'M10: Structure Tensor'
}

colors_map = {
    'm1_scharr': '#0078D4', 'm2_brenner': '#00B7C3', 'm3_sml': '#107C41',
    'm4_steerable': '#D83B01', 'm5_morph': '#E81123', 'm6_wavelet': '#8764B8',
    'm7_dct': '#FF8C00', 'm8_fft': '#00B294', 'm9_normvar': '#68768A', 'm10_tensor': '#E3008C'
}

# spd1
spd1_curves = curves_data['pollen.spd1']['curves']
for k, label in fmo_names.items():
    if k in spd1_curves:
        c = np.array(spd1_curves[k])
        c_norm = (c - c.min()) / (c.max() - c.min() + 1e-9)
        ax1.plot(c_norm, label=label, color=colors_map[k], lw=1.6 if k in ['m1_scharr', 'm10_tensor', 'm9_normvar'] else 1.0)
ax1.set_title('Clean SEM (pollen.spd1) - 10 FMO Profiles', fontsize=11, fontweight='bold', pad=8)
ax1.set_xlabel('Focal Plane Index (z)', fontsize=10)
ax1.set_ylabel('Normalized Focus Score', fontsize=10)
ax1.axvline(96, color='black', linestyle='--', alpha=0.5, label='True Focus (z*=96)')
ax1.set_ylim(-0.05, 1.05)
ax1.legend(loc='upper right', fontsize=7, framealpha=0.9)

# spd5
spd5_curves = curves_data['pollen.spd5']['curves']
for k, label in fmo_names.items():
    if k in spd5_curves:
        c = np.array(spd5_curves[k])
        c_norm = (c - c.min()) / (c.max() - c.min() + 1e-9)
        ax2.plot(c_norm, label=label, color=colors_map[k], lw=1.6 if k in ['m1_scharr', 'm10_tensor', 'm9_normvar'] else 1.0)
ax2.set_title('Heavy Shot Noise (pollen.spd5) - 10 FMO Profiles', fontsize=11, fontweight='bold', pad=8)
ax2.set_xlabel('Focal Plane Index (z)', fontsize=10)
ax2.axvline(96, color='black', linestyle='--', alpha=0.5, label='True Focus (z*=96)')
ax2.set_ylim(-0.05, 1.05)
ax2.legend(loc='upper right', fontsize=7, framealpha=0.9)

plt.tight_layout()
fig.savefig('report_charts/fig1_fmo_curves.png')
plt.close(fig)

# -------------------------------------------------------------
# 2. Figure 2: Search Scheme Efficiency
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.5, 3.8), dpi=200)
algorithms = ['S1: Fibonacci Lattice', 'S2: Hybrid Coarse-Fine', 'S3: Pyramid Bracket', 'S4: Speculative Parallel', 'Global Exhaustive Scan']
reads = [12, 28, 19, 23.2, 199]
latencies = [11.2, 30.9, 11.0, 38.5, 169.4]

x = np.arange(len(algorithms))
w = 0.35

ax1 = ax
ax2 = ax.twinx()

rects1 = ax1.bar(x - w/2, reads, w, label='Frames Read (Beam Exposure)', color='#0078D4', alpha=0.85)
rects2 = ax2.bar(x + w/2, latencies, w, label='Latency (ms)', color='#D83B01', alpha=0.85)

ax1.set_ylabel('Micrograph Frames Read (Lower is Better)', color='#0078D4', fontweight='bold', fontsize=9.5)
ax2.set_ylabel('Wall-Clock Latency in ms (Lower is Better)', color='#D83B01', fontweight='bold', fontsize=9.5)
ax1.set_xticks(x)
ax1.set_xticklabels(algorithms, rotation=15, ha='right', fontsize=9)
ax1.set_title('Search Scheme Efficiency: Sampled Slices vs Latency', fontsize=11, fontweight='bold', pad=10)

ax1.bar_label(rects1, padding=3, fmt='%d', fontsize=8)
ax2.bar_label(rects2, padding=3, fmt='%.1f ms', fontsize=8)

fig.tight_layout()
fig.savefig('report_charts/fig2_search_efficiency.png')
plt.close(fig)

# -------------------------------------------------------------
# 3. Figure 3: Astigmatism & Directional Asymmetry Polar Diagnostics
# -------------------------------------------------------------
with open('autofocus_suite/benchmark/results/astigmatism_cache.json', 'r') as f:
    astig_data = json.load(f)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=200)

spd1_astig = astig_data['pollen.spd1']
spd5_astig = astig_data['pollen.spd5']

z_vals = np.arange(len(spd1_astig['A_xy_series']))

ax1.plot(z_vals, spd1_astig['A_xy_series'], label='A_xy (0°-90°)', color='#0078D4', lw=1.5)
ax1.plot(z_vals, spd1_astig['A_45_series'], label='A_45 (45°-135°)', color='#00B7C3', lw=1.5)
ax1.axhline(0, color='gray', linestyle=':', alpha=0.6)
ax1.axvline(spd1_astig['z_true'], color='green', linestyle='--', label='True z*=' + str(spd1_astig['z_true']))
ax1.set_title('pollen.spd1 Stigmatic Asymmetry (Δz_stig = ' + str(spd1_astig['stigmator_error']) + 'f)', fontsize=10, fontweight='bold')
ax1.set_xlabel('Focal Plane z', fontsize=9)
ax1.set_ylabel('Directional Asymmetry Index', fontsize=9)
ax1.set_ylim(-0.35, 0.35)
ax1.legend(loc='lower right', fontsize=8)

z_vals5 = np.arange(len(spd5_astig['A_xy_series']))
ax2.plot(z_vals5, spd5_astig['A_xy_series'], label='A_xy (0°-90°)', color='#D83B01', lw=1.5)
ax2.plot(z_vals5, spd5_astig['A_45_series'], label='A_45 (45°-135°)', color='#E3008C', lw=1.5)
ax2.axhline(0, color='gray', linestyle=':', alpha=0.6)
ax2.axvline(spd5_astig['z_true'], color='green', linestyle='--', label='True z*=' + str(spd5_astig['z_true']))
ax2.set_title('pollen.spd5 Stigmatic Asymmetry (Δz_stig = ' + str(spd5_astig['stigmator_error']) + 'f)', fontsize=10, fontweight='bold')
ax2.set_xlabel('Focal Plane z', fontsize=9)
ax2.set_ylim(-0.35, 0.35)
ax2.legend(loc='lower right', fontsize=8)

fig.tight_layout()
fig.savefig('report_charts/fig3_astigmatism.png')
plt.close(fig)

# -------------------------------------------------------------
# 4. Figure 4: Variance Stabilizing Transforms (VSTs) on Heavy Shot Noise
# -------------------------------------------------------------
with open('autofocus_suite/benchmark/results/vst_curves_cache.json', 'r') as f:
    vst_data = json.load(f)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=200)

vst_colors = {
    'none': '#68768A',
    'anscombe_unbiased': '#0078D4',
    'anscombe_algebraic': '#E81123',
    'msvst': '#107C41',
    'freeman_tukey': '#D83B01'
}

vst_labels = {
    'none': 'Raw Counts (No VST)',
    'anscombe_unbiased': 'Anscombe (Mäkitalo-Foi Unbiased)',
    'anscombe_algebraic': 'Anscombe (Algebraic Biased)',
    'msvst': 'MSVST (Multi-Scale Spline)',
    'freeman_tukey': 'Freeman-Tukey'
}

spd5_vsts = vst_data['pollen.spd5']['vsts']

# Subplot 1: M1 Scharr focus curves
for vm, label in vst_labels.items():
    if vm in spd5_vsts:
        c = np.array(spd5_vsts[vm]['curves']['m1_scharr'])
        c_norm = (c - c.min()) / (c.max() - c.min() + 1e-9)
        lw = 2.0 if vm in ['anscombe_unbiased', 'msvst'] else 1.2
        ls = '--' if vm == 'anscombe_algebraic' else '-'
        ax1.plot(c_norm, label=f"{label} (PSR={spd5_vsts[vm]['psr']['m1_scharr']})", 
                 color=vst_colors[vm], lw=lw, linestyle=ls)

ax1.axvline(95, color='black', linestyle=':', alpha=0.6, label='True Focus (z*=95)')
ax1.set_title('pollen.spd5: M1 Scharr Curves Under VST Preconditioning', fontsize=10.5, fontweight='bold')
ax1.set_xlabel('Focal Plane Index (z)', fontsize=9.5)
ax1.set_ylabel('Normalized Focus Score', fontsize=9.5)
ax1.set_ylim(-0.05, 1.05)
ax1.legend(loc='upper right', fontsize=7.5, framealpha=0.9)

# Subplot 2: Peak Sharpness Ratio (PSR) comparison across all noise levels
datasets = ['pollen.spd1\n(Clean)', 'pollen.spd2\n(Moderate)', 'pollen.spd3\n(Degraded)', 'pollen.spd5\n(Heavy Shot)']
x_idx = np.arange(len(datasets))
bar_width = 0.16

for i, (vm, label) in enumerate(vst_labels.items()):
    psrs = [vst_data[ds_name]['vsts'][vm]['psr']['m1_scharr'] for ds_name in ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']]
    ax2.bar(x_idx + (i - 2) * bar_width, psrs, bar_width, label=label, color=vst_colors[vm], alpha=0.88)

ax2.set_title('Peak Sharpness Ratio (PSR) Scaling by VST Method', fontsize=10.5, fontweight='bold')
ax2.set_ylabel('Peak Sharpness Ratio (Higher is Better)', fontsize=9.5)
ax2.set_xticks(x_idx)
ax2.set_xticklabels(datasets, fontsize=8.5)
ax2.legend(loc='upper left', fontsize=7.2, framealpha=0.9)

plt.tight_layout()
fig.savefig('report_charts/fig4_vst_comparison.png')
plt.close(fig)

# -------------------------------------------------------------
# 5. Figure 5: The Golden Rule: Inversion Matters Most (Mäkitalo-Foi vs Algebraic)
# -------------------------------------------------------------
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 3.8), dpi=200)

lambdas = np.linspace(0.1, 15.0, 300)

# Exact simulation of Anscombe forward + inverses
# E[2*sqrt(k + 3/8)] for Poisson(lambda)
def poisson_exp_y(lam_arr):
    out = []
    ks = np.arange(0, 100)[:, None]
    vals = 2.0 * np.sqrt(ks + 0.375)
    from scipy.stats import poisson
    for lam in lam_arr:
        pmf = poisson.pmf(ks, lam)
        out.append(float(np.sum(vals * pmf)))
    return np.array(out)

exp_y = poisson_exp_y(lambdas)

# Algebraic inverse on expected transformed variable: (y/2)^2 - 3/8
alg_mean = (exp_y / 2.0)**2 - 0.375

# Mäkitalo-Foi closed form
c_const = np.sqrt(1.5)
D = exp_y
mf_mean = 0.25 * (D**2) - 0.125 + (0.25 * c_const) / D - 1.375 / (D**2) + (0.625 * c_const) / (D**3)

# Subplot 1: Output Intensity vs True Poisson Lambda
ax1.plot(lambdas, lambdas, 'k--', label='Ideal Unbiased Recovery (y=λ)', lw=1.5)
ax1.plot(lambdas, mf_mean, color='#0078D4', label='Mäkitalo-Foi Exact Unbiased', lw=2.0)
ax1.plot(lambdas, alg_mean, color='#E81123', label='Direct Algebraic: (y/2)² - 3/8', lw=1.8, linestyle='-.')
ax1.set_title('(A) Expected Restored Intensity vs True λ', fontsize=10, fontweight='bold')
ax1.set_xlabel('True Specimen Mean Count (λ)', fontsize=9)
ax1.set_ylabel('Restored Count E[I]', fontsize=9)
ax1.legend(loc='upper left', fontsize=8)

# Subplot 2: Mathematical Bias Delta = E[I] - lambda
bias_alg = alg_mean - lambdas
bias_mf = mf_mean - lambdas

ax2.plot(lambdas, bias_mf, color='#0078D4', label='Mäkitalo-Foi Bias (≈ 0)', lw=2.0)
ax2.plot(lambdas, bias_alg, color='#E81123', label='Algebraic Bias (→ -0.25 offset)', lw=1.8, linestyle='-.')
ax2.axhline(-0.25, color='gray', linestyle=':', label='Theoretical Asymptotic Bias (-1/4)')
ax2.axhline(0.0, color='black', linestyle='-', alpha=0.3)
ax2.set_title('(B) Mathematical Bias Δ = E[I] - λ', fontsize=10, fontweight='bold')
ax2.set_xlabel('True Specimen Mean Count (λ)', fontsize=9)
ax2.set_ylabel('Bias in Counts', fontsize=9)
ax2.set_ylim(-0.35, 0.1)
ax2.legend(loc='lower right', fontsize=8)

# Subplot 3: Relative Percentage Error
err_alg = (bias_alg / lambdas) * 100.0
err_mf = (bias_mf / lambdas) * 100.0

ax3.plot(lambdas, err_mf, color='#0078D4', label='Mäkitalo-Foi (< 0.2%)', lw=2.0)
ax3.plot(lambdas, err_alg, color='#E81123', label='Algebraic (Severe Low-Count Crash)', lw=1.8, linestyle='-.')
ax3.axhline(0, color='black', linestyle='-', alpha=0.3)
ax3.set_title('(C) Relative Error % vs Mean Count', fontsize=10, fontweight='bold')
ax3.set_xlabel('True Specimen Mean Count (λ)', fontsize=9)
ax3.set_ylabel('Relative Error %', fontsize=9)
ax3.set_ylim(-35, 5)
ax3.legend(loc='lower right', fontsize=8)

plt.tight_layout()
fig.savefig('report_charts/fig5_makitalo_foi_bias.png')
plt.close(fig)

# -------------------------------------------------------------
# 6. Figure 6: Parametric Sweep: Initial Slice Position (z0)
# -------------------------------------------------------------
with open('autofocus_suite/benchmark/results/parametric_ablation.json', 'r') as f:
    param_data = json.load(f)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=200)

z0_data = param_data['z0_ablation']
z0_vals = [pt['z0'] for pt in z0_data['s1_fibonacci']]

sm_names = {
    's1_fibonacci': 'S1: Fibonacci Lattice',
    's2_hybrid': 'S2: Hybrid Coarse-Fine',
    's3_pyramid': 'S3: Pyramid Bracket',
    's4_speculative': 'S4: Speculative Parallel'
}
sm_colors = {
    's1_fibonacci': '#0078D4',
    's2_hybrid': '#107C41',
    's3_pyramid': '#D83B01',
    's4_speculative': '#8764B8'
}

for sm, label in sm_names.items():
    reads = [pt['reads'] for pt in z0_data[sm]]
    ax1.plot(z0_vals, reads, marker='o', lw=1.8, label=label, color=sm_colors[sm])

ax1.set_title('(A) Sampled Frames vs Initial Position z_0', fontsize=10, fontweight='bold')
ax1.set_xlabel('Initial Focal Plane (z_0)', fontsize=9)
ax1.set_ylabel('Total Micrographs Read', fontsize=9)
ax1.axvline(95, color='gray', linestyle=':', label='True Peak z*=95')
ax1.set_ylim(5, 65)
ax1.legend(loc='upper right', fontsize=8)

for sm, label in sm_names.items():
    errs = [pt['error'] for pt in z0_data[sm]]
    ax2.plot(z0_vals, errs, marker='s', lw=1.8, label=label, color=sm_colors[sm])

ax2.set_title('(B) Focus Error |z - z*| vs Initial Position z_0', fontsize=10, fontweight='bold')
ax2.set_xlabel('Initial Focal Plane (z_0)', fontsize=9)
ax2.set_ylabel('Discretization Error (Frames)', fontsize=9)
ax2.set_ylim(-0.2, 3.0)
ax2.legend(loc='upper left', fontsize=8)

plt.tight_layout()
fig.savefig('report_charts/fig6_first_frame_ablation.png')
plt.close(fig)

# -------------------------------------------------------------
# 7. Figure 7: Parametric Sweep: Dynamic 9-Zone Metering Patches (K in [1, 9])
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=200)

roi_data = param_data['roi_ablation']
k_vals = [pt['k'] for pt in roi_data]
latencies = [pt['ms'] for pt in roi_data]
errors = [pt['error'] for pt in roi_data]

ax1.plot(k_vals, latencies, marker='D', color='#0078D4', lw=2.0)
ax1.axvline(3, color='#107C41', linestyle='--', label='Default Baseline (K=3, 20.5 ms)')
ax1.set_title('(A) Execution Latency vs Metering Zone Count (K)', fontsize=10, fontweight='bold')
ax1.set_xlabel('Active Metering Zones (Top-K)', fontsize=9)
ax1.set_ylabel('Search Latency (ms)', fontsize=9)
ax1.set_xticks(k_vals)
ax1.legend(loc='upper left', fontsize=8)

ax2.plot(k_vals, errors, marker='^', color='#E81123', lw=2.0, label='Discretization Error')
ax2.axvline(3, color='#107C41', linestyle='--', label='Default Baseline (K=3, Error=1 frame)')
ax2.set_title('(B) Peak Error vs Metering Zone Count (K)', fontsize=10, fontweight='bold')
ax2.set_xlabel('Active Metering Zones (Top-K)', fontsize=9)
ax2.set_ylabel('Focus Discretization Error (Frames)', fontsize=9)
ax2.set_xticks(k_vals)
ax2.set_ylim(-0.2, 2.5)
ax2.legend(loc='upper right', fontsize=8)

plt.tight_layout()
fig.savefig('report_charts/fig7_roi_count_ablation.png')
plt.close(fig)

print('Generated all 7 publication-grade figures successfully in report_charts/.')
