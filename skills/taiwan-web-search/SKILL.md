---
name: taiwan-web-search
description: General web search skill for Taiwan-specific websites using websearch + webfetch
license: MIT
metadata:
  audience: general
  workflow: web-search
---

## When to use
Use this when the user asks about any of these sites:
- 104.com.tw, 1111.com.tw, chickpt.com.tw (job boards)
- facebook.com/marketplace (FB Marketplace)
- carousell.tw (旋轉拍賣)
- bibian.com (比比昂)

## Method
1. First try `websearch` tool to discover relevant pages
2. Use `webfetch` to get content from specific URLs
3. For pages requiring JavaScript rendering or login, fall back to browser MCP skills

## Known alternatives
- 求職: 104, 1111, 小雞上工, yourator, cake
- 拍賣: 旋轉拍賣, 比比昂, 蝦皮 (shopee.tw)
- 二手: FB Marketplace, 旋轉拍賣

## Taiwan-Specific Network Issues

See `references/bilibili-cdn-taiwan.md` for Bilibili CDN troubleshooting from Taiwan ISPs (凱擘 routing issues, CDN switching, hosts file fixes).