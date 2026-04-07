def calculate_score(time_limit: int, time_taken: float, wrong_attempts: int) -> float:
    """
    Score formula:
      base_score   = 100
      time_bonus   = (remaining_time / time_limit) * 40
      penalty      = wrong_attempts * 10
      final        = max(0, base + time_bonus - penalty)
    """
    base_score = 100
    remaining_time = max(0, time_limit - time_taken)
    time_bonus = (remaining_time / time_limit) * 40 if time_limit > 0 else 0
    penalty = wrong_attempts * 10
    final_score = base_score + time_bonus - penalty
    return round(max(0.0, final_score), 2)
