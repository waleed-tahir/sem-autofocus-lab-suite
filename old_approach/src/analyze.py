import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import sys
from focus_measures import normalized_variance, tenengrad_measure

def analyze_dataset(dataset_path, output_dir):
    image_paths = sorted(glob.glob(os.path.join(dataset_path, '*.png')))
    if not image_paths:
        print(f"No images found in {dataset_path}")
        return

    variances_nv = []
    variances_tenengrad = []
    
    for path in image_paths:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            variances_nv.append(normalized_variance(img))
            variances_tenengrad.append(tenengrad_measure(img))
            
    # We use 0-based index to be consistent with other scripts
    indices = np.arange(0, len(variances_nv))
    
    methods = {
        'Normalized_Variance': variances_nv,
        'Tenengrad_Sobel': variances_tenengrad
    }

    dataset_name = os.path.basename(dataset_path)
    print(f"\n{'='*40}")
    print(f"Analysis for: {dataset_name}")
    print(f"{'='*40}")
    
    fig, axes = plt.subplots(len(methods), 2, figsize=(14, 6 * len(methods)))
    if len(methods) == 1:
        axes = [axes]
    
    for i, (method_name, variances) in enumerate(methods.items()):
        max_idx = np.argmax(variances)
        coarse_focus_val = variances[max_idx]
        coarse_image_path = image_paths[max_idx]
        coarse_index = indices[max_idx]
        
        # Quadratic curve fitting
        a, b, c = 0, 0, 0
        if max_idx > 0 and max_idx < len(variances) - 1:
            x_points = indices[max_idx - 1 : max_idx + 2]
            y_points = variances[max_idx - 1 : max_idx + 2]
            coeffs = np.polyfit(x_points, y_points, 2)
            a, b, c = coeffs
            if a < 0:
                fine_index = -b / (2 * a)
            else:
                fine_index = coarse_index
        else:
            fine_index = coarse_index

        coarse_wd = 10.0 + coarse_index * 0.01
        fine_wd = 10.0 + fine_index * 0.01

        print(f"\n[{method_name}]")
        print(f"  Coarse sharpest image: {os.path.basename(coarse_image_path)}")
        print(f"  Focus value: {coarse_focus_val:.4f}")
        print(f"  Coarse position: Index {coarse_index} | WD {coarse_wd:.4f} mm")
        print(f"  Fine position: Index {fine_index:.4f} | WD {fine_wd:.4f} mm")
        
        # Plotting
        ax_img = axes[i][0]
        ax_plot = axes[i][1]
        
        img = cv2.imread(coarse_image_path)
        if img is not None:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax_img.imshow(img_rgb)
        ax_img.set_title(f"Coarse Sharpest ({method_name})\n{os.path.basename(coarse_image_path)}")
        ax_img.axis('off')
        
        ax_plot.plot(indices, variances, marker='o', markersize=2, label=method_name)
        ax_plot.axvline(x=coarse_index, color='r', linestyle='--', label=f'Coarse Peak (idx={coarse_index})')
        ax_plot.axvline(x=fine_index, color='g', linestyle='-', label=f'Fine Peak (idx={fine_index:.2f})')
        
        if max_idx > 0 and max_idx < len(variances) - 1 and a < 0:
            x_fit = np.linspace(coarse_index - 1.5, coarse_index + 1.5, 50)
            y_fit = a * x_fit**2 + b * x_fit + c
            ax_plot.plot(x_fit, y_fit, 'k:', label='Quadratic Fit')
            
        ax_plot.set_xlabel('Image Index')
        ax_plot.set_ylabel('Focus Measure Value')
        ax_plot.set_title(f'{method_name} - {dataset_name}')
        ax_plot.legend()
        ax_plot.grid(True)
        
    output_plot = os.path.join(output_dir, f'{dataset_name}_focus_comparison.png')
    plt.tight_layout()
    plt.savefig(output_plot)
    plt.close()
    
if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, 'datasets')
    output_dir = os.path.join(base_dir, 'results')
    
    datasets = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']
    for ds in datasets:
        full_path = os.path.join(dataset_dir, ds)
        if os.path.exists(full_path):
            analyze_dataset(full_path, output_dir)
        else:
            print(f"Dataset not found: {full_path}")
