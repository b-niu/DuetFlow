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


def test_find_mac_only_new_files():
    """测试在 Windows 大幅重整场景下，精准识别 Mac 端独有新增文件"""
    baseline = {
        "old_folder/file1.txt": {"hash": "h1"},
        "old_folder/file2.txt": {"hash": "h2"},
        "common.txt": {"hash": "h_comm"},
    }

    # Windows 端重整后：old_folder 整体被改名为 new_folder
    # 并且删除了某个文件，新增了本地文件
    win_manifest = {
        "new_folder/file1.txt": {"hash": "h1"},
        "new_folder/file2.txt": {"hash": "h2"},
        "common.txt": {"hash": "h_comm"},
        "win_local_new.txt": {"hash": "h_win_new"},
    }

    # Mac 端在 Win 重整期间：
    # 1. 依然保留旧结构 old_folder/file1.txt (来自 baseline) -> 不应被算作 Mac 新文件
    # 2. common.txt (来自 baseline) -> 不应被算作 Mac 新文件
    # 3. 产生了一个全新的文档 mac_note.md (不在 baseline，也不在 Win) -> 应被识别为 Mac 独有新文件！
    # 4. 产生了一个子目录文档 project/idea.docx (不在 baseline，也不在 Win) -> 应被识别为 Mac 独有新文件！
    # 5. 一个锁定的临时文件 (status=SKIPPED_LOCKED) -> 应被跳过
    mac_manifest = {
        "old_folder/file1.txt": {"hash": "h1"},
        "old_folder/file2.txt": {"hash": "h2"},
        "common.txt": {"hash": "h_comm"},
        "mac_note.md": {"size": 1024, "mtime": 1700000000, "hash": "h_mac_new"},
        "project/idea.docx": {"size": 2048, "mtime": 1700000010, "hash": "h_idea"},
        "locked_temp.tmp": {"status": "SKIPPED_LOCKED"},
    }

    found = merge.find_mac_only_new_files(win_manifest, mac_manifest, baseline)
    found_paths = [f["path"] for f in found]

    # 验证只有真正的 Mac 独有新文件被抓取出来
    assert found_paths == ["mac_note.md", "project/idea.docx"]
    assert found[0]["size"] == 1024
    assert found[0]["hash"] == "h_mac_new"

