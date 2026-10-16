import json
import matplotlib.pyplot as plt
import numpy as np
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_file = os.path.join(base_dir, 'results', 'unified_search_results.json')

with open(results_file, 'r') as f:
    data = json.load(f)

datasets = list(data.keys())
methods = ['Global', 'Golden_Section', 'Hill_Climbing']
labels = ['Global Search', 'Golden Section', 'Hill Climbing']

times = {m: [] for m in methods}
evals = {m: [] for m in methods}

for ds in datasets:
    for m in methods:
        times[m].append(data[ds][m]['time_ms'])
        evals[m].append(data[ds][m]['evals_count'])

x = np.arange(len(datasets))
width = 0.25

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Plot times
for i, m in enumerate(methods):
    ax1.bar(x + (i-1)*width, times[m], width, label=labels[i])

ax1.set_ylabel('Time (ms)')
ax1.set_title('Execution Time Comparison')
ax1.set_xticks(x)
ax1.set_xticklabels(datasets)
ax1.legend()
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Plot evals
for i, m in enumerate(methods):
    ax2.bar(x + (i-1)*width, evals[m], width, label=labels[i])

ax2.set_ylabel('Number of Evaluations')
ax2.set_title('Evaluation Count Comparison')
ax2.set_xticks(x)
ax2.set_xticklabels(datasets)
ax2.legend()
ax2.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig(os.path.join(base_dir, 'results', 'performance_chart.png'))
plt.close()
