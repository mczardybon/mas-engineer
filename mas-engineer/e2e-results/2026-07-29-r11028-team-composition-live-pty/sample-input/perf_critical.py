"""Performance-critical code for perf-eval team."""
import time

def find_duplicates_slow(items: list) -> list:
    """O(n^2) duplicate finder — has performance issues."""
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                if items[i] not in duplicates:
                    duplicates.append(items[i])
    return duplicates


def hot_path(items: list) -> int:
    """Called millions of times — must be fast."""
    total = 0
    for x in items:
        if x > 0:
            if x < 100:
                if x % 2 == 0:
                    total += x * 2
                else:
                    total += x
    return total


def inefficient_search(arr: list, target: int) -> int:
    """Linear search where binary search would be appropriate (sorted array)."""
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
