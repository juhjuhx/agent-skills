# Vue/Pinia & Express Auth Patterns

> Learned from ArtFactory multi-agent session (2026-06-26).
> Common pitfalls when agents modify Vue/Express codebases.

## Express: optionalAuth vs authMiddleware

When making routes public (e.g., portfolio pages), the pattern is:

```javascript
// index.js — mount with optionalAuth (not authMiddleware)
app.use('/api/talent', optionalAuth, talentRouter);
```

Then guard private routes individually:

```javascript
function requireAuth(req, res, next) {
  if (!req.user) return res.status(401).json({ error: '需要登入' });
  next();
}

// Private route
talentRouter.get('/me', requireAuth, async (req, res, next) => { ... });

// Public route (no guard)
talentRouter.get('/:id/profile', async (req, res, next) => { ... });
```

### Pitfall: Missing guard = auth bypass
When switching from `authMiddleware` (blocks all) to `optionalAuth` (blocks none), EVERY private route must have its own `requireAuth` guard. Missing one = unauthenticated access.

### Checklist after switching to optionalAuth:
- [ ] GET routes that return user-specific data have requireAuth
- [ ] POST/PUT/DELETE routes have requireAuth
- [ ] Public routes explicitly have NO guard (documented as intentional)
- [ ] Tests verify unauthenticated access returns 401 for private routes

## Pinia: defineStore Closure

Functions must be INSIDE the `defineStore` callback. Placing them outside breaks reactivity and access to store state.

```javascript
// ✅ CORRECT
export const useTalentStore = defineStore('talent', () => {
  const profile = ref(null);

  async function fetchPublicProfile(userId) {
    // Can access profile.value here
    const resp = await fetch(`/api/talent/${userId}/profile`);
    return resp.json();
  }

  return { profile, fetchPublicProfile };
});

// ❌ WRONG — function is outside the closure
export const useTalentStore = defineStore('talent', () => {
  const profile = ref(null);
  return { profile, fetchPublicProfile };
});

async function fetchPublicProfile(userId) { ... } // Can't access profile.value!
```

### How to detect:
The function appears AFTER the `});` closing the defineStore. Check line numbers of the return statement vs the function definition.

## Public Profile Endpoint Pattern

For public-facing profile pages, create a dedicated endpoint that whitelists public fields:

```javascript
talentRouter.get('/:id/profile', async (req, res, next) => {
  const profile = await TalentRepo.findByUserId(req.params.id);
  if (!profile) return res.status(404).json({ error: 'Not found' });

  // Whitelist: NEVER expose email, password_hash, line_user_id
  const publicProfile = {
    id: profile.user_id,
    name: profile.name,
    bio: profile.bio,
    skills: profile.skills,
    // ... other public fields
  };

  // Owner-only extras
  if (req.user && req.user.id === req.params.id) {
    publicProfile.growth_points = profile.growth_points;
  }

  res.json({ profile: publicProfile });
});
```

## Frontend: Public vs Owner Data Flow

```javascript
onMounted(async () => {
  if (isOwner.value && auth.token) {
    // Owner: use authenticated endpoints
    profile.value = await fetchMyProfile();
  } else {
    // Public: use unauthenticated endpoints (raw fetch, no Bearer)
    profile.value = await fetch(`/api/talent/${id}/profile`).then(r => r.json());
  }
});
```

### Pitfall: Using `auth.request()` for public endpoints
`auth.request()` adds Bearer token. For public endpoints, use raw `fetch()` so no token is sent. Otherwise, unauthenticated users get 401.
