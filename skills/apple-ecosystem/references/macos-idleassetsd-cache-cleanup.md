# idleassetsd 螢幕錄影暫存清理

## 問題

`/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/` 累積大量 UUID 命名的 `.mov` 檔案，可能佔用數十 GB。

這是 macOS 螢幕錄影（Cmd+Shift+5）的緩衝目錄。當錄製未完成儲存或被系統中斷時，檔案殘留在此處。

## 診斷

```bash
# 確認目錄內容與總容量
ls -la "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/"
du -sh "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/"
```

特徵：
- 檔名全是 UUID（如 `009BA758-7060-4479-8EE8-FB9B40C8FB97.mov`）
- 副檔名 `.mov`
- 容量從數百 MB 到數十 GB 不等
- 擁有者 `root:wheel`

## 清理

```bash
# 清空目錄內容（需要 sudo）
sudo rm -rf "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS"/*

# 或直接移除整個 Customer 子目錄（macOS 會自動重建）
sudo rm -rf "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS"
```

## 防呆

- 清理前先用 `ls` 確認只有 UUID 命名的 `.mov` 檔案
- 這些是暫存，刪除不會影響系統
- macOS 在下次需要時會自動重建目錄
- 如果使用者說「清理暫存」「釋放空間」「螢幕錄影殘留」，檢查此目錄
- 同層還可能有其他 `Customer/` 子目錄，但 `4KSDR240FPS` 是最常見的 4K 螢幕錄影緩衝區