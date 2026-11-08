# Autofocus Algorithm Module

This directory contains standalone, modular Python implementations of the key autofocus search and focus score algorithms extracted from the Scanning Electron Microscope (SEM) autofocus suite and `autofocus_core.py`.

---

## Directory Structure

| File | Description | Category |
| :--- | :--- | :--- |
| [`gradient_descent_search.py`](file:///c:/Users/PC/Desktop/ali/algorithm/gradient_descent_search.py) | Derivative-based gradient ascent with fake-maximum rejection and basin restarts | Search Algorithm |
| [`coarse_quadratic_search.py`](file:///c:/Users/PC/Desktop/ali/algorithm/coarse_quadratic_search.py) | Full two-stage autofocus: coarse search (`gradient` or `grid`) + fine quadratic fit (`coarse_fit` / `coarse_quadratic`) | Search Algorithm |
| [`quadratic_fit.py`](file:///c:/Users/PC/Desktop/ali/algorithm/quadratic_fit.py) | Parabolic curve fitting ($f(d) = A_0 + A_1 d + A_2 d^2$) for sub-frame continuous peak lock and $R^2$ | Fine Refinement |
| [`coarse_and_fine_search.py`](file:///c:/Users/PC/Desktop/ali/algorithm/coarse_and_fine_search.py) | Two-stage hybrid coarse grid sweep and fine bracket refinement ($O(\sqrt{N})$ complexity) | Search Algorithm |
| [`global_scan_search.py`](file:///c:/Users/PC/Desktop/ali/algorithm/global_scan_search.py) | Full sequential scan baseline ($O(N)$ ground truth reference) | Search Algorithm |
| [`normalized_variance.py`](file:///c:/Users/PC/Desktop/ali/algorithm/normalized_variance.py) | Normalized Variance and Mean-Normalized Variance contrast metrics | Focus Score |
| [`laplacian.py`](file:///c:/Users/PC/Desktop/ali/algorithm/laplacian.py) | Variance of Laplacian (VoL), Laplacian of Gaussian (LoG), and Modified Laplacian (SML) | Focus Score |
| [`__init__.py`](file:///c:/Users/PC/Desktop/ali/algorithm/__init__.py) | Package initialization exposing all algorithms and search structures | Package Entry |
| [`test_extracted_algorithms.py`](file:///c:/Users/PC/Desktop/ali/algorithm/test_extracted_algorithms.py) | Comprehensive test suite covering unit tests and synthetic/real focal stacks | Test Suite |

---

## 1. Search Algorithms

### A. Gradient Descent / Ascent Search (`gradient_descent_search.py`)
Derivative-based ascent algorithm with noise-floor verification:
- **Derivative-Based Ascent:** Computes centered finite differences $g_n = \frac{f(d+h) - f(d-h)}{2h}$ with adaptive baseline span $h = \max(\delta, \lfloor\beta/2\rfloor, 1)$.
- **Decreasing Step Factor:** Moves via $d_{n+1} = d_n + \Gamma_n \cdot \Lambda_n$, where $\Gamma_n = \text{sign}(g_n)$ and $\Lambda_n = \beta \cdot (f_0 / f_n)^2$. The step parameter $\beta$ is halved each time the direction reverses (overshoot).
- **Fake-Maximum Rejection:** Compares candidate peak against symmetric probes at distances $\pm dist$ and $\pm 2\cdot dist$, requiring peak prominence $> k \cdot \sigma$ over the noise floor.
- **Basin Relocation:** If a candidate is rejected as noise, the search relocates to the highest probe or the largest unexplored stretch of frames.

```python
from algorithm import gradient_descent_search

def evaluate_frame(idx: int) -> float:
    ...
    return score

result = gradient_descent_search(evaluate_frame, max_idx=199)
print(f"Optimal Focus Peak : Frame {result.best_idx}")
print(f"Noise Verified     : {result.verified}")
print(f"Restarts Count     : {result.restarts}")
print(f"Frames Evaluated   : {len(result.evals)}")
```

### B. Coarse-Fit / Coarse-Quadratic Search (`coarse_quadratic_search.py`)
Two-stage autofocus search combining coarse search with fine quadratic fitting:
- **Stage 1 (Coarse Search):** Rapidly finds the discrete peak using either:
  * `coarse_method="gradient"` (default): Gradient ascent with fake-maximum rejection.
  * `coarse_method="grid"`: Sparse grid sweep with step $s = \max(3, \text{round}(\sqrt{N}))$.
- **Stage 2 (Fine Quadratic Fit):** Fits a parabola $f(d) = A_0 + A_1 d + A_2 d^2$ on $[k_c - w, k_c + w]$ around coarse peak $k_c$, locating continuous sub-frame peak $z^* = k_c - \frac{A_1}{2 A_2 \cdot \text{step}}$ and goodness of fit $R^2$.
- **Exposed Aliases:** `coarse_quadratic`, `coarse_fit`, `coarse_quadratic_search`, `coarse_fit_search`.

```python
from algorithm import coarse_quadratic, coarse_fit

# Using coarse_quadratic (gradient coarse + quadratic fit)
res_quad = coarse_quadratic(evaluate_frame, max_idx=199)
print(f"Discrete Coarse Peak: Frame {res_quad.coarse_idx}")
print(f"Sub-Frame Fine Peak : Frame {res_quad.fine_idx:.3f}")
print(f"Goodness of Fit R^2 : {res_quad.fit_r2:.4f}")

# Using coarse_fit (grid coarse + quadratic fit)
res_grid_fit = coarse_fit(evaluate_frame, max_idx=199, coarse_method="grid")
print(f"Sub-Frame Peak (Grid Fit): Frame {res_grid_fit.fine_idx:.3f}")
```

### C. Quadratic Curve Fitting (`quadratic_fit.py`)
Standalone fine refinement module:
- Fits $f(d) = A_0 + A_1 d + A_2 d^2$ using Z-score normalized conditioning.
- Rejects convex fits ($A_2 \ge 0$, no maximum) and vertices outside the bracket window.
- Returns `QuadraticFitResult` supporting both attribute access (`.ok`, `.idx`, `.value`, `.r2`, `.coeffs`) and dictionary access (`['ok']`, `['idx']`).

```python
from algorithm import quadratic_fit

fit = quadratic_fit(evaluate_frame, coarse_idx=73, max_idx=199, half_window=10)
if fit.ok:
    print(f"Continuous Peak: Frame {fit.idx:.3f}, R2 = {fit.r2:.4f}")
```

### D. Coarse-and-Fine Hybrid Search (`coarse_and_fine_search.py`)
- Two-stage grid sweep + local fine bracket refinement ($O(\sqrt{N})$ complexity).
- Reduces frame reads by ~85–92%.

### E. Global Linear Scan Search (`global_scan_search.py`)
- Exhaustive sequential evaluation across all frames ($O(N)$ ground truth reference).

---

## 2. Focus Score Algorithms

### A. Normalized Variance (`normalized_variance.py`)
- **Standard Normalized Variance:**
  $$\Phi_{\text{NV}} = \frac{\text{Var}(I)}{\text{Mean}(I) + \epsilon}$$
- **Mean-Normalized Variance:**
  $$\Phi_{\text{MNV}} = \frac{\text{Var}(I)}{\text{Mean}(I)^2 + \epsilon}$$

### B. Laplacian (`laplacian.py`)
- **Variance of Laplacian (VoL):** $\Phi_{\text{VoL}} = \text{Var}(\nabla^2 I)$
- **Laplacian of Gaussian (LoG):** $\Phi_{\text{LoG}} = \text{Var}(\nabla^2 (G_\sigma * I))$
- **Sum of Modified Laplacian (SML):** $\Phi_{\text{SML}} = \frac{1}{N} \sum \left( \left|\frac{\partial^2 I}{\partial x^2}\right| + \left|\frac{\partial^2 I}{\partial y^2}\right| \right)^2$

---

## Running the Tests

To verify all algorithms (synthetic benchmarks and real SEM focal stacks):

```bash
python algorithm/test_extracted_algorithms.py
```
