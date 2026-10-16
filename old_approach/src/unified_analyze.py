import cv2
import numpy as np
import os
import glob
import json
import time
from focus_measures import tenengrad_measure
from search_algorithms import global_search, hill_climbing_search, golden_section_search

def quadratic_fit(evals, max_idx, max_eval_idx):
    if max_eval_idx > 0 and max_eval_idx < max_idx:
        try:
            x_points = np.array([max_eval_idx - 1, max_eval_idx, max_eval_idx + 1])
            y_points = np.array([evals[x] for x in x_points])
            coeffs = np.polyfit(x_points, y_points, 2)
            a, b, c = coeffs
            if a < 0:
                fine_index = -b / (2 * a)
            else:
                fine_index = max_eval_idx
        except KeyError:
            # Fallback if neighbors weren't evaluated
            fine_index = max_eval_idx
    else:
        fine_index = max_eval_idx
    return fine_index

def analyze_dataset_unified(dataset_path):
    image_paths = sorted(glob.glob(os.path.join(dataset_path, '*.png')))
    if not image_paths:
        return None
        
    max_idx = len(image_paths) - 1
    results = {}
    
    # 1. Global Search
    image_cache = {}
    def eval_func_global(idx):
        if idx not in image_cache:
            img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
            image_cache[idx] = tenengrad_measure(img)
        return image_cache[idx]
        
    t0 = time.time()
    g_best, g_evals = global_search(eval_func_global, max_idx)
    g_fine = quadratic_fit(g_evals, max_idx, g_best)
    t1 = time.time()
    results['Global'] = {
        'evals_count': len(g_evals),
        'coarse_idx': g_best,
        'fine_idx': g_fine,
        'time_ms': (t1 - t0) * 1000
    }
    
    # 2. Hill Climbing
    image_cache = {}
    def eval_func_hc(idx):
        if idx not in image_cache:
            img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
            image_cache[idx] = tenengrad_measure(img)
        return image_cache[idx]
        
    t0 = time.time()
    hc_best, hc_evals = hill_climbing_search(eval_func_hc, max_idx, start_idx=0, initial_step=10)
    hc_fine = quadratic_fit(hc_evals, max_idx, hc_best)
    t1 = time.time()
    results['Hill_Climbing'] = {
        'evals_count': len(hc_evals),
        'coarse_idx': hc_best,
        'fine_idx': hc_fine,
        'time_ms': (t1 - t0) * 1000
    }
    
    # 3. Golden Section Search
    image_cache = {}
    def eval_func_gs(idx):
        if idx not in image_cache:
            img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
            image_cache[idx] = tenengrad_measure(img)
        return image_cache[idx]
        
    t0 = time.time()
    gs_best, gs_evals = golden_section_search(eval_func_gs, max_idx)
    gs_fine = quadratic_fit(gs_evals, max_idx, gs_best)
    t1 = time.time()
    results['Golden_Section'] = {
        'evals_count': len(gs_evals),
        'coarse_idx': gs_best,
        'fine_idx': gs_fine,
        'time_ms': (t1 - t0) * 1000
    }
    
    return results

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, 'datasets')
    
    datasets = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']
    all_results = {}
    
    for ds in datasets:
        full_path = os.path.join(dataset_dir, ds)
        if os.path.exists(full_path):
            print(f"Running unified analysis on {ds}...")
            all_results[ds] = analyze_dataset_unified(full_path)
            
    with open(os.path.join(base_dir, 'results', 'unified_search_results.json'), 'w') as f:
        json.dump(all_results, f, indent=4)
        
    for ds, res in all_results.items():
        print(f"\nResults for {ds}:")
        for method, data in res.items():
            print(f"  [{method:15s}] Evals: {data['evals_count']:3d} | Time: {data['time_ms']:7.2f} ms | Coarse: {data['coarse_idx']:3d} | Fine: {data['fine_idx']:.4f}")
