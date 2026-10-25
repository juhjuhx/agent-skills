---
name: hackintosh-hardware
description: Hackintosh hardware compatibility guide.
license: MIT
tags:
  - hackintosh
  - hardware
  - macos
  - opencore
category: research
---

## When to use
- User asks about Hackintosh compatible laptops or PC builds
- User asks about Intel 10th gen CPU + AMD GPU compatibility
- User asks if old MacBook can upgrade to latest macOS
- User needs OpenCore configuration advice

## Core Knowledge

### Intel 10th Gen CPU + AMD GPU Limitations
macOS does NOT natively support AMD discrete GPUs except very old GCN architecture like R9 M370X
- AMD Radeon RX 5000 series: Partial support via workarounds, limited stability
- AMD Radeon Pro 5300M/5500M: Native support in MacBook Pro 16 inch 2019

### Recommended Laptops
| Model | CPU | GPU | Compatibility |
|-------|-----|-----|---------------|
| Lenovo ThinkPad T490/T490s | i5-10210U | Intel UHD 620 | ⭐⭐⭐⭐⭐ |
| Dell Latitude 7400/7490 | i5-10210U | Intel UHD 620 | ⭐⭐⭐⭐⭐ |
| HP EliteBook 840 G7 | i5-10210U | Intel UHD 620 | ⭐⭐⭐⭐ |
| Acer Spin 5 | i5-10210U | Intel UHD 620 | ⭐⭐⭐⭐ |

Recommend prioritizing Intel integrated graphics business laptops, avoid AMD discrete GPU models

### Old MacBook macOS Upgrade Limits
| Model | Native Max | OpenCore Legacy Patcher |
|-------|-----------|------------------------|
| MacBook Pro 2012-2015 | macOS Monterey 12 | macOS Sonoma 14 |
| MacBook Pro 2016-2019 | macOS Ventura 13 | macOS Sonoma 14 |
| MacBook 2015-2017 | macOS High Sierra 10.13 | macOS Monterey 12 |
| MacBook Air 2012-2017 | macOS Monterey 12 | macOS Sonoma 14 |
| MacBook Pro 2020 Intel | macOS Monterey 12 | macOS Sonoma 14 |

### Best Choices
- MacBook Pro 15 inch 2018-2019 with i7-9750H or i7-10750H
  - AMD Radeon Pro 5500M native support
  - Used price about NT$15000-25000

- MacBook Pro 13 inch 2020 with i5-1038NG7
  - Dual graphics with Intel Iris, smooth Sonoma upgrade
  - Used price about NT$12000-18000

## Web Search Limitations
- Google and DuckDuckGo searches often blocked by JS challenges
- browser_navigate requires Chrome which needs agent-browser install
- Try direct visits to Dortania OpenCore Laptop Guide and InsanelyMac Forum

## Support Files
- references/search-workarounds.md for web search limitations and workarounds
- templates/buying-checklist.md for purchase checklist

## Resources
- Dortania OpenCore Laptop Guide at https://dortania.github.io/OpenCore-Laptop-Guide/
- OpenCore Legacy Patcher at https://github.com/dortania/OpenCore-Legacy-Patcher
- InsanelyMac Forum at https://www.insanelymac.com/
