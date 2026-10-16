import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import sys

def analyze_dataset(dataset_path, output_dir='.'):
    image_paths = sorted(glob.glob(os.path.join(dataset_path, '*.png')))
    if not image_paths:
        print(f"No images found in {dataset_path}")
        return

    variances = []
    
    for path in image_paths:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            mean, stddev = cv2.meanStdDev(img)
            var = stddev[0][0] ** 2
            mean_val = mean[0][0]
            norm_var = var / mean_val if mean_val != 0 else 0.0
            variances.append(norm_var)
            
    # We use 0-based index for consistency with other scripts
    indices = np.arange(0, len(variances))
    
    # Coarse sharpest image
    max_idx = np.argmax(variances)
    coarse_focus_val = variances[max_idx]
    coarse_image_path = image_paths[max_idx]
    coarse_index = indices[max_idx]
    
    # Quadratic curve fitting around the coarse peak
    # y = ax^2 + bx + c
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

    # Calculate physical positions
    # stepsize 10um = 0.01mm, min WD = 10mm (at index 0)
    coarse_wd = 10.0 + coarse_index * 0.01
    fine_wd = 10.0 + fine_index * 0.01

    print(f"--- Analysis for {dataset_path} ---")
    print(f"Coarse sharpest image: {os.path.basename(coarse_image_path)}")
    print(f"Focus value (Normalized Variance): {coarse_focus_val:.4f}")
    print(f"Coarse position (Index): {coarse_index}")
    print(f"Coarse position (WD): {coarse_wd:.4f} mm")
    print(f"Fine position (Index): {fine_index:.4f}")
    print(f"Fine position (WD): {fine_wd:.4f} mm\n")
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Display the coarse image
    img = cv2.imread(coarse_image_path)
    if img is not None:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ax1.imshow(img_rgb)
    ax1.set_title(f"Coarse Sharpest Image\n{os.path.basename(coarse_image_path)}")
    ax1.axis('off')
    
    # Plot the variance curve
    ax2.plot(indices, variances, marker='o', markersize=2, label='Normalised Variance')
    ax2.axvline(x=coarse_index, color='r', linestyle='--', label=f'Coarse Peak (idx={coarse_index})')
    ax2.axvline(x=fine_index, color='g', linestyle='-', label=f'Fine Peak (idx={fine_index:.2f})')
    
    # If a valid parabola was fitted, plot it locally
    if max_idx > 0 and max_idx < len(variances) - 1 and a < 0:
        x_fit = np.linspace(coarse_index - 1.5, coarse_index + 1.5, 50)
        y_fit = a * x_fit**2 + b * x_fit + c
        ax2.plot(x_fit, y_fit, 'k:', label='Quadratic Fit')
        
    ax2.set_xlabel('Image Index')
    ax2.set_ylabel('Normalised Variance')
    ax2.set_title(f'Focus Measure - {os.path.basename(dataset_path)}')
    ax2.legend()
    ax2.grid(True)
    
    dataset_name = os.path.basename(dataset_path)
    output_plot = os.path.join(output_dir, f'{dataset_name}_focus_analysis.png')
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
