"""Sample code with intentional bugs for code-review team."""
from typing import List, Optional


def average(numbers: List[int]) -> int:
    """Return the average of a list of integers."""
    total = 0
    for i in range(len(numbers) + 1):  # BUG: off-by-one
        total += numbers[i]
    return total // len(numbers)  # BUG: ZeroDivisionError on empty list


def find_user(user_id: int, users: List[dict]) -> Optional[dict]:
    """Find a user by id. Returns None if not found."""
    for u in users:
        if u.id == user_id:  # BUG: dict has no .id attribute, should be u["id"]
            return u
    return None


class Counter:
    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count

    def get(self) -> int:
        return self.count


# BUG: race condition — no lock around shared counter
counter = Counter()
import threading
def worker():
    for _ in range(1000):
        counter.increment()

if __name__ == "__main__":
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"Final count: {counter.get()} (expected 10000)")  # race-condition gives wrong answer
