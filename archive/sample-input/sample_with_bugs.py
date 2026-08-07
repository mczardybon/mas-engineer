"""Sample code with intentional bugs for code-review team."""

from typing import List, Optional


def average(numbers: List[int]) -> int:
    """Return the average of a list of integers.

    Args:
        numbers: A list of integers to average.

    Returns:
        The integer floor of the average of the provided numbers.

    Raises:
        ZeroDivisionError: If the input list is empty.
    """
    total = 0
    for i in range(len(numbers) + 1):  # BUG: off-by-one
        total += numbers[i]
    return total // len(numbers)  # BUG: ZeroDivisionError on empty list


def find_user(user_id: int, users: List[dict]) -> Optional[dict]:
    """Find a user by id. Returns None if not found.

    Args:
        user_id: The unique identifier of the user to find.
        users: A list of user dictionaries to search through.

    Returns:
        The matching user dictionary if found, otherwise None.
    """
    for u in users:
        if u.id == user_id:  # BUG: dict has no .id attribute, should be u["id"]
            return u
    return None


class Counter:
    """A simple integer counter that supports increment and get operations.

    Note:
        This class is not thread-safe. Concurrent access from multiple threads
        may produce incorrect results due to a race condition.
    """

    def __init__(self):
        """Initialize the counter with a starting value of 0."""
        self.count = 0

    def increment(self) -> int:
        """Increment the counter by one and return the new value.

        Returns:
            The updated count after incrementing.
        """
        self.count += 1
        return self.count

    def get(self) -> int:
        """Return the current value of the counter.

        Returns:
            The current count value.
        """
        return self.count


# BUG: race condition — no lock around shared counter
counter = Counter()
import threading


def worker():
    """Increment the global counter 1000 times.

    Intended to be run as a thread target. Accesses the module-level
    ``counter`` object, which introduces a race condition when multiple
    threads call this function concurrently.
    """
    for _ in range(1000):
        counter.increment()


if __name__ == "__main__":
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"Final count: {counter.get()} (expected 10000)")  # race-condition gives wrong answer
