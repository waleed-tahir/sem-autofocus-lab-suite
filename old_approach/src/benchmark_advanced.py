import cv2
import numpy as np
import os
import glob
import json
import time

from focus_measures import (
    normalized_variance, tenengrad_measure, variance_of_laplacian, laplacian_of_gaussian, brenner_gradient
)
from search_algorithms import (
    global_search, hill_climbing_search, golden_section_search,
    momentum_hill_climbing, newton_raphson_search, secant_search
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dataset_dir = os.path.join(base_dir, 'datasets')
results_dir = os.path.join(base_dir, 'results')

def quadratic_fit(evals, max_idx, max_eval_idx):
    if max_eval_idx > 0 and max_eval_idx < max_idx:
        try:
            x_points = np.array([max_eval_idx - 1, max_eval_idx, max_eval_idx + 1])
            y_points = np.array([evals[int(x)] for x in x_points])
            coeffs = np.polyfit(x_points, y_points, 2)
            a, b, c = coeffs[0], coeffs[1], coeffs[2]
            if a < 0:
                return -b / (2 * a)
        except Exception:
            pass
    return float(max_eval_idx)

def run_benchmarks():
    datasets = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']
    
    focus_measures = {
        'Tenengrad': tenengrad_measure,
        'VoL': variance_of_laplacian,
        'LoG': laplacian_of_gaussian,
        'Brenner': brenner_gradient
    }
    
    search_algos = {
        'Global': global_search,
        'Hill_Climbing': hill_climbing_search,
        'Golden_Section': golden_section_search,
        'Momentum': momentum_hill_climbing,
        'Newton_Raphson': newton_raphson_search,
        'Secant': secant_search
    }
    
    results = {}
    
    for ds in datasets:
        print(f"Benchmarking {ds}...")
        ds_path = os.path.join(dataset_dir, ds)
        image_paths = sorted(glob.glob(os.path.join(ds_path, '*.png')))
        if not image_paths:
            continue
        max_idx = len(image_paths) - 1
        
        results[ds] = {'measures': {}, 'algorithms': {}}
        
        # Benchmark Focus Measures
        for fm_name, fm_func in focus_measures.items():
            cache = {}
            def eval_func(idx, _fm=fm_func):
                if idx not in cache:
                    img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        cache[idx] = 0.0
                    else:
                        cache[idx] = _fm(img)
                return cache[idx]
                
            t0 = time.time()
            best_idx, evals = global_search(eval_func, max_idx)
            t1 = time.time()
            
            curve = [float(evals.get(i, 0)) for i in range(max_idx + 1)]
            
            results[ds]['measures'][fm_name] = {
                'time_ms': (t1 - t0) * 1000,
                'coarse_idx': best_idx,
                'curve': curve
            }
            
        # Benchmark Algorithms using LoG (Laplacian of Gaussian) as it's the best measure
        print(f"  Testing algorithms with LoG...")
        for algo_name, algo_func in search_algos.items():
            cache = {}
            trace = []
            def eval_func_algo(idx, _cache=cache, _trace=trace):
                if idx not in _cache:
                    img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        val = 0.0
                    else:
                        val = laplacian_of_gaussian(img)
                    _cache[idx] = val
                    _trace.append((idx, float(val)))
                else:
                    _trace.append((idx, float(_cache[idx])))
                return _cache[idx]
                
            t0 = time.time()
            if algo_name == 'Golden_Section':
                best_idx, evals = algo_func(eval_func_algo, max_idx)
            else:
                best_idx, evals = algo_func(eval_func_algo, max_idx, start_idx=0)
            t1 = time.time()
            fine_idx = quadratic_fit(evals, max_idx, best_idx)
            
            results[ds]['algorithms'][algo_name] = {
                'time_ms': (t1 - t0) * 1000,
                'evals_count': len(evals),
                'coarse_idx': best_idx,
                'fine_idx': float(fine_idx),
                'trace': trace
            }
            print(f"    {algo_name}: {len(evals)} evals, peak at {fine_idx:.2f}")
            
    with open(os.path.join(results_dir, 'advanced_benchmark.json'), 'w') as f:
        json.dump(results, f, indent=4)
    print("Done! Results saved to results/advanced_benchmark.json")

if __name__ == '__main__':
    run_benchmarks()
