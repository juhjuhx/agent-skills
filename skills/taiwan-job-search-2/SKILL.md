---
name: taiwan-job-search
description: Search job listings on 104, 1111, and 小雞上工 with login support
license: MIT
metadata:
  audience: general
  workflow: web-automation
---

## Targets
- 104 人力銀行 (104.com.tw)
- 1111 人力銀行 (1111.com.tw)
- 小雞上工 (chickpt.com.tw)

## MCP Selection
- **Login required** → use `firefox` (real browser with saved session, --connectExisting)
- **Quick search only** → use `playwright` (headless Chromium)

## Login Flow (Browser MCP)
1. Navigate to the site login page
2. Check if already logged in (look for username/avatar element)
3. If not logged in, ask user to log in manually in their browser
4. Once logged in, proceed with search

## Search Patterns

### 104
- URL: `https://www.104.com.tw/jobs/search/`
- Key parameters:
  - `keyword` - search keyword (e.g. 前端工程師)
  - `area` - area code (6001008000=台北市)
  - `ro` - role (0=全部)
- Key selectors: `.job-list-item` for listings, `.info-job__title` for title
- Extract: job title, company name, salary range, location, job URL

### 1111
- URL: `https://www.1111.com.tw/search/`
- Key parameters:
  - `ks` - keyword
  - `si` - area code
- Results in `.search-result-item` containers
- Extract: job title, company, salary, location, link

### 小雞上工
- URL: `https://www.chickpt.com.tw/jobs`
- Key parameters:
  - `q` - keyword
  - `area` - area code
- Extract: job title, pay rate, company, location, link

## Output Format
Return results as a table: 職稱 | 公司 | 薪資 | 地區 | 連結
