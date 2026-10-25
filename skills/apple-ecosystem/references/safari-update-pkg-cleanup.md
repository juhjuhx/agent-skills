# Safari 更新套件清理

> 2026-07-07 新增。

## 問題

macOS 下載的 Safari 更新套件殘留在 `/Library/Updates/`，可能佔用數 GB。

## 診斷

```bash
ls -lh /Library/Updates/*/Safari*.pkg 2>/dev/null
du -sh /Library/Updates/ 2>/dev/null
```

## 清理

```bash
# 確認是已安裝的更新
# 刪除整個更新套件目錄（需要 sudo）
sudo rm -rf /Library/Updates/122-15866/
```

## 注意

- 需要 `sudo`，Hermes terminal 無法執行（無密碼輸入），需使用者手動執行
- 刪除前確認 Safari 已正常運作
