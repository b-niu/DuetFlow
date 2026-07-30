"""测试 duetflow.merge 模块的三路合并逻辑与冷启动逻辑"""

from duetflow import merge


def test_cold_start_merge():
    """冷启动模式（baseline 为空）：测试按文件存在情况与修改时间合并"""
    win_manifest = {
        "a.txt": {"mtime": 100, "hash": "h1"},
        "b.txt": {"mtime": 200, "hash": "h2_win"},
        "c.txt": {"mtime": 100, "hash": "h3_same"},
    }
    mac_manifest = {
        "b.txt": {"mtime": 150, "hash": "h2_mac"},
        "c.txt": {"mtime": 100, "hash": "h3_same"},
        "d.txt": {"mtime": 100, "hash": "h4"},
    }
    baseline = {}

    plan = merge.three_way_merge(win_manifest, mac_manifest, baseline)
    plan_dict = {item["path"]: item["action"] for item in plan}

    assert plan_dict["a.txt"] == "WIN_TO_MAC"
    assert plan_dict["d.txt"] == "MAC_TO_WIN"
    assert plan_dict["c.txt"] == "SKIP"
    # b.txt Win 端的 mtime (200) 大于 Mac 端 (150)，故保留 Win 端
    assert plan_dict["b.txt"] == "WIN_TO_MAC"


def test_three_way_merge_cases():
    """正常三路合并模式：测试全部判决分支"""
    baseline = {
        "unchanged.txt": {"hash": "h1"},
        "win_mod.txt": {"hash": "h2_base"},
        "mac_mod.txt": {"hash": "h3_base"},
        "conflict.txt": {"hash": "h4_base"},
        "win_del.txt": {"hash": "h5_base"},
        "mac_del.txt": {"hash": "h6_base"},
        "mod_del.txt": {"hash": "h7_base"},
    }

    win_manifest = {
        "unchanged.txt": {"hash": "h1"},
        "win_mod.txt": {"hash": "h2_new"},
        "mac_mod.txt": {"hash": "h3_base"},
        "conflict.txt": {"hash": "h4_win"},
        "mac_del.txt": {"hash": "h6_base"},
        "mod_del.txt": {"hash": "h7_win"},
    }

    mac_manifest = {
        "unchanged.txt": {"hash": "h1"},
        "win_mod.txt": {"hash": "h2_base"},
        "mac_mod.txt": {"hash": "h3_new"},
        "conflict.txt": {"hash": "h4_mac"},
        "win_del.txt": {"hash": "h5_base"},
    }

    plan = merge.three_way_merge(win_manifest, mac_manifest, baseline)
    plan_dict = {item["path"]: item for item in plan}

    assert plan_dict["unchanged.txt"]["action"] == "SKIP"
    assert plan_dict["win_mod.txt"]["action"] == "WIN_TO_MAC"
    assert plan_dict["mac_mod.txt"]["action"] == "MAC_TO_WIN"
    assert plan_dict["conflict.txt"]["action"] == "CONFLICT"
    assert plan_dict["win_del.txt"]["action"] == "QUARANTINE_MAC"
    assert plan_dict["mac_del.txt"]["action"] == "QUARANTINE_WIN"
    assert plan_dict["mod_del.txt"]["action"] == "CONFLICT"
    assert plan_dict["mod_del.txt"]["reason"] == "modified_vs_deleted"
