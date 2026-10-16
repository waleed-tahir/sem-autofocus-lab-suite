import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import yaml

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dataset_dir = os.path.join(base_dir, 'datasets')
output_dir = os.path.join(base_dir, 'results')

# The datasets specified by the user
datasets = ['pollen.spd1', 'pollen.spd2', 'pollen.spd3', 'pollen.spd5']

for dataset in datasets:
    dataset_path = os.path.join(dataset_dir, dataset)
    # Get all png files in the dataset
    image_paths = sorted(glob.glob(os.path.join(dataset_path, '*.png')))
    
    # Read working distances from yaml
    wd_file = os.path.join(dataset_path, f'{dataset}.WDs.yml')
    working_distances = []
    if os.path.exists(wd_file):
        with open(wd_file, 'r') as f:
            # PyYAML might fail on OpenCV's %YAML:1.0 header, so we skip it
            lines = f.readlines()
            if lines and lines[0].startswith('%YAML'):
                lines = lines[1:]
            content = ''.join(lines)
            data = yaml.safe_load(content)
            if data and 'WD' in data:
                working_distances = data['WD']
    
    variances = []
    
    for path in image_paths:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            mean, stddev = cv2.meanStdDev(img)
            var = stddev[0][0] ** 2
            mean_val = mean[0][0]
            
            # Normalised variance is var / mean
            if mean_val != 0:
                norm_var = var / mean_val
            else:
                norm_var = 0.0
            
            variances.append(norm_var)
            
    if variances:
        plt.figure()
        if len(working_distances) == len(variances):
            plt.plot(working_distances, variances, marker='o', linestyle='-', markersize=2)
            plt.xlabel('Working Distance (d)')
        else:
            plt.plot(variances, marker='o', linestyle='-', markersize=2)
            plt.xlabel('Image Index')
            
        plt.title(f'Normalised Variance for {dataset}')
        plt.ylabel('Normalised Variance')
        plt.grid(True)
        
        output_file = os.path.join(output_dir, f'{dataset}_norm_var.png')
        plt.savefig(output_file)
        plt.close()
        print(f"Saved plot to {output_file}")
    else:
        print(f"No valid images found in {dataset}")
