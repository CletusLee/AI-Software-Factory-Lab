---
name: inventory-retry-invariants
description: INVENTORY-101 專案規則。相同同步事件重送需冪等，衝突不得改變原庫存項目。
---

# INVENTORY-101 retry invariants

相同同步 event ID、SKU 和 quantity 的重送必須冪等。event ID 相同而 SKU 或 quantity 不同時必須拒絕，並保留第一次建立的庫存項目。

審查時指出 payload 比較和拒絕分支，並引用 inventory entry 的實際更新或斷言。此專案使用 SKU 與庫存數量，不套用支付金額或 payment ledger 規則。
