"""Shared deterministic PAY-482 scenario classification."""
import json


def classify(value, test_status):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    matches = [name for name in ('stale', 'timeout', 'fail', 'ready') if name in (text or '').lower()]
    scenario = matches[0] if len(matches) == 1 else 'unknown'
    recommendation = {'stale': 'NOT READY', 'timeout': 'UNKNOWN', 'fail': 'NOT READY',
                      'ready': 'READY', 'unknown': 'UNKNOWN'}[scenario]
    reasons = {'stale': '模擬 CI 的受測版本與候選版本不一致。',
               'timeout': '模擬 CI 查詢逾時，缺少證據。',
               'fail': '模擬併發測試失敗，需修正後重跑。',
               'ready': '本機單元測試通過，示範資料的候選及受測版本相符。',
               'unknown': '請在輸入中明確指定一個 scenario：stale、timeout、fail 或 ready。'}
    if test_status != 'PASS':
        recommendation = 'UNKNOWN' if test_status == 'UNKNOWN' else 'NOT READY'
    reason = reasons[scenario] if test_status == 'PASS' else f'本機測試結果為 {test_status}。'
    return scenario, recommendation, reason
