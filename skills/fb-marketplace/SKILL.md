---
name: fb-marketplace
description: Search products on Facebook Marketplace with login support
license: MIT
metadata:
  audience: general
  workflow: web-automation
---

## Target
- Facebook Marketplace (facebook.com/marketplace)

## MCP Selection
- **Always use `firefox`** — Facebook has strong anti-bot detection
- Playwright headless mode will be detected and blocked
- Must use `--connectExisting` mode (connected to your running Firefox)

## Prerequisites
1. User must be logged into Facebook in Firefox
2. Firefox must be running with Marionette enabled (`marionette.enabled=true` in about:config)
3. First verify login status before searching

## Search Flow
1. Navigate to `https://www.facebook.com/marketplace`
2. Wait for page to fully load (dynamic content, may need 3-5s)
3. For location-based search, navigate to:
   - `https://www.facebook.com/marketplace/{city}/search?query={keyword}`
   - Example: `https://www.facebook.com/marketplace/taipei/search?query=iphone`
4. Scroll to trigger infinite scroll loading
5. Extract product cards: title, price, location, posted time, link

## Important Notes
- Facebook changes DOM structure frequently — prefer URL-based navigation
- If CAPTCHA appears, pause and ask user to solve it in their browser
- Rate limiting: wait 2-3 seconds between scrolls/actions
- If page shows "login required", ask user to log in manually
- Do NOT attempt to bypass Facebook's anti-bot with stealth scripts

## Output Format
Return as: 商品名稱 | 價格 | 地區 | 刊登時間 | 連結