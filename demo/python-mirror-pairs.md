Solve LeetCode 3761 — Minimum Absolute Distance Between Mirror Pairs — in Python.

## Problem

Given an integer array `nums`, a **mirror pair** is a pair of indices `(i, j)` with `i < j`
such that `reverse(nums[i]) == nums[j]`, where `reverse(x)` reverses the decimal digits of `x`
and drops any leading zeros (e.g. `reverse(120) == 21`).

Return the **minimum absolute distance** `j - i` over all mirror pairs, or `-1` if no mirror
pair exists.

### Examples

```
Input:  nums = [12, 21, 45, 33, 54]
Output: 1
Explanation: (0,1) → reverse(12)=21=nums[1], distance 1.
             (2,4) → reverse(45)=54=nums[4], distance 2.
             Minimum is 1.

Input:  nums = [120, 21]
Output: 1
Explanation: reverse(120)=21=nums[1], distance 1.

Input:  nums = [21, 120]
Output: -1
Explanation: reverse(21)=12≠120 and reverse(120)=21≠21 (nums[0]=21, not 120).
             No mirror pair exists.
```

### Constraints

- `1 <= nums.length <= 10^5`
- `1 <= nums[i] <= 10^9`

## Requirements

Create `src/mirror_pairs.py` containing a `Solution` class:

```python
class Solution:
    def minAbsoluteDistance(self, nums: list[int]) -> int:
        ...
```

### Algorithm notes

- `reverse(x)` strips leading zeros: `reverse(120) == 21`, `reverse(100) == 1`.
- The same value can appear multiple times; every pair `(i, j)` where `i < j` and
  `reverse(nums[i]) == nums[j]` is valid.
- A palindrome number (e.g. `121`) is its own reverse, so two equal palindrome values at
  indices `i < j` form a mirror pair.
- Use a hash-map: as you scan left to right, for each index `j` look up the most recent
  index `i` where `nums[i] == reverse(nums[j])`. This gives O(n) average time.

## Test file

Create `tests/test_mirror_pairs.py` using **pytest** covering:

| Description | Input | Expected |
|---|---|---|
| Basic, two pairs | `[12, 21, 45, 33, 54]` | `1` |
| Leading-zero reverse | `[120, 21]` | `1` |
| No mirror pair | `[21, 120]` | `-1` |
| Single element | `[5]` | `-1` |
| Palindrome pair | `[121, 5, 121]` | `2` |
| Multiple pairs, pick closest | `[12, 21, 12, 21]` | `1` |
| Pair only at far ends | `[12, 4, 5, 6, 21]` | `4` |
| Reverse causes leading-zero strip | `[100, 1, 2]` | `1` (reverse(100)=1=nums[1]) |
| All same palindrome | `[11, 11, 11]` | `1` |
| No pair in large spread | `[123, 456, 789]` | `-1` |
