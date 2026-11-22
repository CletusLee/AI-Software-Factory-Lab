---
name: pay482-retry-invariants
description: PAY-482 專案規則。相同事件 ID 搭配不同金額時應拒絕，並保留原始帳目。
---

# PAY-482 retry invariants

對同一個 webhook event ID，重送相同金額必須維持冪等。重送不同金額必須拒絕，且不得改變第一次寫入的帳目。

審查程式時，指出負責比較 event ID 與 amount 的分支，並確認衝突檢查發生在任何覆寫之前。

審查測試時，分別確認測試涵蓋相同 payload 重送、不同 event ID，以及相同 ID 不同金額時拒絕且原始 ledger entry 保持不變。引用實際檔案和斷言。不得把建議測試描述成已執行。
