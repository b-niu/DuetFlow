"""测试 duetflow.trash 模块的熔断判定与隔离区功能"""

from duetflow import trash


def test_circuit_breaker_empty():
    """测试总文件数为 0 时的熔断判定"""
    triggered, q_count, ratio = trash.circuit_breaker_check([], 0)
    assert not triggered
    assert q_count == 0
    assert ratio == 0.0


def test_circuit_breaker_trigger_ratio():
    """测试比例超标触发熔断"""
    # 10 个文件中 6 个待隔离，比例 60% > 20% 且 隔离数 6 > 5
    plan = [{"action": "QUARANTINE_WIN", "path": f"f{i}.txt"} for i in range(6)]
    triggered, q_count, ratio = trash.circuit_breaker_check(plan, 10, max_ratio=0.20, max_count=50)
    assert triggered
    assert q_count == 6
    assert ratio == 0.60


def test_circuit_breaker_normal():
    """测试正常变动不触发熔断"""
    # 100 个文件中 2 个待隔离，比例 2%
    plan = [{"action": "QUARANTINE_WIN", "path": "f1.txt"}, {"action": "WIN_TO_MAC", "path": "f2.txt"}]
    triggered, q_count, ratio = trash.circuit_breaker_check(plan, 100, max_ratio=0.20, max_count=50)
    assert not triggered
    assert q_count == 1
