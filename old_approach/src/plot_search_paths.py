import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from focus_measures import tenengrad_measure
from search_algorithms import hill_climbing_search, golden_section_search

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dataset_dir = os.path.join(base_dir, 'datasets')
output_dir = os.path.join(base_dir, 'results')

def plot_search_path(dataset_path, dataset_name):
    image_paths = sorted(glob.glob(os.path.join(dataset_path, '*.png')))
    if not image_paths:
        return
    max_idx = len(image_paths) - 1
    
    # 1. Compute full curve
    curve_y = []
    for path in image_paths:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        curve_y.append(tenengrad_measure(img))
    curve_x = np.arange(len(curve_y))
    
    # wrapper for tracking evaluations
    def make_eval_func():
        trace = []
        def eval_func(idx):
            val = curve_y[idx]
            trace.append((idx, val))
            return val
        return eval_func, trace

    # Hill Climbing trace
    eval_func_hc, trace_hc = make_eval_func()
    hill_climbing_search(eval_func_hc, max_idx, start_idx=0, initial_step=10)
    
    # Golden Section trace
    eval_func_gs, trace_gs = make_eval_func()
    golden_section_search(eval_func_gs, max_idx)
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Hill Climbing subplot
    ax1.plot(curve_x, curve_y, color='lightgray', linewidth=2, label='True Focus Curve')
    hc_x = [t[0] for t in trace_hc]
    hc_y = [t[1] for t in trace_hc]
    ax1.plot(hc_x, hc_y, 'r-o', alpha=0.7, label='Evaluated Points', markersize=5)
    ax1.plot(hc_x[0], hc_y[0], 'go', markersize=8, label='Start')
    ax1.plot(hc_x[-1], hc_y[-1], 'bo', markersize=8, label='End')
    true_peak = np.argmax(curve_y)
    hc_best_eval = max(range(len(hc_y)), key=lambda k: hc_y[k])
    if abs(hc_x[hc_best_eval] - true_peak) <= 2:
        ax1.set_title('Hill Climbing: Found Peak')
    else:
        ax1.set_title('Hill Climbing: Trapped in Local Max')
    ax1.set_xlabel('Image Index')
    ax1.set_ylabel('Focus Measure (Tenengrad)')
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    # Golden Section subplot
    ax2.plot(curve_x, curve_y, color='lightgray', linewidth=2, label='True Focus Curve')
    gs_x = [t[0] for t in trace_gs]
    gs_y = [t[1] for t in trace_gs]
    ax2.plot(gs_x, gs_y, 'm-o', alpha=0.5, label='Evaluated Points', markersize=5)
    ax2.plot(gs_x[-1], gs_y[-1], 'bo', markersize=8, label='End (True Peak)')
    ax2.set_title(f'Golden Section: Hones in on Global Max')
    ax2.set_xlabel('Image Index')
    ax2.set_ylabel('Focus Measure (Tenengrad)')
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    plt.suptitle(f'Search Path Analysis - {dataset_name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{dataset_name}_search_path.png'))
    plt.close()

if __name__ == '__main__':
    datasets = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']
    for ds in datasets:
        full_path = os.path.join(dataset_dir, ds)
        if os.path.exists(full_path):
            print(f"Generating search path plot for {ds}...")
            plot_search_path(full_path, ds)
