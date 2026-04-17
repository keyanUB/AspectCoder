Implement an EventEmitter class in JavaScript (ES2020, CommonJS module).

## Requirements

Create a file `src/event_emitter.js` containing an `EventEmitter` class.

### Interface

```js
class EventEmitter {
  on(event, listener) {}       // register a persistent listener; returns this (chainable)
  off(event, listener) {}      // remove a specific listener; returns this
  once(event, listener) {}     // register a one-time listener that auto-removes after first call; returns this
  emit(event, ...args) {}      // invoke all listeners for the event with the given args; returns true if any listeners fired, false otherwise
  removeAllListeners(event) {} // remove all listeners for event; if event omitted, clear everything; returns this
  listenerCount(event) {}      // return the number of active listeners for event
}

module.exports = { EventEmitter };
```

### Behaviour

- Listeners are called in registration order.
- `once` listeners are removed before they are invoked (so re-entrant emits inside a once listener do not fire it again).
- `off` with a listener function that was never registered is a no-op (no error).
- `emit` on an event with no listeners returns `false` without throwing.
- The same listener function registered twice with `on` fires twice per emit.

### Edge cases to handle

- Emitting during emit (re-entrant emit) must not corrupt the listener list.
- `off` called inside a listener must not cause other listeners in the same emit to be skipped.
- Passing a non-string event name should throw `TypeError`.
- Passing a non-function listener to `on`, `off`, or `once` should throw `TypeError`.

## Test file

Also create `tests/event_emitter.test.js` using Node's built-in `assert` module (no external test framework):
- on/emit basic round-trip
- multiple listeners fire in order
- once fires exactly once
- off removes only the specified listener
- re-entrant emit inside a listener works correctly
- removeAllListeners clears the correct scope
- listenerCount returns accurate counts
- TypeError thrown for invalid arguments
