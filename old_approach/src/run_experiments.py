import os
import glob
import json
import time
import numpy as np
import cv2
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import curve_fit
from scipy.ndimage import gaussian_filter1d

import sys
sys.path.append(os.path.dirname(__file__))

from focus_measures import (
    normalized_variance, tenengrad_measure, variance_of_laplacian,
    laplacian_of_gaussian, brenner_gradient
)
from search_algorithms import (
    hill_climbing_search, golden_section_search, momentum_hill_climbing,
    newton_raphson_search, secant_search
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, 'datasets')
results_dir = os.path.join(base_dir, 'results')
os.makedirs(results_dir, exist_ok=True)

DATASETS = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']
MEASURES = {
    'NV': normalized_variance,
    'Tenengrad': tenengrad_measure,
    'VoL': variance_of_laplacian,
    'LoG': laplacian_of_gaussian,
    'Brenner': brenner_gradient
}
ALGORITHMS = {
    'Hill-Climbing': hill_climbing_search,
    'Momentum': momentum_hill_climbing,
    'Newton-Raphson': newton_raphson_search,
    'Secant': secant_search,
    'Golden Section': golden_section_search
}

CACHE_FILE = os.path.join(results_dir, 'curves_cache.json')

def precompute_curves():
    if os.path.exists(CACHE_FILE):
        print("Loading cached curves...")
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
            
    print("Computing curves from scratch...")
    cache = {}
    for ds in DATASETS:
        cache[ds] = {}
        img_paths = sorted(glob.glob(os.path.join(data_dir, ds, '*.jpg')))
        if not img_paths:
            img_paths = sorted(glob.glob(os.path.join(data_dir, ds, '*.png')))
            
        print(f"Processing {ds} with {len(img_paths)} images...")
        images = [cv2.imread(p, cv2.IMREAD_GRAYSCALE) for p in img_paths]
        
        for m_name, m_func in MEASURES.items():
            curve = [float(m_func(img)) for img in images]
            cache[ds][m_name] = curve
            
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)
    return cache

def run_algo(algo_name, curve, max_idx, start_idx=0):
    evals_count = [0]
    def eval_func(x):
        evals_count[0] += 1
        return curve[int(max(0, min(max_idx, round(x))))]
        
    func = ALGORITHMS[algo_name]
    if algo_name == 'Golden Section':
        best_idx, evals = func(eval_func, max_idx)
    else:
        best_idx, evals = func(eval_func, max_idx, start_idx=start_idx)
    
    return best_idx, len(evals)

# --- 1. Success rate vs starting position ---
def exp1_success_vs_start(cache):
    print("Running Exp 1: Success vs Start...")
    ds = 'pollen.spd1'
    m_name = 'Tenengrad'
    curve = cache[ds][m_name]
    true_peak = np.argmax(curve)
    
    max_idx = len(curve) - 1
    
    plt.figure(figsize=(10, 6))
    for algo_name in ALGORITHMS.keys():
        errors = []
        starts = list(range(len(curve)))
        if algo_name == 'Golden Section':
            idx, _ = run_algo(algo_name, curve, max_idx)
            errors = [abs(idx - true_peak)] * len(curve)
        else:
            for s in starts:
                idx, _ = run_algo(algo_name, curve, max_idx, start_idx=s)
                errors.append(abs(idx - true_peak))
        
        plt.plot(starts, errors, label=algo_name, alpha=0.8, linewidth=2)
        
    plt.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='Success Threshold')
    plt.xlabel('Starting Position (Index)')
    plt.ylabel('Absolute Error (Indices)')
    plt.title(f'Exp 1: Search Error vs Start Position ({m_name})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp1_success_vs_start.png'))
    plt.close()

# --- 2. Golden Section error vs true peak location ---
def exp2_gs_peak_shift(cache):
    print("Running Exp 2: GS vs Peak Shift...")
    ds = 'pollen.spd1'
    m_name = 'Tenengrad'
    base_curve = np.array(cache[ds][m_name])
    max_idx = len(base_curve) - 1
    
    shifts = list(range(10, max_idx - 10, 10))
    errors = []
    
    for shift in shifts:
        current_peak = np.argmax(base_curve)
        roll_amount = shift - current_peak
        if roll_amount > 0:
            floor_val = np.mean(base_curve[:40])
            shifted_curve = np.array([floor_val] * roll_amount + base_curve[:-roll_amount].tolist())
        elif roll_amount < 0:
            floor_val = np.mean(base_curve[:40])
            shifted_curve = np.array(base_curve[-roll_amount:].tolist() + [floor_val] * (-roll_amount))
        else:
            shifted_curve = base_curve.copy()
        
        # Smooth the padding junction to remove artificial discontinuity
        shifted_curve = gaussian_filter1d(shifted_curve, sigma=1.5).tolist()
        
        idx, _ = run_algo('Golden Section', shifted_curve, max_idx)
        errors.append(abs(idx - shift))
        
    plt.figure(figsize=(10, 6))
    plt.plot(shifts, errors, marker='o', linestyle='-', color='purple')
    plt.xlabel('True Peak Location (Index)')
    plt.ylabel('Golden Section Error (Indices)')
    plt.title('Exp 2: Golden Section Error vs True Peak Location')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp2_gs_peak_shift.png'))
    plt.close()

# --- 3. Algorithm x focus-measure heatmap ---
def exp3_heatmap(cache):
    print("Running Exp 3: Heatmap...")
    success_rates = np.zeros((len(ALGORITHMS), len(MEASURES)))
    algo_names = list(ALGORITHMS.keys())
    measure_names = list(MEASURES.keys())
    
    for i, algo in enumerate(algo_names):
        for j, measure in enumerate(measure_names):
            successes = 0
            total = 0
            for ds in DATASETS:
                curve = cache[ds][measure]
                true_peak = np.argmax(curve)
                max_idx = len(curve) - 1
                starts = np.linspace(0, max_idx, 20, dtype=int)
                
                if algo == 'Golden Section':
                    idx, _ = run_algo(algo, curve, max_idx)
                    if abs(idx - true_peak) <= 1:
                        successes += len(starts)
                    total += len(starts)
                else:
                    for s in starts:
                        idx, _ = run_algo(algo, curve, max_idx, start_idx=s)
                        if abs(idx - true_peak) <= 1:
                            successes += 1
                        total += 1
            success_rates[i, j] = (successes / total) * 100
            
    plt.figure(figsize=(8, 6))
    sns.heatmap(success_rates, annot=True, fmt=".1f", xticklabels=measure_names, yticklabels=algo_names, cmap='RdYlGn', vmin=0, vmax=100)
    plt.title('Exp 3: Success Rate (%) over All Starts/Datasets')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp3_heatmap.png'))
    plt.close()

# --- 4. Success rate vs noise level ---
def exp4_noise_robustness(cache):
    print("Running Exp 4: Noise Robustness...")
    ds = 'pollen.spd1'
    m_name = 'NV'
    base_curve = np.array(cache[ds][m_name])
    peak_val = np.max(base_curve)
    true_peak = np.argmax(base_curve)
    
    sigmas = np.linspace(0, 0.2 * peak_val, 10)
    
    max_idx = len(base_curve) - 1
    
    plt.figure(figsize=(10, 6))
    for algo in ALGORITHMS.keys():
        success_means = []
        for sigma in sigmas:
            successes = 0
            trials = 50
            for _ in range(trials):
                noisy_curve = base_curve + np.random.normal(0, sigma, size=base_curve.shape)
                # Fixed midpoint start for fair noise-only comparison across algorithms
                start = max_idx // 2
                idx, _ = run_algo(algo, noisy_curve.tolist(), max_idx, start_idx=start)
                if abs(idx - true_peak) <= 2:
                    successes += 1
            success_means.append(successes / trials * 100)
        plt.plot(sigmas / peak_val * 100, success_means, label=algo, marker='o')
        
    plt.xlabel('Noise Standard Deviation (% of Peak Height)')
    plt.ylabel('Success Rate (%)')
    plt.title(f'Exp 4: Robustness against Gaussian Noise ({m_name})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp4_noise_robustness.png'))
    plt.close()

# --- 5. Accuracy-cost scatter ---
def exp5_accuracy_cost(cache):
    print("Running Exp 5: Accuracy-Cost...")
    plt.figure(figsize=(10, 6))
    
    markers = ['o', 's', '^', 'D', 'v']
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']
    
    for i, algo in enumerate(ALGORITHMS.keys()):
        for j, measure in enumerate(MEASURES.keys()):
            evals_list = []
            errors_um = []
            for ds in DATASETS:
                curve = cache[ds][measure]
                true_peak = np.argmax(curve)
                max_idx = len(curve) - 1
                starts = [0] if algo == 'Golden Section' else [0, 50, max_idx - 50]
                for s in starts:
                    if algo == 'Golden Section':
                        idx, evals = run_algo(algo, curve, max_idx)
                    else:
                        idx, evals = run_algo(algo, curve, max_idx, start_idx=s)
                    evals_list.append(evals)
                    errors_um.append(abs(idx - true_peak) * 10)
                    
            plt.scatter(evals_list, errors_um, c=colors[i], marker=markers[j], alpha=0.6,
                        label=algo if j==0 else "")
            
    plt.yscale('symlog', linthresh=0.5)
    plt.xlabel('Number of Evaluations (Cost)')
    plt.ylabel('Absolute Error in $\\mu$m (log scale)')
    plt.title('Exp 5: Accuracy vs Cost')
    
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    # Add measure markers to legend for readability
    from matplotlib.lines import Line2D
    measure_handles = [Line2D([0], [0], marker=markers[j], color='gray', label=m,
                              linestyle='', markersize=8) for j, m in enumerate(MEASURES.keys())]
    all_handles = list(by_label.values()) + measure_handles
    all_labels = list(by_label.keys()) + list(MEASURES.keys())
    plt.legend(all_handles, all_labels, loc='upper right', fontsize=8, ncol=2)
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp5_accuracy_cost.png'))
    plt.close()

# --- 6. Error distribution per algorithm ---
def exp6_error_dist(cache):
    print("Running Exp 6: Error Distribution...")
    data = []
    labels = []
    
    for algo in ALGORITHMS.keys():
        errors_um = []
        for ds in DATASETS:
            for measure in MEASURES.keys():
                curve = cache[ds][measure]
                true_peak = np.argmax(curve)
                max_idx = len(curve) - 1
                for s in [0, max_idx // 2, max_idx]:
                    idx, _ = run_algo(algo, curve, max_idx, start_idx=s)
                    errors_um.append(abs(idx - true_peak) * 10)
        data.append(errors_um)
        labels.append(algo)
        
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=data, cut=0)
    plt.xticks(range(len(labels)), labels)
    
    plt.axhspan(0, 20, color='green', alpha=0.2, label='Depth of Field (~20$\\mu$m)')
    
    plt.ylabel('Absolute Error ($\\mu$m)')
    plt.title('Exp 6: Error Distribution across all setups')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp6_error_dist.png'))
    plt.close()

# --- 7. Focus-measure quality panel ---
def exp7_measure_quality(cache):
    print("Running Exp 7: Measure Quality...")
    
    measure_names = list(MEASURES.keys())
    metrics = {'Peak/Floor Ratio': [], 'Floor CV': []}
    
    for measure in measure_names:
        p2f = []
        cv = []
        for ds in DATASETS:
            curve = np.array(cache[ds][measure])
            peak = np.max(curve)
            # Dynamic floor detection: indices below 20% of peak rise
            peak_val = np.max(curve)
            min_val = np.min(curve)
            threshold = min_val + 0.2 * (peak_val - min_val)
            floor_end = len(curve)
            for k in range(len(curve)):
                if curve[k] > threshold:
                    floor_end = k
                    break
            floor_end = max(floor_end, 10)  # At least 10 samples for statistics
            floor = curve[:floor_end]
            
            p2f.append(peak / np.mean(floor) if np.mean(floor) != 0 else 0)
            cv.append(np.std(floor) / np.mean(floor) if np.mean(floor) != 0 else 0)
            
        metrics['Peak/Floor Ratio'].append(np.mean(p2f))
        metrics['Floor CV'].append(np.mean(cv))
        
    x = np.arange(len(measure_names))
    width = 0.35
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    rects1 = ax1.bar(x - width/2, metrics['Peak/Floor Ratio'], width, label='Peak/Floor Ratio', color='tab:blue')
    ax1.set_ylabel('Peak/Floor Ratio', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    ax2 = ax1.twinx()
    rects2 = ax2.bar(x + width/2, metrics['Floor CV'], width, label='Floor CV', color='tab:red')
    ax2.set_ylabel('Floor CV (Noise)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(measure_names)
    plt.title('Exp 7: Focus Measure Quality')
    fig.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp7_measure_quality.png'))
    plt.close()

# --- 8. Convergence traces ---
def exp8_convergence(cache):
    print("Running Exp 8: Convergence Traces...")
    ds = 'pollen.spd1'
    m_name = 'Tenengrad'
    curve = cache[ds][m_name]
    true_peak = np.argmax(curve)
    max_idx = len(curve) - 1
    
    plt.figure(figsize=(10, 6))
    for algo_name, func in ALGORITHMS.items():
        best_diff_history = []
        
        def eval_func(x):
            idx = int(max(0, min(max_idx, round(x))))
            val = curve[idx]
            
            if not hasattr(eval_func, "best_val") or val > eval_func.best_val:
                eval_func.best_val = val
                eval_func.best_idx = idx
                
            best_diff_history.append(abs(eval_func.best_idx - true_peak))
            return val
            
        eval_func.best_val = -np.inf
        eval_func.best_idx = 0
        
        if algo_name == 'Golden Section':
            func(eval_func, max_idx)
        else:
            func(eval_func, max_idx, start_idx=0)
            
        plt.plot(range(1, len(best_diff_history)+1), best_diff_history, label=algo_name, linewidth=2)
        
    plt.xlabel('Evaluation Step')
    plt.ylabel('Distance to True Peak (Indices)')
    plt.title('Exp 8: Convergence Traces from Index 0')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp8_convergence.png'))
    plt.close()

# --- 9. Fine-peak estimate with uncertainty ---
def exp9_fine_peak(cache):
    print("Running Exp 9: Fine-Peak Bootstrap...")
    ds = 'pollen.spd1'
    
    def gaussian(x, a, x0, sigma, offset):
        return a * np.exp(-(x - x0)**2 / (2 * sigma**2)) + offset
        
    results = {}
    for measure in MEASURES.keys():
        curve = np.array(cache[ds][measure])
        x = np.arange(len(curve))
        
        try:
            popt, _ = curve_fit(gaussian, x, curve, p0=[np.max(curve), np.argmax(curve), 5, np.min(curve)], maxfev=5000)
            ground_truth = popt[1]
        except Exception:
            ground_truth = np.argmax(curve)
            
        peaks = []
        max_idx = len(curve) - 1
        # Use actual floor noise level for realistic bootstrap
        floor_noise = np.std(curve[:40])
        for _ in range(100):
            noisy = curve + np.random.normal(0, floor_noise, size=curve.shape)
            c_idx = np.argmax(noisy)
            if 0 < c_idx < max_idx:
                x_sub = np.array([-1, 0, 1])
                y_sub = noisy[c_idx-1:c_idx+2]
                poly = np.polyfit(x_sub, y_sub, 2)
                fine_offset = -poly[1] / (2 * poly[0]) if poly[0] < 0 else 0
                peaks.append(c_idx + fine_offset)
        
        results[measure] = (ground_truth, np.mean(peaks), np.std(peaks))
        
    measure_names = list(results.keys())
    means = [results[m][1] for m in measure_names]
    stds = [results[m][2] for m in measure_names]
    gts = [results[m][0] for m in measure_names]
    
    plt.figure(figsize=(10, 6))
    plt.errorbar(measure_names, means, yerr=stds, fmt='o', label='3-Point Bootstrap', capsize=5)
    plt.plot(measure_names, gts, 'r^', label='Gaussian Whole-Curve Fit')
    plt.ylabel('Fine Peak Position (Index)')
    plt.title('Exp 9: Sub-Index Fine Peak Uncertainty (spd1)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp9_fine_peak_bootstrap.png'))
    plt.close()

# --- 10. Timing breakdown with error bars ---
def exp10_timing():
    print("Running Exp 10: Timing Breakdown...")
    img_paths = sorted(glob.glob(os.path.join(data_dir, 'pollen.spd1', '*.jpg')))[:10]
    if not img_paths:
        img_paths = sorted(glob.glob(os.path.join(data_dir, 'pollen.spd1', '*.png')))[:10]
        
    # Note: After first iteration, OS disk cache serves images from RAM.
    # These timings reflect warm-cache I/O, not cold-disk first access.
    io_times = []
    comp_times = []
    
    for _ in range(20):
        t0 = time.perf_counter()
        imgs = [cv2.imread(p, cv2.IMREAD_GRAYSCALE) for p in img_paths]
        t1 = time.perf_counter()
        measures = [tenengrad_measure(img) for img in imgs]
        t2 = time.perf_counter()
        
        io_times.append((t1 - t0) * 1000 / len(img_paths)) 
        comp_times.append((t2 - t1) * 1000 / len(img_paths))
        
    labels = ['Image I/O (Disk)', 'Tenengrad Compute']
    means = [np.mean(io_times), np.mean(comp_times)]
    stds = [np.std(io_times), np.std(comp_times)]
    
    plt.figure(figsize=(6, 6))
    plt.bar(labels, means, yerr=stds, capsize=5, color=['tab:gray', 'tab:blue'])
    plt.ylabel('Time per Frame (ms)')
    plt.title('Exp 10: Evaluation Timing Breakdown')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp10_timing_breakdown.png'))
    plt.close()

# --- 11. Periodicity check on the noise floor ---
def exp11_periodicity(cache):
    print("Running Exp 11: Periodicity (FFT)...")
    ds = 'pollen.spd1'
    
    plt.figure(figsize=(10, 6))
    
    for m_name in ['VoL', 'Brenner']:
        curve = np.array(cache[ds][m_name])
        floor = curve[0:50]
        floor = floor - np.mean(floor)
        
        fft = np.abs(np.fft.rfft(floor))
        freqs = np.fft.rfftfreq(len(floor))
        
        if m_name == 'Brenner':
            fft *= 100
            
        plt.plot(1 / freqs[1:], fft[1:], label=m_name + (' (x100)' if m_name == 'Brenner' else ''))
        
    plt.xlabel('Period (Frames)')
    plt.ylabel('Amplitude')
    plt.xlim(0, 20)
    plt.axvline(x=7.5, color='r', linestyle='--', alpha=0.5, label='Suspected Artifact Period (~7.5)')
    plt.title('Exp 11: FFT of Out-of-Focus Noise Floor')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'exp11_periodicity.png'))
    plt.close()

if __name__ == '__main__':
    np.random.seed(42)  # For reproducibility
    cache = precompute_curves()
    
    exp1_success_vs_start(cache)
    exp2_gs_peak_shift(cache)
    exp3_heatmap(cache)
    exp4_noise_robustness(cache)
    exp5_accuracy_cost(cache)
    exp6_error_dist(cache)
    exp7_measure_quality(cache)
    exp8_convergence(cache)
    exp9_fine_peak(cache)
    exp10_timing()
    exp11_periodicity(cache)
    
    print("All experiments completed successfully. Plots saved to results/.")
