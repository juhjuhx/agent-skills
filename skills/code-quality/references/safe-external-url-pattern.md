# Safe External URL Pattern

> Established 2026-06-26 from ArtFactory security audit.

## Problem

User-supplied URLs (`website_url`, `external_url`, `image_url`) passed directly to `href` attributes
without protocol validation. Vulnerable to:
- `javascript:alert(1)` — XSS via link click
- `data:text/html,<script>...` — XSS via data URI
- `//evil.example.com` — protocol-relative URL hijack

## Solution: Shared `safeExternalUrl` Helper

```javascript
// frontend/src/utils/safeExternalUrl.js
export function safeExternalUrl(url) {
  if (!url || typeof url !== 'string') return '';
  try {
    const parsed = new URL(url.trim());
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '';
  } catch {
    return '';
  }
}
```

## Usage in Vue Components

```javascript
import { safeExternalUrl } from '../utils/safeExternalUrl.js';

const safeWebsiteUrl = computed(() => safeExternalUrl(profile.value?.website_url));
```

```html
<a v-if="safeWebsiteUrl" :href="safeWebsiteUrl" target="_blank" rel="noopener noreferrer">
```

## Template Rule

Every `target="_blank"` link MUST have:
1. URL validated through `safeExternalUrl()`
2. `rel="noopener noreferrer"` attribute
3. `v-if` guard so unsafe URLs don't render at all

## Test Cases

```javascript
describe('safeExternalUrl', () => {
  test('https://valid.com → https://valid.com/', ...);
  test('http://valid.com → http://valid.com/', ...);
  test('javascript:alert(1) → empty string', ...);
  test('data:text/html,<script> → empty string', ...);
  test('//evil.example.com → empty string', ...);
  test('empty/null/undefined → empty string', ...);
  test('malformed url → empty string', ...);
});
```

## Refactoring Existing Code

Pages with inline `sanitizeHttpUrl()` (ContentDetailPage, JobDetailPage) should be refactored
to use the shared helper. The pattern is identical — only the import changes.
