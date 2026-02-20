"""
Receipt Selection Module
Selects receipts to match a target amount using various strategies.
"""
from config import CURRENCY_SYMBOL, MAX_OVERAGE_ALLOWED, EXACT_MATCH_TOLERANCE


def select_receipts_by_target(receipts, target_amount, tolerance=None, max_overage=None):
    """
    Select receipts to match or get as close as possible to the target amount.
    
    Uses multiple strategies:
    1. Exact match
    2. Best fit without exceeding
    3. Closest match (may exceed by up to max_overage)
    
    Args:
        receipts: List of receipt dictionaries with 'amount' key
        target_amount: Target total amount to reach
        tolerance: Acceptable tolerance for "exact" match (default: from config)
        max_overage: Maximum amount allowed to exceed target (default: from config)
        
    Returns:
        List of selected receipt dictionaries
    """
    if not receipts:
        return []
    
    if target_amount <= 0:
        print("Warning: Target amount must be positive.")
        return []
    
    # Use config defaults if not specified
    if tolerance is None:
        tolerance = EXACT_MATCH_TOLERANCE
    if max_overage is None:
        max_overage = MAX_OVERAGE_ALLOWED
    
    # Sort receipts by amount (largest first)
    sorted_receipts = sorted(receipts, key=lambda r: r['amount'], reverse=True)
    
    # Strategy 1: Try to find an exact match or very close match
    selected = find_exact_match(sorted_receipts, target_amount, tolerance)
    if selected:
        print(f"  Found exact match (within {CURRENCY_SYMBOL}{tolerance})")
        return selected
    
    # Strategy 2: Find best combination without exceeding target
    selected = find_best_fit_subset(sorted_receipts, target_amount)
    if selected:
        total = sum(r['amount'] for r in selected)
        print(f"  Found best fit without exceeding target ({CURRENCY_SYMBOL}{total:.2f})")
        return selected
    
    # Strategy 3: Find closest match (may exceed target up to max_overage)
    selected = find_closest_match(sorted_receipts, target_amount, max_overage)
    if selected:
        total = sum(r['amount'] for r in selected)
        diff = abs(total - target_amount)
        if total > target_amount:
            print(f"  Found closest match ({CURRENCY_SYMBOL}{total:.2f}, exceeds by {CURRENCY_SYMBOL}{diff:.2f})")
        else:
            print(f"  Found closest match ({CURRENCY_SYMBOL}{total:.2f}, under by {CURRENCY_SYMBOL}{diff:.2f})")
        return selected
    
    return []


def find_exact_match(receipts, target, tolerance):
    """
    Find a combination of receipts that exactly matches the target
    (or within tolerance).
    """
    n = len(receipts)
    
    # Try all possible combinations (brute force for small sets)
    # For large sets, this should use dynamic programming
    if n <= 20:  # Brute force for small sets
        from itertools import combinations
        
        for r in range(1, n + 1):
            for combo in combinations(receipts, r):
                total = sum(receipt['amount'] for receipt in combo)
                if abs(total - target) <= tolerance:
                    return list(combo)
    else:
        # For larger sets, use dynamic programming
        return dynamic_programming_subset_sum(receipts, target, tolerance)
    
    return None


def find_best_fit_subset(receipts, target):
    """
    Find the combination of receipts that gets closest to target
    without exceeding it.
    """
    n = len(receipts)
    
    # Dynamic programming approach
    # dp[i][j] = (achievable, receipts_used)
    # i = receipt index, j = amount
    
    # Scale amounts to integers to avoid floating point issues
    scale = 100  # Assuming 2 decimal places
    target_scaled = int(target * scale)
    
    # Initialize DP table
    dp = {}
    dp[0] = []  # We can achieve 0 with no receipts
    
    for receipt in receipts:
        amount_scaled = int(receipt['amount'] * scale)
        new_dp = dp.copy()
        
        for current_amount, current_receipts in dp.items():
            new_amount = current_amount + amount_scaled
            if new_amount <= target_scaled:
                if new_amount not in new_dp or len(current_receipts) + 1 < len(new_dp[new_amount]):
                    new_dp[new_amount] = current_receipts + [receipt]
        
        dp = new_dp
    
    # Find the closest amount without exceeding
    if not dp:
        return None
    
    best_amount = max(dp.keys())
    return dp[best_amount] if best_amount > 0 else None


def find_closest_match(receipts, target, max_overage=100):
    """
    Find the combination that is closest to the target.
    Prefers combinations that don't exceed target + max_overage.
    
    Args:
        receipts: List of receipts
        target: Target amount
        max_overage: Maximum allowed overage (default: 100)
    """
    n = len(receipts)
    
    if n == 0:
        return None
    
    # Try greedy approach with overage limit
    selected = []
    current_total = 0
    
    # Sort by amount (largest first)
    sorted_receipts = sorted(receipts, key=lambda r: r['amount'], reverse=True)
    
    # Greedy: Add receipts until we meet target (can exceed up to max_overage)
    for receipt in sorted_receipts:
        if current_total < target:
            # Check if adding this receipt exceeds allowed overage
            potential_total = current_total + receipt['amount']
            if potential_total <= target + max_overage:
                selected.append(receipt)
                current_total += receipt['amount']
    
    # If we have selected receipts, return them
    if selected and current_total >= target * 0.5:  # At least 50% of target
        return selected
    
    # Fallback: Try to find smallest combination that exceeds but stays within limit
    best_combo = None
    best_diff = float('inf')
    
    from itertools import combinations
    for r in range(1, min(n + 1, 10)):  # Limit search to avoid timeout
        for combo in combinations(sorted_receipts, r):
            total = sum(receipt['amount'] for receipt in combo)
            diff = abs(total - target)
            
            # Prefer combinations close to target, within overage limit
            if total >= target and total <= target + max_overage:
                if diff < best_diff:
                    best_diff = diff
                    best_combo = list(combo)
            elif best_combo is None and diff < best_diff:
                # If no valid combo found yet, track best regardless
                best_diff = diff
                best_combo = list(combo)
    
    return best_combo if best_combo else [receipts[0]]


def dynamic_programming_subset_sum(receipts, target, tolerance):
    """
    Use dynamic programming to find subset sum close to target.
    """
    scale = 100
    target_scaled = int(target * scale)
    tolerance_scaled = int(tolerance * scale)
    
    n = len(receipts)
    amounts = [int(r['amount'] * scale) for r in receipts]
    
    # DP table: dp[i][j] = can we achieve sum j using first i receipts?
    max_sum = target_scaled + tolerance_scaled + 1
    dp = [[False] * max_sum for _ in range(n + 1)]
    parent = [[None] * max_sum for _ in range(n + 1)]
    
    # Base case
    dp[0][0] = True
    
    # Fill DP table
    for i in range(1, n + 1):
        for j in range(max_sum):
            # Don't take current receipt
            if dp[i-1][j]:
                dp[i][j] = True
                if parent[i][j] is None:
                    parent[i][j] = (i-1, j, False)
            
            # Take current receipt
            if j >= amounts[i-1] and dp[i-1][j - amounts[i-1]]:
                dp[i][j] = True
                if parent[i][j] is None:
                    parent[i][j] = (i-1, j - amounts[i-1], True)
    
    # Find closest sum to target within tolerance
    best_sum = None
    for j in range(max_sum):
        if dp[n][j]:
            if abs(j - target_scaled) <= tolerance_scaled:
                if best_sum is None or abs(j - target_scaled) < abs(best_sum - target_scaled):
                    best_sum = j
    
    if best_sum is None:
        return None
    
    # Backtrack to find selected receipts
    selected_indices = []
    i, j = n, best_sum
    
    while i > 0 and j > 0 and parent[i][j] is not None:
        prev_i, prev_j, taken = parent[i][j]
        if taken:
            selected_indices.append(i - 1)
        i, j = prev_i, prev_j
    
    return [receipts[idx] for idx in selected_indices]
