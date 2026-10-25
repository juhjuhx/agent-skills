---
name: taiwan-marketplace
description: Search products on 旋轉拍賣 and 比比昂 with login support
license: MIT
metadata:
  audience: general
  workflow: web-automation
---

## Targets
- 旋轉拍賣 (Carousell Taiwan) - carousell.tw
- 比比昂 (Bibian Japan proxy shopping) - bibian.com

## MCP Selection
- **旋轉拍賣** → use `playwright` (lightweight, usually no anti-bot)
- **比比昂** → use `firefox` (requires login for proxy shopping details, --connectExisting)

## Search Patterns

### 旋轉拍賣 (Carousell)
- URL: `https://www.carousell.tw/search/{keyword}/`
- Example: `https://www.carousell.tw/search/iphone%2015/`
- Filter by URL parameters (category, price range, condition)
- Results in: article elements with product data
- Extract: title, price (TWD), condition, seller name, link
- Check for "已售出" (sold) status

### 比比昂 (Bibian)
- URL: `https://www.bibian.com/search`
- Parameters: `q` (keyword)
- Sources: Japan Yahoo Auction, Rakuten, Mercari
- Results contain: product name, current bid/price (JPY), time left, shipping
- Login required for bidding/purchase details — use `browsermcp`
- Extract: item name, current price, bid count, time remaining, source platform, link

## Output Format
Return as: 商品名稱 | 價格 | 賣家/來源 | 狀態 | 連結