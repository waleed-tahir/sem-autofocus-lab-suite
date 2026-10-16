import math

def global_search(eval_func, max_idx, **kwargs):
    """
    Evaluates every single index in the range [0, max_idx].
    Returns the index of the maximum value and the dictionary of evaluations.
    """
    evals = {}
    best_idx = 0
    best_val = -float('inf')
    
    for i in range(max_idx + 1):
        val = eval_func(i)
        evals[i] = val
        if val > best_val:
            best_val = val
            best_idx = i
            
    return best_idx, evals


def hill_climbing_search(eval_func, max_idx, start_idx=0, initial_step=10, max_iter=200):
    """
    Hill climbing search to find the peak faster.
    """
    evals = {}
    
    def f(x):
        x = max(0, min(max_idx, int(x)))
        if x not in evals:
            evals[x] = eval_func(x)
        return evals[x]
        
    current = start_idx
    step = initial_step
    
    # Determine initial direction, enforcing positive direction if at 0
    direction = 1
    if current == 0:
        direction = 1
    elif current == max_idx:
        direction = -1
    else:
        if f(current + step) < f(current):
            direction = -1
        
    iterations = 0
    while step > 0 and iterations < max_iter:
        iterations += 1
        next_pos = current + direction * step
        # Clamp to valid range instead of reversing at boundary
        next_pos = max(0, min(max_idx, next_pos))
        
        if next_pos == current:
            # At boundary, can't move further in this direction
            step = step // 2
            direction = -direction
            continue
            
        if f(next_pos) > f(current):
            current = next_pos
        else:
            # Passed the peak
            step = step // 2
            direction = -direction

    # Ensure local neighbors are evaluated for quadratic fitting later
    for i in [current - 1, current, current + 1]:
        f(i)
        
    # Find the max among all evaluated points to be safe
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    
    # Also evaluate neighbors of best_idx
    for i in [best_idx - 1, best_idx, best_idx + 1]:
        f(i)
        
    return best_idx, evals


def golden_section_search(eval_func, max_idx, start_idx=None, **kwargs):
    """
    Golden Section Search for finding the peak of a unimodal function.
    Properly reuses evaluations for O(1) step cost.
    """
    evals = {}
    
    def f(x):
        x = max(0, min(max_idx, int(round(x))))
        if x not in evals:
            evals[x] = eval_func(x)
        return evals[x]
        
    golden_ratio = (math.sqrt(5) - 1) / 2
    start_idx = start_idx if start_idx is not None else kwargs.get('start_idx', max_idx // 2)
    step = max(5.0, float(max_idx) * 0.05)  # 5% of range or 5
    
    current = float(start_idx)
    direction = 1 if f(current + step) > f(current) else -1
    
    # Bracket the maximum
    a_bracket = current
    while True:
        next_pos = current + direction * step
        if next_pos < 0 or next_pos > max_idx:
            break
        if f(next_pos) <= f(current):
            break
        current = next_pos
        step *= 1.5  # Accelerate bracketing
        
    if direction == 1:
        a = max(0.0, a_bracket)
        b = min(float(max_idx), current + step)
    else:
        a = max(0.0, current - step)
        b = min(float(max_idx), a_bracket)
    
    c = b - golden_ratio * (b - a)
    d = a + golden_ratio * (b - a)
    
    fc = f(c)
    fd = f(d)
    
    while abs(b - a) > 2.0:
        if fc > fd:
            # Peak is to the left of d
            b = d
            d = c
            fd = fc
            c = b - golden_ratio * (b - a)
            fc = f(c)
        else:
            # Peak is to the right of c
            a = c
            c = d
            fc = fd
            d = a + golden_ratio * (b - a)
            fd = f(d)
        
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    
    # Evaluate immediate neighbors for quadratic fitting
    for i in [best_idx - 1, best_idx, best_idx + 1]:
        f(i)
        
    return best_idx, evals


def momentum_hill_climbing(eval_func, max_idx, start_idx=0, initial_velocity=10, momentum_decay=0.8, max_iter=200):
    """
    Gradient ascent with momentum. Helps push through small local maxima.
    """
    evals = {}
    
    def f(x):
        x = max(0, min(max_idx, int(round(x))))
        if x not in evals:
            evals[x] = eval_func(x)
        return evals[x]
        
    current = start_idx
    velocity = float(initial_velocity)
    
    # Determine initial direction securely
    if current == 0:
        velocity = abs(velocity)
    elif current == max_idx:
        velocity = -abs(velocity)
    else:
        if f(current + velocity) < f(current):
            velocity = -velocity
        
    iterations = 0
    while abs(velocity) >= 1 and iterations < max_iter:
        iterations += 1
        next_pos = current + int(round(velocity))
        if next_pos < 0 or next_pos > max_idx:
            velocity = -velocity * momentum_decay
            continue
            
        if f(next_pos) > f(current):
            current = next_pos
        else:
            # Reverses and dampens velocity
            velocity = -velocity * momentum_decay

    # Evaluate neighbors
    for i in [current - 1, current, current + 1]:
        f(i)
        
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    for i in [best_idx - 1, best_idx, best_idx + 1]:
        f(i)
        
    return best_idx, evals


def newton_raphson_search(eval_func, max_idx, start_idx=0, max_iter=30):
    """
    Estimates 1st and 2nd derivative to model local parabola and jump to peak.
    Uses proper forward/backward differences at boundaries.
    """
    evals = {}
    
    def f(x):
        x = max(0, min(max_idx, int(round(x))))
        if x not in evals:
            evals[x] = eval_func(x)
        return evals[x]
        
    def get_derivs(x):
        c = int(round(x))
        if c <= 0:
            f0 = f(0); f1 = f(1); f2 = f(2)
            d1 = f1 - f0
            d2 = f2 - 2*f1 + f0
        elif c >= max_idx:
            f0 = f(max_idx); fm1 = f(max_idx-1); fm2 = f(max_idx-2)
            d1 = f0 - fm1
            d2 = f0 - 2*fm1 + fm2
        else:
            f0 = f(c); fp = f(c+1); fm = f(c-1)
            d1 = (fp - fm) / 2.0
            d2 = fp - 2*f0 + fm
        return f0, d1, d2

    current = float(start_idx)
    for _ in range(max_iter):
        f_val, d1, d2 = get_derivs(current)
        
        if d2 >= 0:
            if abs(d1) < 1e-6:
                step = 10.0 if current < max_idx / 2 else -10.0
            else:
                step = 5.0 if d1 > 0 else -5.0
        else:
            step = -d1 / d2
            
        step = max(-30.0, min(30.0, step))
            
        if abs(step) < 0.5:
            break
            
        next_pos = current + step
        next_pos = max(0.0, min(float(max_idx), next_pos))
        
        # Cycle detection: try smaller steps, then opposite direction
        rounded = int(round(next_pos))
        if rounded in evals:
            step /= 2.0
            next_pos = current + step
            next_pos = max(0.0, min(float(max_idx), next_pos))
            rounded = int(round(next_pos))
            if rounded in evals:
                step = -step / 2.0
                next_pos = current + step
                next_pos = max(0.0, min(float(max_idx), next_pos))
                if int(round(next_pos)) in evals:
                    break
        
        if abs(next_pos - current) < 1e-6:
            break
        current = next_pos
        
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    for i in [best_idx - 1, best_idx, best_idx + 1]:
        f(i)
        
    return best_idx, evals


def secant_search(eval_func, max_idx, start_idx=0, max_iter=30):
    """
    Secant search algorithm, root finding applied to the derivative.
    Properly handles boundaries for derivative approximation.
    """
    evals = {}
    def f(x):
        x = max(0, min(max_idx, int(round(x))))
        if x not in evals:
            evals[x] = eval_func(x)
        return evals[x]
        
    def f_prime(x):
        c = int(round(x))
        if c <= 0:
            return f(1) - f(0)
        elif c >= max_idx:
            return f(max_idx) - f(max_idx-1)
        else:
            return (f(c+1) - f(c-1)) / 2.0
        
    x0 = float(start_idx)
    df_init = f_prime(x0)
    x1 = float(start_idx + (10.0 if df_init > 0 else -10.0))
    x1 = max(0.0, min(float(max_idx), x1))
    
    for _ in range(max_iter):
        df0 = f_prime(x0)
        df1 = f_prime(x1)
        
        d2_approx = (df1 - df0) / (x1 - x0) if x1 != x0 else 0
        if abs(df1 - df0) < 1e-4 or d2_approx > 0:
            step = 10.0 if df1 > 0 else -10.0
        else:
            step = -df1 * (x1 - x0) / (df1 - df0)
        
        step = max(-30.0, min(30.0, step))
        x_next = x1 + step
        x_next = max(0.0, min(float(max_idx), x_next))
        
        if round(x_next) in evals:
            step /= 2.0
            x_next = x1 + step
            x_next = max(0.0, min(float(max_idx), x_next))
            if round(x_next) in evals:
                break
        
        if abs(x_next - x1) < 0.5:
            x1 = x_next
            break
            
        if abs(x_next - x0) < 1e-6:
            break
            
        x0 = x1
        x1 = x_next
        
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    for i in [best_idx - 1, best_idx, best_idx + 1]:
        f(i)
        
    return best_idx, evals
