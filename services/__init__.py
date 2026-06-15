#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务模块

📅 2026.03.19 新增
📝 变更说明：创建服务模块，包含各种业务服务
"""

from .ai_table_editor import AITableEditor, ai_edit_table

__all__ = ['AITableEditor', 'ai_edit_table']