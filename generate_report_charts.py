import os
import json
import matplotlib.pyplot as plt
import numpy as np

os.makedirs('report_charts', exist_ok=True)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

with open('autofocus_suite/benchmark/results/curves_cache.json', 'r') as f:
    curves_data = json.load(f)

# 1. Figure 1: 10 FMO Curves on Clean vs Heavy Shot Noise
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

# 2. Figure 2: Search Scheme Efficiency
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

# 3. Figure 3: Astigmatism & Directional Asymmetry Polar Diagnostics
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

print('Generated publication-grade figures successfully in report_charts/.')
