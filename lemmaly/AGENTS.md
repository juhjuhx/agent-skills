# Lemmaly Rule Catalog (compiled)

Full compiled view of every CLI rule with hand-authored Incorrect/Correct examples and escalation path. Generated from `rules/*.json` and `skills/lemmaly/rules/*.md`.

For per-rule documents, load `skills/lemmaly/rules/<rule-id>.md`. For the deterministic CLI, run `node cli/lemmaly.js scan <path>`.


## CRITICAL — will break or scale-fail in production

### `cs-async-void` — csharp

# async void — exceptions are unobserved and crash the process

`async void` cannot be awaited. Exceptions raised inside are unobserved and crash the process — they bypass `try/catch` at the call site. The only legitimate use is true event handlers (e.g. `OnClick`).

## Fix

Return Task. async void is only acceptable for true event handlers (OnClick, etc.).

## Incorrect

```csharp
public async void DoWork() {
  await Task.Delay(100);
  throw new Exception("boom"); // crashes the process
}
```

## Correct

```csharp
public async Task DoWork() {
  await Task.Delay(100);
  throw new Exception("boom"); // caller can await + catch
}

// Event handlers stay async void with a try/catch at the boundary:
private async void OnClick(object s, EventArgs e) {
  try { await DoWorkAsync(); }
  catch (Exception ex) { _log.LogError(ex, "OnClick failed"); }
}
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `go-loop-var-capture` — go

# Loop variable captured by goroutine — pre-1.22 races on the last value

Before Go 1.22, the loop variable in `for ... := range` was reused across iterations. Goroutines that closed over it all read the *same* (final) value. Go 1.22+ fixes this at the language level, but the pattern still appears in libraries that target older versions.

## Fix

Pin the variable inside the loop: `i := i` before `go func() { use(i) }()`, or pass as argument: `go func(i int) { ... }(i)`. (Fixed automatically in Go 1.22+.)

## Incorrect

```go
// Pre-1.22: all goroutines print the last item
for _, v := range items {
  go func() {
    fmt.Println(v)
  }()
}
```

## Correct

```go
// Pin the variable explicitly
for _, v := range items {
  v := v
  go func() { fmt.Println(v) }()
}

// Or pass as a parameter
for _, v := range items {
  go func(v string) { fmt.Println(v) }(v)
}
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `java-arraylist-remove-in-for-i` — java

# list.remove(i) inside for-i — index shifts; ConcurrentModification risk

Removing from an `ArrayList` inside a `for (int i = 0; i < list.size(); i++)` shifts indices and skips elements — and on a `Collections.synchronizedList` or in concurrent code, it throws `ConcurrentModificationException`.

## Fix

Iterate backwards, use Iterator.remove(), or collect indexes and remove in one removeIf().

## Incorrect

```java
for (int i = 0; i < list.size(); i++) {
  if (shouldRemove(list.get(i))) {
    list.remove(i); // shifts everything; next element is skipped
  }
}
```

## Correct

```java
// Idiomatic and correct
list.removeIf(this::shouldRemove);

// Or, with an explicit iterator:
var it = list.iterator();
while (it.hasNext()) {
  if (shouldRemove(it.next())) it.remove();
}
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `js-async-in-foreach` — javascript

# async passed to .forEach — returned promises are dropped

`Array.prototype.forEach` ignores return values. Passing an `async` function returns promises that are dropped — errors are swallowed and the caller continues before the work finishes.

## Fix

Use `for (const x of arr) await fn(x)` or `await Promise.all(arr.map(fn))`.

## Incorrect

```ts
// Promises dropped; errors silently swallowed
items.forEach(async (item) => {
  await save(item);
});
console.log('done'); // logs before any save completes
```

## Correct

```ts
// Sequential, with errors propagated
for (const item of items) {
  await save(item);
}

// Parallel
await Promise.all(items.map((item) => save(item)));
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-await-in-for-loop` — javascript

# await inside for-loop — likely N+1 / serialized I/O

Awaiting inside a `for` over independent items serializes wall-clock work into O(n × latency). For network or DB calls this is the N+1 problem.

## Fix

Collect promises into an array and use Promise.all(...), or batch with a bulk query (WHERE id IN (...)).

## Incorrect

```ts
// Wall-clock: O(n × latency)
for (const id of ids) {
  const user = await db.users.findById(id);
  results.push(user);
}
```

## Correct

```ts
// Wall-clock: O(latency); one bulk query
const users = await db.users.findMany({ where: { id: { in: ids } } });

// Or, if calls are truly independent:
const results = await Promise.all(ids.map(id => db.users.findById(id)));
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `php-query-in-loop` — php

# DB query inside loop — N+1

A SQL query inside a loop is the textbook N+1 problem. 1000 orders, 1000 round-trips to the DB. Batch with `WHERE id IN (...)` or eager-load in your ORM.

## Fix

Collect the ids, run ONE `WHERE id IN (...)` query, index by id, then loop. In Eloquent use eager loading: `Model::with('relation')`.

## Incorrect

```php
<?php
foreach ($orderIds as $id) {
  $row = $db->query("SELECT * FROM orders WHERE id = $id"); // 1 query per id
  process($row);
}
```

## Correct

```php
<?php
// One bulk query
$placeholders = implode(',', array_fill(0, count($orderIds), '?'));
$stmt = $db->prepare("SELECT * FROM orders WHERE id IN ($placeholders)");
$stmt->execute($orderIds);
foreach ($stmt->fetchAll() as $row) {
  process($row);
}

// Eloquent / Doctrine: use eager loading
$orders = Order::with('items')->whereIn('id', $orderIds)->get();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `py-mutable-default-arg` — python

# Mutable default argument — shared across calls

Python evaluates default arguments once, at function definition. A mutable default (list, dict, set) is **shared across every call** — calls accumulate state from previous calls.

## Fix

Default to None; create inside: `def f(x=None): x = x or []`.

## Incorrect

```python
def collect(item, bucket=[]):  # shared across all calls!
    bucket.append(item)
    return bucket
```

## Correct

```python
def collect(item, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `rb-n-plus-one-activerecord` — ruby

# ActiveRecord iteration touching an association — N+1 without includes

Iterating an ActiveRecord scope and touching an association fires one extra query per row. `includes` (preload or eager_load) fetches everything in a constant number of queries.

## Fix

Use `Model.includes(:assoc)` or `:preload` / `:eager_load` before iterating.

## Incorrect

```ruby
# N+1 queries
Post.all.each do |p|
  puts p.author.name # 1 extra query per post
end
```

## Correct

```ruby
# 2 queries total (or 1 with eager_load)
Post.includes(:author).each do |p|
  puts p.author.name
end
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `sql-update-no-where` — sql

# UPDATE / DELETE without WHERE — touches every row

An `UPDATE` or `DELETE` without a `WHERE` clause rewrites every row in the table. In production this is an incident, not a bug.

## Fix

Add a WHERE clause, or confirm in a comment that touching all rows is intentional.

## Incorrect

```sql
UPDATE users SET active = false;
DELETE FROM sessions;
```

## Correct

```sql
UPDATE users SET active = false WHERE last_seen_at < NOW() - INTERVAL '90 days';
DELETE FROM sessions WHERE expires_at < NOW();
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.


## HIGH — hot-path or correctness risk at realistic n

### `cpp-raw-new` — cpp

# Raw `new` outside of smart-pointer ctor — manual delete, exception-unsafe

Raw `new` requires a matching `delete` on every exit path. If an exception fires between `new` and `delete`, the memory leaks. Smart pointers (`unique_ptr`, `shared_ptr`) destruct automatically.

## Fix

Use `std::make_unique<T>(...)` or `std::make_shared<T>(...)`. Reserve raw `new` for placement-new or interop with C APIs.

## Incorrect

```cpp
Widget* w = new Widget(42);
configure(w);   // if this throws, w leaks
delete w;
```

## Correct

```cpp
auto w = std::make_unique<Widget>(42);
configure(w.get()); // destructs on every exit path, including throw
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `cpp-string-concat-in-loop` — cpp

# std::string += inside loop — O(n^2) without reserve()

`std::string::operator+=` past capacity reallocates. Without a `reserve`, repeated concatenation is O(n²). `std::ostringstream` or one `reserve` fixes it.

## Fix

Call `s.reserve(total)` once if size known, or accumulate into a `std::ostringstream` and call `.str()` at the end.

## Incorrect

```cpp
std::string s;
for (const auto& part : parts) {
  s += part;
}
```

## Correct

```cpp
std::ostringstream os;
for (const auto& part : parts) {
  os << part;
}
auto s = os.str();

// Or, if size known:
std::string s;
s.reserve(total_size);
for (const auto& part : parts) s += part;
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `cs-disposable-no-using` — csharp

# IDisposable allocated without using — leak on exception

`IDisposable` resources allocated without `using` leak if an exception fires before `Dispose()`. `using var` ensures cleanup even on throw.

## Fix

Wrap in `using var x = new ...;` or `using (var x = ...) { }`.

## Incorrect

```csharp
var stream = new FileStream(path, FileMode.Open);
var data = ReadAll(stream); // if this throws, stream is never disposed
stream.Dispose();
```

## Correct

```csharp
using var stream = new FileStream(path, FileMode.Open);
var data = ReadAll(stream); // disposed on every exit path
```

### `cs-list-contains-in-loop` — csharp

# List.Contains inside LINQ/loop — O(n*m); use HashSet<T>

`List<T>.Contains` is O(n). Inside LINQ over m items it is O(n·m). `HashSet<T>` is O(1).

## Fix

Convert to HashSet once: `var s = new HashSet<T>(list); s.Contains(x);`

## Incorrect

```csharp
// O(n·m)
var active = users.Where(u => !banned.Contains(u.Id)).ToList();
```

## Correct

```csharp
// O(n+m)
var bannedSet = new HashSet<int>(banned);
var active = users.Where(u => !bannedSet.Contains(u.Id)).ToList();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `cs-string-concat-in-loop` — csharp

# string += inside loop — O(n^2) on immutable string

C# `string` is immutable. `s += x` allocates a new string each iteration — O(n²). `StringBuilder` reuses one buffer; or use `string.Concat` / `string.Join` for known parts.

## Fix

Use StringBuilder: `var sb = new StringBuilder(); foreach (...) sb.Append(x); sb.ToString();`

## Incorrect

```csharp
// O(n²)
string s = "";
foreach (var line in lines) {
  s += line + "\n";
}
```

## Correct

```csharp
// O(n)
var sb = new StringBuilder(lines.Count * 80);
foreach (var line in lines) {
  sb.Append(line).Append('\n');
}
var s = sb.ToString();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `go-defer-in-loop` — go

# defer inside loop — defers accumulate until function returns

`defer` fires when the enclosing *function* returns, not when the loop body ends. Deferring inside a loop over N files holds N open handles until the function exits — easy way to exhaust file descriptors.

## Fix

Wrap the body in a function so each iteration's defer fires at iteration end, or close resources explicitly.

## Incorrect

```go
for _, f := range files {
  fp, _ := os.Open(f)
  defer fp.Close() // accumulates; nothing closes until the outer function returns
  process(fp)
}
```

## Correct

```go
for _, f := range files {
  func() {
    fp, _ := os.Open(f)
    defer fp.Close() // closes at end of this iteration
    process(fp)
  }()
}
```

### `go-err-not-checked` — go

# Error return value discarded — silent failures

Discarding the error return with `_` is silent failure. The function looks like it succeeded; downstream code sees zero values and behaves unpredictably.

## Fix

Handle the error or comment why it is safe to ignore (`_ = err // <reason>`).

## Incorrect

```go
data, _ := os.ReadFile(path)
return parse(data) // parse on empty buffer if file missing
```

## Correct

```go
data, err := os.ReadFile(path)
if err != nil {
  return nil, fmt.Errorf("read %s: %w", path, err)
}
return parse(data), nil
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `go-string-concat-in-loop` — go

# string += inside loop — O(n^2); use strings.Builder

Go strings are immutable. `s += x` allocates each iteration — O(n²). `strings.Builder` reuses one backing array.

## Fix

Use strings.Builder: `var sb strings.Builder; for ... { sb.WriteString(x) }; sb.String()`.

## Incorrect

```go
// O(n²)
var s string
for _, line := range lines {
  s += line + "\n"
}
```

## Correct

```go
// O(n)
var sb strings.Builder
sb.Grow(len(lines) * 80)
for _, line := range lines {
  sb.WriteString(line)
  sb.WriteByte('\n')
}
s := sb.String()
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `java-bare-catch-exception` — java

# catch (Exception) with empty body or log-only — swallows root cause

`catch (Exception e)` with an empty body or just `printStackTrace()` swallows the root cause. The bug lives on, the stack trace evaporates, the production incident has no breadcrumbs.

## Fix

Catch the narrowest exception, rethrow as a domain exception, or handle with a documented fallback. Never swallow silently.

## Incorrect

```java
try {
  riskyCall();
} catch (Exception e) {
  e.printStackTrace(); // swallowed; caller thinks everything is fine
}
```

## Correct

```java
try {
  riskyCall();
} catch (IOException e) {
  // narrow exception, rethrow as domain error with cause preserved
  throw new ReadFailedException("riskyCall failed for " + ctx, e);
}
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `java-list-contains-in-loop` — java

# List.contains inside iterator — O(n*m); use HashSet

`List.contains` is O(n). Used inside a stream/iterator over m items it is O(n·m). A `HashSet` lookup is O(1).

## Fix

Build a HashSet outside: `Set<T> s = new HashSet<>(list); s.contains(x);`

## Incorrect

```java
// O(n·m)
var active = users.stream()
    .filter(u -> !banned.contains(u.id))
    .toList();
```

## Correct

```java
// O(n+m)
var bannedSet = new HashSet<>(banned);
var active = users.stream()
    .filter(u -> !bannedSet.contains(u.id))
    .toList();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `java-string-concat-in-loop` — java

# String += inside loop — O(n^2) on immutable String

Java `String` is immutable. `s += x` allocates a fresh `String` (and an underlying `char[]`) each iteration — O(n²) total work. `StringBuilder` reuses one buffer.

## Fix

Use StringBuilder: `var sb = new StringBuilder(); for (...) sb.append(x); sb.toString();`

## Incorrect

```java
// O(n²)
String s = "";
for (var line : lines) {
  s += line + "\n";
}
```

## Correct

```java
// O(n)
var sb = new StringBuilder(lines.size() * 80);
for (var line : lines) {
  sb.append(line).append('\n');
}
String s = sb.toString();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-anonymous-handler-jsx` — javascript

# Anonymous arrow handler in JSX — breaks memoized-child equality

An anonymous arrow handler is a new function every render. For an ordinary child, this is fine. For a `React.memo` child, it breaks equality and forces a re-render every time.

## Fix

Wrap with useCallback if the child is memoized. Otherwise ignore.

## Incorrect

```tsx
// Child is React.memo — this defeats it
<MemoButton onClick={() => save(id)} />
```

## Correct

```tsx
const onClick = useCallback(() => save(id), [id]);
<MemoButton onClick={onClick} />
```

### `js-deep-clone-via-json` — javascript

# JSON.parse(JSON.stringify(x)) — slow clone; loses Dates/Maps/undefined

`JSON.parse(JSON.stringify(x))` is slow, allocates twice, and silently loses `Date`, `Map`, `Set`, `undefined`, `BigInt`, `RegExp`, and any non-enumerable property. It is also unsafe on cyclic structures.

## Fix

Use structuredClone(x), or copy only the fields you actually need.

## Incorrect

```ts
const copy = JSON.parse(JSON.stringify(state));
// state.createdAt was a Date — now a string
```

## Correct

```ts
const copy = structuredClone(state); // preserves Date, Map, Set, cycles

// Or, when you only need a few fields:
const copy = { id: state.id, name: state.name };
```

### `js-helper-call-in-iterator` — javascript

# get*/find*/fetch* helper called inside iterator — likely N round-trips

A `get*`/`find*`/`fetch*` helper inside an iterator usually means N independent lookups. If the helper hits a DB or network, this is N+1. If it scans an array, it is O(n × m).

## Fix

Hoist the helper out of the loop and pass a precomputed lookup (Map/Set) into the iterator, or batch with a single bulk query.

## Incorrect

```ts
// N round trips
const enriched = orders.map((o) => ({
  ...o,
  user: getUserById(o.userId),
}));
```

## Correct

```ts
// 1 round trip
const userIds = [...new Set(orders.map((o) => o.userId))];
const users = await db.users.findMany({ where: { id: { in: userIds } } });
const userById = new Map(users.map((u) => [u.id, u]));
const enriched = orders.map((o) => ({ ...o, user: userById.get(o.userId) }));
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-inline-object-jsx-prop` — javascript

# Inline object literal as JSX prop — new reference every render

An inline object literal in JSX creates a new reference every render. If the child is `React.memo`, this defeats the memoization. If it is a dependency of a hook in the child, it re-fires that hook every render.

## Fix

Hoist outside render, or wrap in useMemo if the child is React.memo.

## Incorrect

```tsx
<Chart options={{ animated: true, color: 'red' }} />
```

## Correct

```tsx
// Hoist if static
const CHART_OPTIONS = { animated: true, color: 'red' };
<Chart options={CHART_OPTIONS} />

// Memoize if derived
const options = useMemo(() => ({ animated, color }), [animated, color]);
<Chart options={options} />
```

### `js-spread-in-reduce` — javascript

# Object spread inside reduce — O(n^2)

Object-spread in a reducer copies the accumulator on every iteration — O(n²) work and O(n²) allocation. The result is the same as mutating once.

## Fix

Mutate the accumulator (`acc[k] = v; return acc`) or use Object.fromEntries(arr.map(...)).

## Incorrect

```ts
// O(n²)
const byId = items.reduce((acc, x) => ({ ...acc, [x.id]: x }), {});
```

## Correct

```ts
// O(n)
const byId = Object.fromEntries(items.map((x) => [x.id, x]));

// Or mutate the accumulator
const byId = items.reduce((acc, x) => { acc[x.id] = x; return acc; }, {});
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-unique-via-indexof` — javascript

# Unique-by-indexOf — O(n^2) dedupe; use `Array.from(new Set(arr))`

`.filter((x, i, a) => a.indexOf(x) === i)` is the textbook O(n²) dedupe. A `Set` does it in O(n).

## Fix

Use `Array.from(new Set(arr))`, or build a Set inline. O(n) instead of O(n^2).

## Incorrect

```ts
// O(n²)
const unique = arr.filter((x, i, a) => a.indexOf(x) === i);
```

## Correct

```ts
// O(n)
const unique = Array.from(new Set(arr));
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-useeffect-missing-deps` — javascript

# useEffect without a deps array — runs after every render

A `useEffect` with no dependency array runs after every render. If the effect updates state, you can get a render loop or wasted work each frame.

## Fix

Add a deps array — `[]` for mount-only, `[a, b]` to track changes.

## Incorrect

```tsx
useEffect(() => {
  setUser(fetchUser(id));
}); // no deps — runs every render
```

## Correct

```tsx
useEffect(() => {
  setUser(fetchUser(id));
}, [id]); // runs when id changes
```

### `php-count-in-for-condition` — php

# count() in for-condition — recomputed every iteration

PHP recomputes the loop condition every iteration. `count($a)` on a 100k-element array, called 100k times, is 10B element traversals. Hoist it.

## Fix

Hoist: `for ($i = 0, $n = count($a); $i < $n; $i++)`. Or use `foreach`.

## Incorrect

```php
<?php
for ($i = 0; $i < count($a); $i++) {
  echo $a[$i];
}
```

## Correct

```php
<?php
// Hoist the length
for ($i = 0, $n = count($a); $i < $n; $i++) {
  echo $a[$i];
}

// Or, idiomatic
foreach ($a as $x) {
  echo $x;
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `php-in-array-in-loop` — php

# in_array inside loop — O(n*m); use array_flip + isset

`in_array` is a linear scan. Used inside a loop over m items it is O(n·m). `array_flip + isset` is O(1) per check.

## Fix

`$set = array_flip($haystack); ... isset($set[$x])` is O(1) per check.

## Incorrect

```php
<?php
foreach ($users as $u) {
  if (in_array($u->id, $banned)) continue;
  ship($u);
}
```

## Correct

```php
<?php
$bannedSet = array_flip($banned); // O(n) once
foreach ($users as $u) {
  if (isset($bannedSet[$u->id])) continue; // O(1)
  ship($u);
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `py-django-loop-without-eager` — python

# Django ORM iteration — verify select_related/prefetch_related to avoid N+1

Iterating a Django QuerySet that touches a related model triggers one extra query per row — classic N+1. `select_related` (foreign key, one query with JOIN) or `prefetch_related` (reverse / many-to-many, two queries) fixes it.

## Fix

Add .select_related('fk') for FK/OneToOne, .prefetch_related('rel') for reverse FK / M2M.

## Incorrect

```python
# N+1 queries
for order in Order.objects.all():
    print(order.user.email)  # extra query per order
```

## Correct

```python
# 1 query with JOIN
for order in Order.objects.select_related("user"):
    print(order.user.email)

# For reverse FK / M2M:
for user in User.objects.prefetch_related("orders"):
    for order in user.orders.all():
        ...
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `py-string-concat-in-loop` — python

# String += inside loop — O(n^2)

Python strings are immutable. `s += x` in a loop allocates and copies the whole `s` each iteration — O(n²) total work. A list join is O(n).

## Fix

Append to a list, then ''.join(list). Or use io.StringIO.

## Incorrect

```python
# O(n²)
s = ""
for line in lines:
    s += line + "\n"
```

## Correct

```python
# O(n)
s = "\n".join(lines) + "\n"

# Or, for incremental building:
parts = []
for line in lines:
    parts.append(line)
s = "\n".join(parts)
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `rb-bare-rescue` — ruby

# Bare rescue — catches StandardError, hides bugs

A bare `rescue` (without a class) catches `StandardError` — including `NoMethodError`, `ArgumentError`, and other bugs you almost always want to surface. Catch the specific class.

## Fix

Catch a specific class: `rescue Net::ReadTimeout` etc. Bare rescue swallows too much.

## Incorrect

```ruby
begin
  fetch_remote
rescue
  retry # also catches typos and bugs in fetch_remote
end
```

## Correct

```ruby
begin
  fetch_remote
rescue Net::ReadTimeout, Net::OpenTimeout => e
  retry
end
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `rb-include-in-iterator` — ruby

# Array#include? inside iterator — O(n*m); use Set

`Array#include?` is O(n). Used inside an iterator over m items it is O(n·m). `Set#include?` is O(1).

## Fix

`require 'set'; allowed = Set.new(list); ... allowed.include?(x)`.

## Incorrect

```ruby
# O(n·m)
users.select { |u| banned.include?(u.id) }
```

## Correct

```ruby
# O(n+m)
require 'set'
banned_set = Set.new(banned)
users.select { |u| banned_set.include?(u.id) }
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `rs-unwrap-in-prod` — rust

# .unwrap() / .expect() panics on None/Err — surface the error

`.unwrap()` and `.expect()` panic on `None`/`Err`. In production code they crash the process and lose the structured error. Rust gives you `?`, `match`, and `ok_or` to surface the error to the caller.

## Fix

Use `?`, `match`, `unwrap_or`, `unwrap_or_else`, or `ok_or(...)?`. Reserve unwrap for tests and provably infallible paths.

## Incorrect

```rust
let value = map.get(&key).unwrap(); // panics if key missing
```

## Correct

```rust
let value = map.get(&key).ok_or(Error::MissingKey)?;

// Or, when None has a meaningful default:
let value = map.get(&key).copied().unwrap_or_default();
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `sh-for-ls` — shell

# for f in $(ls ...) — breaks on filenames with spaces / newlines

`for f in $(ls ...)` breaks on filenames with spaces, tabs, newlines, or globs. The output of `ls` is meant for humans, not programs. Use a glob or `find -print0 | xargs -0`.

## Fix

Use glob `for f in *.txt` or `find ... -print0 | xargs -0`. Never parse `ls`.

## Incorrect

```shell
for f in $(ls *.txt); do
  process "$f"  # breaks on "my file.txt"
done
```

## Correct

```shell
# Glob directly
for f in *.txt; do
  process "$f"
done

# Or, when find is necessary
find . -name '*.txt' -print0 | xargs -0 -n1 process
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `sh-set-e-no-pipefail` — shell

# set -e without set -o pipefail — failures inside pipes are masked

`set -e` exits on a failed command, but a failure in the middle of a pipe is masked — only the *last* command's exit status counts. `set -o pipefail` fixes it. `set -u` catches unset variables.

## Fix

Use `set -euo pipefail` so the script also fails when an earlier stage in a pipe fails.

## Incorrect

```shell
#!/bin/bash
set -e
some_failing_step | grep needle # if some_failing_step fails, script keeps going
```

## Correct

```shell
#!/bin/bash
set -euo pipefail
some_failing_step | grep needle # any failure in the pipe aborts the script
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `sh-unquoted-var` — shell

# Unquoted $var — word splitting and glob expansion

An unquoted `$var` is subject to word splitting (on `$IFS`) and glob expansion. A path with a space, a tab, or a `*` will silently do the wrong thing.

## Fix

Quote: `"$var"`. Use `"${arr[@]}"` for arrays. Required even for paths you trust.

## Incorrect

```shell
if [ -d $dir ]; then echo yes; fi
# If $dir = "/tmp/with space", expands to: [ -d /tmp/with space ] — syntax error
```

## Correct

```shell
if [ -d "$dir" ]; then echo yes; fi
# Always quote. For arrays: "${arr[@]}".
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `sql-leading-wildcard-like` — sql

# LIKE with leading wildcard — cannot use a B-tree index

A B-tree index sorts by prefix. `LIKE '%foo'` cannot use it — the query scans the table. Use a trigram index (Postgres `pg_trgm`), reverse the column for suffix search, or a full-text search index.

## Fix

Use a trigram index (pg_trgm), full-text search, or a reversed-column index.

## Incorrect

```sql
SELECT * FROM products WHERE name LIKE '%phone';
```

## Correct

```sql
-- Postgres: GIN index on trigrams
CREATE INDEX products_name_trgm ON products USING gin (name gin_trgm_ops);
SELECT * FROM products WHERE name ILIKE '%phone%';

-- Or full-text:
SELECT * FROM products WHERE to_tsvector(name) @@ to_tsquery('phone');
```

### `sql-not-in-subquery` — sql

# NOT IN (subquery) — null-unsafe; usually slower than NOT EXISTS

`NOT IN (subquery)` is null-unsafe: if any row in the subquery is NULL, the whole predicate is NULL (not TRUE), and the outer row is dropped. `NOT EXISTS` is null-safe and usually has a better plan.

## Fix

Rewrite as `WHERE NOT EXISTS (SELECT 1 FROM ... WHERE ...)`.

## Incorrect

```sql
SELECT * FROM orders
WHERE user_id NOT IN (SELECT id FROM banned_users);
-- One NULL in banned_users.id → returns zero rows
```

## Correct

```sql
SELECT o.* FROM orders o
WHERE NOT EXISTS (
  SELECT 1 FROM banned_users b WHERE b.id = o.user_id
);
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `sql-select-star` — sql

# SELECT * — fetches unused columns; blocks index-only scans

`SELECT *` fetches every column, defeating index-only scans, inflating wire traffic, and breaking downstream code when a column is added/renamed. Project only what you need.

## Fix

Name the columns. Smaller payload and more covering-index opportunities.

## Incorrect

```sql
SELECT * FROM users WHERE id = $1;
```

## Correct

```sql
SELECT id, email, created_at FROM users WHERE id = $1;
```


## MEDIUM — suboptimal; flag when n is large or hot path

### `cpp-map-double-lookup` — cpp

# map.count(k) then map[k] — two lookups; use find()

`m.count(k)` then `m[k]` does two hash lookups (and for `std::map`, two binary searches). `find` returns an iterator that gives both presence and value in one lookup.

## Fix

Use `auto it = m.find(k); if (it != m.end()) use(it->second);` — one lookup.

## Incorrect

```cpp
if (m.count(k)) {
  use(m[k]); // second lookup
}
```

## Correct

```cpp
auto it = m.find(k);
if (it != m.end()) {
  use(it->second);
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `cpp-range-loop-copy` — cpp

# Range-for `auto x` copies each element — use `const auto&` for non-trivial types

`for (auto x : container)` copies each element into `x`. For non-trivial types (`std::string`, `std::vector<…>`, custom types) this is expensive. `const auto&` borrows, `auto&` mutates in place.

## Fix

Prefer `for (const auto& x : container)` unless you intentionally need a copy.

## Incorrect

```cpp
for (auto s : large_strings) {
  process(s); // s is a fresh copy each iteration
}
```

## Correct

```cpp
for (const auto& s : large_strings) {
  process(s); // reference, no copy
}
```

### `cpp-vector-push-no-reserve` — cpp

# vector push_back in loop without reserve() — log-amortized reallocation

`std::vector::push_back` past the current capacity doubles the backing array and copies/moves every element. Calling `reserve(n)` first does one allocation.

## Fix

Call `v.reserve(n)` before the loop when n is known.

## Incorrect

```cpp
std::vector<int> v;
for (int i = 0; i < n; ++i) {
  v.push_back(compute(i)); // reallocates log(n) times
}
```

## Correct

```cpp
std::vector<int> v;
v.reserve(n);
for (int i = 0; i < n; ++i) {
  v.push_back(compute(i));
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `go-slice-append-no-cap` — go

# append in loop without preallocated capacity — repeated reallocation

A slice grown by repeated `append` reallocates and copies its backing array each time it crosses a capacity boundary. Preallocating with `make([]T, 0, n)` does one allocation total.

## Fix

Preallocate: `out := make([]T, 0, len(in))` then `append`.

## Incorrect

```go
var out []int
for _, x := range in {
  out = append(out, x*2) // grows; reallocates log(n) times
}
```

## Correct

```go
out := make([]int, 0, len(in))
for _, x := range in {
  out = append(out, x*2)
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-array-key-index` — javascript

# key={index} on a list — breaks identity for reorderable items

`key={index}` is fine for a static list. For a list that reorders, inserts, or deletes in the middle, it forces React to mismatch component state with the wrong row — losing input focus, animation, and local state.

## Fix

Use a stable id when the list can reorder, insert, or delete in the middle.

## Incorrect

```tsx
{items.map((item, i) => <Row key={i} item={item} />)}
```

## Correct

```tsx
{items.map((item) => <Row key={item.id} item={item} />)}
```

### `js-includes-in-iterator` — javascript

# Array.includes inside .map/.filter/.forEach — O(n*m); use a Set

`.includes` on an array is O(n). Calling it inside `.map`/`.filter`/`.forEach` over m items is O(n × m). A `Set` lookup is O(1).

## Fix

Build a Set once outside the iterator, then `set.has(x)` inside.

## Incorrect

```ts
// O(n × m)
const allowed = ['admin', 'editor', 'owner'];
const result = users.filter((u) => allowed.includes(u.role));
```

## Correct

```ts
// O(n + m)
const allowed = new Set(['admin', 'editor', 'owner']);
const result = users.filter((u) => allowed.has(u.role));
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `js-nested-for-loops` — javascript

# Nested for-loops — O(n*m); consider hashing one side

Two `for` loops that check membership between arrays are O(n × m). Hashing one side into a `Set` makes it O(n + m).

## Fix

If looking up between the two arrays, put one into a Set/Map first → O(n+m).

## Incorrect

```ts
// O(n × m)
const matches = [];
for (const a of left) {
  for (const b of right) {
    if (a.id === b.id) matches.push([a, b]);
  }
}
```

## Correct

```ts
// O(n + m)
const rightById = new Map(right.map((b) => [b.id, b]));
const matches = [];
for (const a of left) {
  const b = rightById.get(a.id);
  if (b) matches.push([a, b]);
}
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `php-loose-equality` — php

# == / != — loose equality has surprising coercions

PHP `==` does type coercion in surprising ways (`"0" == false` is `true`, `"abc" == 0` was `true` before PHP 8). `===` compares value AND type — no surprises.

## Fix

Use `===` / `!==` unless type-juggling is explicitly intended (with a comment).

## Incorrect

```php
<?php
if ($status == 0) { /* matches "", "0", false, null, 0, "abc" pre-PHP 8 */ }
```

## Correct

```php
<?php
if ($status === 0) { /* matches only int 0 */ }
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `py-bare-except` — python

# Bare except — hides timeouts, OOM, KeyboardInterrupt

Bare `except:` catches `SystemExit`, `KeyboardInterrupt`, `MemoryError`, and `GeneratorExit` — things you almost never want to swallow. It hides timeouts, OOM, and Ctrl-C.

## Fix

Catch specific exceptions: `except (TimeoutError, ConnectionError):`.

## Incorrect

```python
try:
    do_work()
except:
    log("failed")  # also swallows Ctrl-C, OOM, timeouts
```

## Correct

```python
try:
    do_work()
except Exception as e:  # excludes SystemExit, KeyboardInterrupt
    log(f"failed: {e}")
```

## Escalate to

If this pattern is widespread in the codebase, load **invariant-guard** for the corrective workflow.

### `py-in-list-literal` — python

# Membership against a list literal — O(n) per check; use a set

`x in [a, b, c, ...]` is an O(n) linear scan. Inside a loop over m items, this is O(n × m). A `set` (or a literal `{a, b, c}` for membership) is O(1).

## Fix

Hoist to a module-level frozenset({...}).

## Incorrect

```python
# O(n × m)
roles = ["admin", "editor", "owner"]
result = [u for u in users if u.role in roles]
```

## Correct

```python
# O(n + m)
roles = {"admin", "editor", "owner"}
result = [u for u in users if u.role in roles]
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `py-open-without-with` — python

# open() without `with` — risk of leaked file descriptors

`open()` returns a file object. Without `with`, an exception between open and close leaks the file descriptor. Long-running processes (servers, workers) eventually exhaust the OS limit.

## Fix

Use `with open(path) as f:` to ensure the handle is released.

## Incorrect

```python
f = open(path)
data = f.read()
f.close()  # skipped if read() raises
```

## Correct

```python
with open(path) as f:
    data = f.read()
# f is closed even if read() raises
```

### `py-range-len` — python

# range(len(x)) — un-Pythonic; use enumerate(x)

`for i in range(len(xs))` then indexing `xs[i]` is un-Pythonic, slower, and forces you to think about indices when you usually want the items. `enumerate` is idiomatic and faster.

## Fix

Use `for i, item in enumerate(x):` when you need the index too.

## Incorrect

```python
for i in range(len(xs)):
    process(xs[i])
```

## Correct

```python
for x in xs:
    process(x)

# When you actually need the index
for i, x in enumerate(xs):
    process(i, x)
```

### `py-set-add-in-loop-large-n` — python

# set.add() over a stream — unbounded memory; use HyperLogLog if you only need the count

Accumulating every item into a `set` to count distinct values over an unbounded stream grows memory with the cardinality — at billions of distinct items the set alone is hundreds of gigabytes and OOMs. When the caller only needs the *count* (and tolerates small error), HyperLogLog estimates cardinality in kilobytes.

## Fix

If you only need the count of distinct items, use a probabilistic cardinality estimator (HyperLogLog, e.g. datasketch). If you need membership of a bounded set, this is fine — ignore.

## Incorrect

```python
# Memory grows with cardinality — OOMs at billions of distinct IPs
seen = set()
for line in log_stream:
    seen.add(line.split()[0])
return len(seen)
```

## Correct

```python
# ~12 KB regardless of cardinality; ~0.8% standard error at p=14
from datasketch import HyperLogLog

hll = HyperLogLog(p=14)
for line in log_stream:
    hll.update(line.split()[0].encode('utf-8'))
return int(hll.count())
```

## Escalate to

If this pattern is widespread in the codebase, load **mathguard** for the corrective workflow.

### `rb-string-concat-in-loop` — ruby

# String += in loop — O(n^2) since += creates a new string each iteration

`s += x` creates a new string each iteration — O(n²). `<<` mutates in place (O(n) amortized). `Array#join` is O(n) and idiomatic.

## Fix

Use `<<` (mutates) or `parts.join` if building from an array.

## Incorrect

```ruby
s = ""
parts.each { |p| s += p } # O(n²)
```

## Correct

```ruby
# Mutating concat
s = String.new
parts.each { |p| s << p }

# Idiomatic
s = parts.join
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `rs-clone-in-loop` — rust

# .clone() inside iterator — avoid if a borrow works

A `.clone()` inside an iterator allocates a fresh copy per element. If a borrow (`&x`) or `Rc::clone` (cheap atomic increment for shared ownership) would do, the deep clone is wasted work.

## Fix

Borrow with &, use Rc/Arc for shared ownership, or move once outside the loop.

## Incorrect

```rust
// Deep clones every element
let names: Vec<String> = users.iter().map(|u| u.name.clone()).collect();
```

## Correct

```rust
// Borrow when possible
let names: Vec<&str> = users.iter().map(|u| u.name.as_str()).collect();

// Cheap reference-counted clone when shared ownership is needed
let shared: Vec<Rc<String>> = users.iter().map(|u| Rc::clone(&u.name)).collect();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `rs-string-push-no-capacity` — rust

# String::new() + push_str in loop — repeated reallocation

`String::new()` starts at capacity 0. Each `push_str` past capacity reallocates. `with_capacity` or `join` avoids it.

## Fix

Preallocate: `String::with_capacity(n)`, or `parts.join(sep)` for known parts.

## Incorrect

```rust
let mut s = String::new();
for part in parts.iter() {
  s.push_str(part); // reallocates as it grows
}
```

## Correct

```rust
let total: usize = parts.iter().map(|p| p.len()).sum();
let mut s = String::with_capacity(total);
for part in parts.iter() {
  s.push_str(part);
}

// Or, simplest:
let s = parts.join("");
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `rs-vec-push-no-capacity` — rust

# Vec::new() + push in loop — repeated reallocation

`Vec::new()` starts with capacity 0; each `push` past the current capacity reallocates and copies. Preallocating with `Vec::with_capacity(n)` does one allocation.

## Fix

Preallocate: `Vec::with_capacity(n)`, or use `.collect::<Vec<_>>()` over an iterator that has a size hint.

## Incorrect

```rust
let mut out = Vec::new();
for x in input.iter() {
  out.push(transform(x)); // grows; reallocates log(n) times
}
```

## Correct

```rust
let mut out = Vec::with_capacity(input.len());
for x in input.iter() {
  out.push(transform(x));
}

// Or, when transform is pure:
let out: Vec<_> = input.iter().map(transform).collect();
```

## Escalate to

If this pattern is widespread in the codebase, load **complexity-cuts** for the corrective workflow.

### `sh-useless-cat-pipe` — shell

# cat file | cmd — useless use of cat (UUOC)

`cat file | cmd` reads the file and pipes through `cat` just to feed `cmd`. Every command that takes a file argument can read it directly — one fewer process, clearer intent.

## Fix

Run the command on the file directly: `grep ... file` instead of `cat file | grep ...`.

## Incorrect

```shell
cat access.log | grep "500"
```

## Correct

```shell
grep "500" access.log

# Or stdin redirection if the command takes only stdin:
cmd < access.log
```

### `sql-or-in-where` — sql

# OR in WHERE — can prevent index use

A query planner can use an index on one side of an `OR` but often not both, falling back to a sequential scan. `UNION ALL` or `IN (...)` (when both sides are equality on the same column) usually wins.

## Fix

Equality on same column → `WHERE col IN (...)`. Otherwise consider UNION ALL.

## Incorrect

```sql
SELECT * FROM events
WHERE user_id = $1 OR account_id = $1;
```

## Correct

```sql
SELECT * FROM events WHERE user_id = $1
UNION ALL
SELECT * FROM events WHERE account_id = $1;

-- Or, when both sides are the same column:
SELECT * FROM events WHERE user_id IN ($1, $2, $3);
```

### `sql-select-no-limit` — sql

# SELECT without LIMIT — unbounded result set

A query with no `LIMIT` returns however many rows match. On a small table this is fine; on a growing one it eventually OOMs the client or the page. Add a bound, or paginate.

## Fix

Add LIMIT, or paginate by id range. Unbounded reads OOM under growth.

## Incorrect

```sql
SELECT id, email FROM users ORDER BY created_at DESC;
```

## Correct

```sql
SELECT id, email FROM users
ORDER BY created_at DESC
LIMIT 100;

-- Keyset pagination for next page:
SELECT id, email FROM users
WHERE created_at < $1
ORDER BY created_at DESC
LIMIT 100;
```
