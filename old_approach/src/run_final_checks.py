import os
import glob
import numpy as np
import cv2
import matplotlib.pyplot as plt
import json

import sys
sys.path.append(os.path.dirname(__file__))

from search_algorithms import (
    hill_climbing_search, golden_section_search, momentum_hill_climbing,
    newton_raphson_search, secant_search
)
from focus_measures import (
    normalized_variance, tenengrad_measure, variance_of_laplacian,
    laplacian_of_gaussian, brenner_gradient
)

ALGORITHMS = {
    'Hill-Climbing': hill_climbing_search,
    'Momentum': momentum_hill_climbing,
    'Newton-Raphson': newton_raphson_search,
    'Secant': secant_search,
    'Golden Section': golden_section_search
}

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, 'datasets')
results_dir = os.path.join(base_dir, 'results')

def check_synthetic_gaussian():
    print("--- Check 1: Noiseless Synthetic Gaussian ---")
    x = np.arange(200)
    # Smooth, noiseless Gaussian. True peak at 100
    curve = 100.0 * np.exp(-(x - 100)**2 / (2 * 15**2))
    
    starts = [0, 50, 150, 199]
    max_idx = len(curve) - 1
    
    with open(os.path.join(results_dir, "synthetic_failures.txt"), "w") as f:
        for algo_name, func in ALGORITHMS.items():
            for s in starts:
                evals_list = []
                def eval_func(idx):
                    idx = int(max(0, min(max_idx, round(idx))))
                    evals_list.append((idx, curve[idx]))
                    return curve[idx]
                    
                if algo_name == 'Golden Section':
                    if s != 0: continue # GS doesn't take start_idx
                    best_idx, evals = func(eval_func, max_idx)
                else:
                    best_idx, evals = func(eval_func, max_idx, start_idx=s)
                    
                if abs(best_idx - 100) > 1:
                    print(f"{algo_name} failed from start {s}. Best idx: {best_idx}")
                    f.write(f"Algo: {algo_name}, Start: {s}, Best Idx: {best_idx}\n")
                    f.write(f"Evaluations: {evals_list}\n\n")

def check_float64_measures():
    print("--- Check 2: Float64 Measures & Intensity FFT ---")
    ds = 'pollen.spd1'
    img_paths = sorted(glob.glob(os.path.join(data_dir, ds, '*.png')))
    
    uint8_vol = []
    float64_vol = []
    mean_intensities = []
    
    for p in img_paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        mean_intensities.append(np.mean(img))
        
        # Original VoL
        uint8_vol.append(np.var(cv2.Laplacian(img, cv2.CV_64F, ksize=3)))
        
        # Float64 VoL
        img_f64 = img.astype(np.float64)
        float64_vol.append(np.var(cv2.Laplacian(img_f64, cv2.CV_64F, ksize=3)))
        
    plt.figure(figsize=(10, 5))
    plt.plot(uint8_vol, label='VoL (from uint8 image)')
    plt.plot(float64_vol, label='VoL (from float64 image)', linestyle='--')
    plt.legend()
    plt.title('VoL: uint8 input vs float64 input')
    plt.savefig(os.path.join(results_dir, "vol_dtype_comparison.png"))
    plt.close()
    
    # FFT of Mean Intensity
    floor_intensity = mean_intensities[0:80]
    floor_intensity = floor_intensity - np.mean(floor_intensity)
    fft_int = np.abs(np.fft.rfft(floor_intensity))
    freqs = np.fft.rfftfreq(len(floor_intensity))
    
    plt.figure(figsize=(10, 5))
    plt.plot(1 / freqs[1:], fft_int[1:], label='Mean Intensity FFT')
    plt.title('FFT of Mean Image Intensity (Out of Focus Floor)')
    plt.xlabel('Period (Frames)')
    plt.legend()
    plt.savefig(os.path.join(results_dir, "intensity_fft.png"))
    plt.close()

def check_floor_cv():
    print("--- Check 3: Recompute Floor CV ---")
    with open(os.path.join(results_dir, 'curves_cache.json'), 'r') as f:
        cache = json.load(f)
        
    ds = 'pollen.spd1'
    
    print(f"Floor CVs for {ds} (indices 0-40 explicit floor):")
    for measure in ['NV', 'Tenengrad', 'VoL', 'LoG', 'Brenner']:
        curve = np.array(cache[ds][measure])
        # Explicit floor: first 40 frames where it is completely out of focus
        floor = curve[0:40]
        cv = np.std(floor) / np.mean(floor)
        print(f"  {measure}: {cv:.4f}")

if __name__ == '__main__':
    check_synthetic_gaussian()
    check_float64_measures()
    check_floor_cv()
    print("Checks completed.")
