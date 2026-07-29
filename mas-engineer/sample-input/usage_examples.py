"""Usage examples for the public API in sample_with_bugs.py.

This module demonstrates the intended usage of each public function and
class defined in ``sample_with_bugs.py``.  Known bugs in the source are
documented alongside the examples so consumers can anticipate the actual
(sometimes incorrect) behaviour.

.. caution::

   The source file contains intentional bugs.  These examples show the
   *intended* contract; test or call the source at your own risk.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from sample_with_bugs import average, find_user, Counter


# ===========================================================================
# 1. average()
# ===========================================================================

def examples_average() -> None:
    """Demonstrate the intended use of ``average()``.

    **Known bugs**
        - Off-by-one in the loop (``range(len(numbers) + 1)``) → raises
          ``IndexError`` on most non-empty inputs.
        - Missing empty-list guard → ``ZeroDivisionError`` when input is ``[]``.
    """

    # -- Normal case (triggers off-by-one IndexError) -----------------------
    nums = [1, 2, 3, 4, 5]
    try:
        result = average(nums)
        print(f"average({nums}) = {result}  (expected 3)")
    except IndexError:
        print(f"average({nums}) → IndexError (bug: off-by-one loop)")

    # -- Single-element list -------------------------------------------------
    try:
        result = average([10])
        print(f"average([10]) = {result}  (expected 10)")
    except IndexError:
        print("average([10]) → IndexError (bug: off-by-one loop)")

    # -- All zeros -----------------------------------------------------------
    try:
        result = average([0, 0, 0])
        print(f"average([0, 0, 0]) = {result}  (expected 0)")
    except IndexError:
        print("average([0, 0, 0]) → IndexError (bug: off-by-one loop)")

    # -- Negative numbers ----------------------------------------------------
    try:
        result = average([-5, 0, 5])
        print(f"average([-5, 0, 5]) = {result}  (expected 0)")
    except IndexError:
        print("average([-5, 0, 5]) → IndexError (bug: off-by-one loop)")

    # -- Empty list (triggers IndexError first — off-by-one loop iterates) ---
    try:
        average([])
    except IndexError:
        print("average([]) → IndexError (bug: off-by-one even on empty list)")
    except ZeroDivisionError:
        print("average([]) → ZeroDivisionError (would fire if loop were fixed)")


# ===========================================================================
# 2. find_user()
# ===========================================================================

def examples_find_user() -> None:
    """Demonstrate the intended use of ``find_user()``.

    **Known bugs**
        - Accesses attribute ``u.id`` instead of key ``u["id"]``.  Dicts do
          not have a ``.id`` attribute → ``AttributeError`` at runtime.
    """

    users: list[dict] = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]

    # -- User found --------------------------------------------------------
    # Intended: returns {"id": 1, "name": "Alice"}
    # Actual:   AttributeError — dict has no .id attribute
    try:
        user = find_user(1, users)
    except AttributeError:
        print("find_user(1, ...) → AttributeError (u.id vs u['id'])")
    else:
        print(f"find_user(1, ...) → {user}")

    # -- User not found ----------------------------------------------------
    try:
        user = find_user(99, users)
    except AttributeError:
        print("find_user(99, ...) → AttributeError (same root cause)")
    else:
        # *If* the bug is fixed, this branch runs.
        expected: str = "None"
        print(f"find_user(99, ...) → {user}  (expected {expected})")

    # -- Empty user list ---------------------------------------------------
    try:
        user = find_user(1, [])
    except AttributeError:
        print("find_user(1, []) → AttributeError")
    else:
        print(f"find_user(1, []) → {user}  (expected None)")


# ===========================================================================
# 3. Counter
# ===========================================================================

def examples_counter() -> None:
    """Demonstrate the intended use of ``Counter``.

    **Known bugs**
        - No locking → race condition when multiple threads call
          ``increment()`` concurrently (see :func:`examples_race_condition`).
    """

    # -- Basic single-threaded usage ---------------------------------------

    c = Counter()
    assert c.get() == 0, "New counter should start at 0"

    c.increment()                     # 0 → 1
    c.increment()                     # 1 → 2
    c.increment()                     # 2 → 3

    print(f"After 3 increments: count = {c.get()}  (expected 3)")

    # -- Chain-like usage (method returns the new value) --------------------
    val = c.increment()               # 3 → 4
    print(f"increment() returned {val}  (expected 4)")

    # -- Reset by re-initialising ------------------------------------------
    c2 = Counter()
    for i in range(10):
        c2.increment()
    print(f"10 increments: count = {c2.get()}  (expected 10)")


def examples_race_condition() -> None:
    """Demonstrate the race condition in the module-level ``counter``.

    The global ``counter`` in ``sample_with_bugs`` is shared across threads
    with **no lock**, so the final count is almost always less than the
    expected value of ``10 × 1000 = 10_000``.
    """

    # Replicate the same pattern from __main__ in the source file.
    import threading
    from sample_with_bugs import counter

    # Reset counter (it was already incremented by __main__ if that ran).
    counter.count = 0

    # Sanity check
    assert counter.get() == 0

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    actual = counter.get()
    expected = 10_000
    print(f"Race-condition test: count = {actual}  (expected {expected})")
    if actual != expected:
        print("  → Race condition confirmed (missing lock)")


def worker():
    """Increment the module-level counter 1000 times."""
    from sample_with_bugs import counter
    for _ in range(1000):
        counter.increment()


# ===========================================================================
# 4. Combined / real-world-style scenario
# ===========================================================================

def example_workflow() -> None:
    """A short workflow that ties several API pieces together."""
    print("\n--- Workflow example ---")

    # 1. Build a user list
    users = [
        {"id": 10, "name": "Diana", "scores": [8, 9, 10]},
        {"id": 20, "name": "Eve", "scores": [6, 7, 5]},
    ]

    # 2. Try to look up a user (catches the known AttributeError)
    try:
        user = find_user(10, users)
    except AttributeError:
        user = None
        print("[find_user skipped — known bug]")

    # 3. Compute averages for each user's scores (if bugs are fixed)
    #    (Here we call average directly as a demonstration — the off-by-one
    #     bug will surface.)
    for u in users:
        try:
            avg = average(u["scores"])
        except (IndexError, ZeroDivisionError) as exc:
            print(f"  average({u['name']}.scores) → {type(exc).__name__} (bug)")
        else:
            print(f"  average({u['name']}.scores) = {avg}")

    # 4. Use a Counter to track something
    visit_counter = Counter()
    for u in users:
        visit_counter.increment()
    print(f"  Users processed: {visit_counter.get()}")


# ===========================================================================
# Run all examples
# ===========================================================================

if __name__ == "__main__":
    print("=== average() examples ===")
    examples_average()

    print("\n=== find_user() examples ===")
    examples_find_user()

    print("\n=== Counter examples ===")
    examples_counter()

    print("\n=== Race condition demo ===")
    examples_race_condition()

    example_workflow()
