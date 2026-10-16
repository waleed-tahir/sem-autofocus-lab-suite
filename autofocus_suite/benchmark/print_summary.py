import json

data = json.load(open('autofocus_suite/benchmark/results/ablation_results.json'))
print("=== ABLATION TOURNAMENT SUMMARY ===")
for ds, ds_data in data['datasets'].items():
    runs = ds_data['runs']
    print(f"\nDataset: {ds} (Total runs evaluated: {len(runs)})")
    exact = [r for r in runs if r['discrete_error'] == 0]
    print(f"  Exact 0-error combinations: {len(exact)}/{len(runs)}")
    exact_sorted = sorted(exact, key=lambda x: (x['wall_clock_ms'], x['frames_read']))
    if exact_sorted:
        best = exact_sorted[0]
        print(f"  WINNER (FASTEST EXACT): {best['search_name']} + {best['fmo_name']} (Anscombe: {best['use_anscombe']})")
        print(f"    Latency: {best['wall_clock_ms']} ms | Reads: {best['frames_read']} frames ({best['read_pct']}%) | Subframe Error: {best['subframe_error']} | PSR: {best['psr']} | Muni: {best['m_uni']}")
