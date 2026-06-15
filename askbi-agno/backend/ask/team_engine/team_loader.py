"""团队加载: 从 DB 读取团队配置（含嵌套解析）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from utils.db_utils import db_utils

logger = logging.getLogger(__name__)


def load_team(team_id: int) -> Optional[Dict[str, Any]]:
    """从 DB 加载完整团队配置（含成员列表）。"""
    team = db_utils.get_team(team_id)
    if not team:
        return None

    members = db_utils.list_team_members(team_id)
    return {
        "id": team["id"],
        "name": team["name"],
        "description": team.get("description", ""),
        "mode": team["mode"],
        "leader_config": team.get("leader_config", {}),
        "max_iterations": team.get("max_iterations", 10),
        "members": members,
    }


def load_team_shallow(team_id: int) -> Optional[Dict[str, Any]]:
    """加载团队基本信息（不含成员详情）。"""
    return db_utils.get_team(team_id)
