Implement a singly linked list in C.

## Requirements

Create a file `src/linked_list.c` and its header `src/linked_list.h`.

### Data structures

```c
typedef struct Node {
    int value;
    struct Node *next;
} Node;

typedef struct {
    Node *head;
    size_t size;
} LinkedList;
```

### Functions to implement

```c
LinkedList *ll_create(void);
void        ll_destroy(LinkedList *list);          // free all nodes and the list struct
int         ll_push_front(LinkedList *list, int value);  // returns 0 on success, -1 on alloc failure
int         ll_push_back(LinkedList *list, int value);   // returns 0 on success, -1 on alloc failure
int         ll_pop_front(LinkedList *list, int *out);    // returns 0 on success, -1 if empty
int         ll_remove(LinkedList *list, int value);      // remove first occurrence; returns 0 if found, -1 if not
int         ll_contains(const LinkedList *list, int value); // returns 1 if found, 0 if not
size_t      ll_size(const LinkedList *list);
```

### Requirements

- No memory leaks: every allocation must have a matching free path.
- `ll_destroy(NULL)` must be a no-op (do not crash).
- Functions that allocate must handle `malloc` returning NULL and propagate the error via return code.
- Thread safety is not required.

## Test file

Also create `tests/test_linked_list.c` using a simple assert-based test harness (no external framework):
- push_front and push_back add elements in the correct order
- pop_front on an empty list returns -1
- ll_remove on a missing value returns -1
- ll_contains returns correct results before and after removal
- ll_destroy frees without crashing (run under valgrind to verify)
