"""
外接知识库管理器
管理 RAG 知识库配置
"""
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path

class KnowledgeManager:
    def __init__(self, config_file: str = "knowledge_bases_config.json"):
        self.config_file = config_file
        self.config_path = Path(config_file)
        self.knowledge_bases = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载知识库配置失败: {e}")
                return {}
        # 默认提供一个 ID 为 1 的示例 (如果有的话)
        return {
            "1": {
                "name": "官方 RAG 知识库",
                "description": "默认启用的 RAG 检索系统",
                "type": "rag",
                "active": True
            }
        }
    
    def _save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_bases, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存知识库配置失败: {e}")
    
    def add_kb(self, kb_id: str, name: str, kb_type: str, description: str = "", api_url: str = "", headers: Dict[str, str] = None) -> Dict[str, Any]:
        self.knowledge_bases[kb_id] = {
            "name": name,
            "type": kb_type,
            "description": description,
            "api_url": api_url,
            "headers": headers or {},
            "active": True
        }
        self._save_config()
        return {"success": True, "message": "知识库添加成功"}
    
    def remove_kb(self, kb_id: str) -> Dict[str, Any]:
        if kb_id in self.knowledge_bases:
            del self.knowledge_bases[kb_id]
            self._save_config()
            return {"success": True, "message": "知识库删除成功"}
        return {"success": False, "message": "知识库不存在"}
    
    def list_kbs(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": kb_id,
                **info
            }
            for kb_id, info in self.knowledge_bases.items()
        ]

knowledge_manager = KnowledgeManager()

