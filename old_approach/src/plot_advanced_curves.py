import json
import matplotlib.pyplot as plt
import numpy as np
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_file = os.path.join(base_dir, 'results', 'advanced_benchmark.json')

with open(results_file, 'r') as f:
    data = json.load(f)
    
ds_name = 'pollen.spd1'
measures = data[ds_name]['measures']

plt.figure(figsize=(12, 6))

for m_name, m_data in measures.items():
    curve = np.array(m_data['curve'])
    # Normalize curve between 0 and 1
    curve = (curve - curve.min()) / (curve.max() - curve.min() + 1e-9)
    # Highlight the 2nd order ones with thicker/different lines
    if m_name in ['VoL', 'LoG']:
        plt.plot(curve, label=m_name, linewidth=2.5)
    else:
        plt.plot(curve, label=m_name, linestyle='--', alpha=0.7)
    
plt.title(f'Focus Measure Comparison (Normalized) - {ds_name}')
plt.xlabel('Image Index (Working Distance)')
plt.ylabel('Normalized Focus Score')
plt.legend()
plt.grid(True, alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(base_dir, 'results', 'advanced_measures_comparison.png'))
plt.close()
