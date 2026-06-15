from typing import Optional, Set
import uuid
import os
from config.config_db import TABLE_CHAT_SESSION
from utils.db_utils import db_utils
from utils.white_list_utils import read_white_list_files


class SessionManager:
    """
    Session management class for handling chat sessions, white lists, and knowledge bases.
    """
    
    def __init__(self, chat_id: Optional[str] = None, white_list: Optional[str] = None, knowledge_id: Optional[str] = None):
        self.white_list_tables: Set[str] = self.validate_white_list(white_list)
        self.knowledge_id = self.validate_knowledge_id(knowledge_id)
        self.chat_id = self.validate_chat_id(chat_id)
        self.initialize_session()
    
    def init_database_tables(self):
        """
        初始化数据库表
        """
        try:
            db_utils.create_tables()
        except Exception as e:
            print(f"[WARN] 数据库表初始化失败: {e}")
    
    def validate_white_list(self, white_list_folder: Optional[str] = None) -> Set[str]:
        """
        从refer_list文件夹读取白名单表名
        """
        if not white_list_folder:
            white_list_folder = "refer_list"
        
        # 读取白名单文件
        white_list_tables = read_white_list_files(white_list_folder)
        
        # 如果白名单为空，不再抛出异常，而是返回空集合
        # 在后续校验逻辑 (utils/white_list_utils.py) 中，如果白名单为空则默认允许所有表
        if not white_list_tables:
            print(f"[INFO] 白名单文件夹 {white_list_folder} 为空，默认允许所有表访问")
        
        return white_list_tables
    
    def validate_knowledge_id(self, knowledge_id):
        """
        验证知识库ID是否有效
        0: 不使用知识库
        1: 使用知识库
        """
        if knowledge_id is None:
            return None
        
        # 转换为字符串以便处理
        knowledge_id_str = str(knowledge_id).strip()
        
        # 只接受1或0作为有效值
        if knowledge_id_str in ['0', '1']:
            return knowledge_id_str
        else:
            raise ValueError(f"知识库ID {knowledge_id} 无效，只能是1或0")
    
    def validate_chat_id(self, chat_id):
        """
        验证会话ID是否存在
        """
        if not chat_id:
            # 生成新的UUID作为会话ID
            return str(uuid.uuid4())
        
        # 检查会话ID是否存在
        chat_session = db_utils.get_chat_session(chat_id)
        if chat_session:
            return chat_id
        
        # 如果是新会话（数据库中还没有），也允许通过，后续 initialize_session 会插入
        return chat_id
    
    def initialize_session(self):
        """
        初始化会话
        """
        # 检查会话是否已存在
        existing_session = db_utils.get_chat_session(self.chat_id)
        if not existing_session:
            # 创建新会话
            success = db_utils.insert_chat_session(
                chat_id=self.chat_id,
                knowledge_id=self.knowledge_id
            )
            if not success:
                raise Exception(f"创建会话失败: chat_id={self.chat_id}")
    
    def get_white_list_tables(self) -> Set[str]:
        """
        获取白名单允许的表名集合
        """
        return self.white_list_tables
    
    def validate_table_names_in_code(self, code: str) -> bool:
        """
        检查代码中出现的表名是否都在白名单中
        """
        from utils.white_list_utils import validate_table_names_in_code
        invalid_tables = validate_table_names_in_code(code, self.white_list_tables)
        return len(invalid_tables) == 0
