Implement an LRU (Least Recently Used) cache in Python.

## Requirements

Create a file `src/lru_cache.py` containing an `LRUCache` class with the following interface:

```python
class LRUCache:
    def __init__(self, capacity: int) -> None: ...
    def get(self, key: int) -> int: ...          # return -1 if key not found
    def put(self, key: int, value: int) -> None: ...
```

### Behaviour

- `get(key)` returns the value for the given key, or `-1` if it does not exist. Accessing a key marks it as most recently used.
- `put(key, value)` inserts or updates the key-value pair. If inserting would exceed `capacity`, evict the least recently used entry first.
- Both operations must run in **O(1)** time.

### Edge cases to handle

- `capacity` of 1
- `get` on a key that was just evicted returns -1
- `put` with an existing key updates the value and refreshes recency
- `capacity` of 0 should raise `ValueError`

## Test file

Also create `tests/test_lru_cache.py` with pytest tests covering:
- Basic get/put round-trip
- Eviction of the least recently used entry
- Recency refresh on get
- Recency refresh on put of existing key
- capacity=1 edge case
- capacity=0 raises ValueError
