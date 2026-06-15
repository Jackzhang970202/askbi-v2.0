#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能改表服务 - Agno 版本

使用 OpenAI 兼容接口替代 AutoGen，保持规则引擎不变。
"""

import json
import math
import re
from typing import Dict, List, Any, Optional

from openai import OpenAI

from core import _load_config


class AITableEditor:
    """AI智能改表服务"""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def analyze_and_generate_rules(
        self,
        sample_data: List[Dict],
        columns: List[str],
        user_request: str
    ) -> Dict[str, Any]:
        """分析用户需求并生成修改规则"""
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(sample_data, columns, user_request)

            result = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
                extra_body={"enable_thinking": False},
            )
            response_text = (result.choices[0].message.content or "").strip()

            if not response_text:
                return {"success": False, "error": "AI返回内容为空"}

            rules = self._extract_json(response_text)

            if not rules:
                return {"success": False, "error": "无法解析AI返回的修改规则"}

            return {
                "success": True,
                "rules": rules,
                "description": rules.get("description", "修改表格")
            }

        except Exception as e:
            return {"success": False, "error": f"AI分析失败: {str(e)}"}

    def _build_system_prompt(self) -> str:
        return """你是表格数据处理专家。根据用户的自然语言描述生成JSON格式的修改规则。

## 输出格式（只返回JSON，不要其他文字）

```json
{
    "action": "modify",
    "description": "修改描述",
    "rules": [{"type": "规则类型", ...}]
}
```

## 支持的规则类型

1. fill_empty: 填充空值
   {"type": "fill_empty", "columns": ["列名或*"], "fill_value": "填充值"}

2. replace_value: 替换值
   {"type": "replace_value", "column": "列名", "condition": "空值", "new_value": "新值"}

3. add_column: 在最后添加列
   {"type": "add_column", "column_name": "新列名", "default_value": "默认值"}

4. insert_column: 在指定列前面插入新列
   {"type": "insert_column", "column_name": "新列名", "before_column": "目标列名", "default_value": "默认值"}

5. extract_column: 从其他列提取/计算信息填入新列
   {"type": "extract_column", "column_name": "新列名", "before_column": "目标列名（可选）", "formula": "提取公式"}

6. delete_column: 删除列
   {"type": "delete_column", "column": "列名"}

7. formula: 条件公式（对符合条件的行进行计算）
   {"type": "formula", "target_column": "目标列", "condition": "条件表达式", "formula": "计算公式"}

8. cell_update: 精确修改某个单元格（行号从1开始）
   {"type": "cell_update", "row": 行号, "column": "列名", "value": "新值"}

9. row_formula: 对指定行进行公式计算
   {"type": "row_formula", "row": 行号, "column": "列名", "formula": "原值+1"}

## 重要规则

1. 当用户提到"第X行"或"某个单元格"时，必须使用 cell_update 或 row_formula 类型
2. 公式中的"原值"会被替换为当前单元格的实际值后再计算
3. 行号从1开始计数
4. 当用户说"在XX列前面加一列"时，使用 insert_column 类型
5. 当用户需要从现有列提取信息时，使用 extract_column 类型"""

    def _build_user_prompt(self, sample_data: List[Dict], columns: List[str], user_request: str) -> str:
        sample_str = "数据预览（前10行）：\n"
        for i, row in enumerate(sample_data[:10]):
            row_display = {k: v for k, v in list(row.items())[:10]}
            sample_str += f"第{i+1}行: {row_display}\n"

        total_rows = len(sample_data)
        return f"""表格列名：{columns}
总行数：{total_rows}行

{sample_str}

用户需求：{user_request}

请根据用户需求返回JSON规则。行号从1开始计数。返回JSON规则："""

    def _extract_json(self, text: str) -> Optional[Dict]:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass

        return None

    def apply_rules(self, data: List[Dict], columns: List[str], rules: Dict[str, Any]) -> Dict[str, Any]:
        """将修改规则应用到完整数据集"""
        try:
            modified_data = []
            modified_cells = []
            rule_list = rules.get("rules", [])

            for row_idx, row in enumerate(data):
                new_row = dict(row)

                for rule in rule_list:
                    rule_type = rule.get("type")

                    if rule_type == "replace_value":
                        result = self._apply_replace_value(new_row, row_idx, rule, columns)
                        modified_cells.extend(result["cells"])

                    elif rule_type == "add_column":
                        col_name = rule.get("column_name")
                        if col_name:
                            if row_idx == 0 and col_name not in columns:
                                columns.append(col_name)
                            new_row[col_name] = rule.get("default_value", "")
                            modified_cells.append({
                                "row": row_idx, "column": col_name,
                                "old_value": None, "new_value": new_row[col_name]
                            })

                    elif rule_type == "insert_column":
                        col_name = rule.get("column_name")
                        before_col = rule.get("before_column")
                        if col_name:
                            if row_idx == 0 and col_name not in columns:
                                if before_col and before_col in columns:
                                    insert_idx = columns.index(before_col)
                                    columns.insert(insert_idx, col_name)
                                else:
                                    columns.append(col_name)
                            new_row[col_name] = rule.get("default_value", "")
                            modified_cells.append({
                                "row": row_idx, "column": col_name,
                                "old_value": None, "new_value": new_row[col_name]
                            })

                    elif rule_type == "extract_column":
                        col_name = rule.get("column_name")
                        before_col = rule.get("before_column")
                        formula = rule.get("formula", "")
                        if col_name:
                            if row_idx == 0 and col_name not in columns:
                                if before_col and before_col in columns:
                                    insert_idx = columns.index(before_col)
                                    columns.insert(insert_idx, col_name)
                                else:
                                    columns.append(col_name)
                            extracted_value = self._evaluate_extract_formula(formula, new_row, columns)
                            new_row[col_name] = extracted_value
                            modified_cells.append({
                                "row": row_idx, "column": col_name,
                                "old_value": None, "new_value": extracted_value
                            })

                    elif rule_type == "delete_column":
                        col_name = rule.get("column")
                        if col_name in new_row:
                            del new_row[col_name]
                        if col_name in columns:
                            columns.remove(col_name)

                    elif rule_type == "formula":
                        result = self._apply_formula(new_row, row_idx, rule, columns)
                        modified_cells.extend(result["cells"])

                    elif rule_type == "fill_empty":
                        result = self._apply_fill_empty(new_row, row_idx, rule)
                        modified_cells.extend(result["cells"])

                    elif rule_type == "row_formula":
                        target_row = rule.get("row", 0)
                        if row_idx + 1 == target_row:
                            result = self._apply_row_formula(new_row, row_idx, rule, columns)
                            modified_cells.extend(result["cells"])

                    elif rule_type == "cell_update":
                        target_row = rule.get("row", 0)
                        if row_idx + 1 == target_row:
                            result = self._apply_cell_update(new_row, row_idx, rule)
                            modified_cells.extend(result["cells"])

                modified_data.append(new_row)

            return {
                "success": True,
                "data": modified_data,
                "columns": columns,
                "modified_cells": modified_cells,
                "modified_count": len(modified_cells)
            }

        except Exception as e:
            return {"success": False, "error": f"应用规则失败: {str(e)}"}

    def _apply_replace_value(self, row: Dict, row_idx: int, rule: Dict, columns: List[str]) -> Dict:
        modified_cells = []
        column = rule.get("column")
        condition = rule.get("condition", "")
        new_value = rule.get("new_value", "")
        target_cols = [column] if column and column in row else columns

        for col in target_cols:
            if col not in row:
                continue
            old_value = row.get(col)
            should_replace = False
            if condition in ("空值", "空", "empty"):
                should_replace = old_value is None or old_value == "" or (isinstance(old_value, float) and math.isnan(old_value))
            elif condition == "非空":
                should_replace = old_value is not None and old_value != ""
            elif condition == "全部":
                should_replace = True
            if should_replace:
                row[col] = new_value
                modified_cells.append({"row": row_idx, "column": col, "old_value": old_value, "new_value": new_value})

        return {"cells": modified_cells}

    def _apply_fill_empty(self, row: Dict, row_idx: int, rule: Dict) -> Dict:
        modified_cells = []
        target_cols = rule.get("columns", ["*"])
        fill_value = rule.get("fill_value", "")
        if "*" in target_cols:
            target_cols = list(row.keys())
        for col in target_cols:
            if col not in row:
                continue
            old_value = row.get(col)
            if old_value is None or old_value == "" or (isinstance(old_value, float) and math.isnan(old_value)):
                row[col] = fill_value
                modified_cells.append({"row": row_idx, "column": col, "old_value": old_value, "new_value": fill_value})
        return {"cells": modified_cells}

    def _apply_formula(self, row: Dict, row_idx: int, rule: Dict, columns: List[str]) -> Dict:
        modified_cells = []
        target_column = rule.get("target_column")
        condition = rule.get("condition", "")
        formula = rule.get("formula", "")
        if not target_column or target_column not in columns:
            return {"cells": []}

        should_apply = True
        if condition:
            try:
                cond = condition
                for col in columns:
                    if col in cond:
                        val = row.get(col)
                        try:
                            val = float(val) if val is not None and val != '' else 0
                        except Exception:
                            val = 0
                        cond = cond.replace(col, str(val))
                cond = cond.replace("或", " or ").replace("且", " and ")
                cond = cond.replace("大于", ">").replace("小于", "<").replace("等于", "==")
                cond = re.sub(r'[^\d\s\.\+\-\*\/\<\>\=\!orandnot]+', ' ', cond)
                cond = ' '.join(cond.split())
                if cond.strip():
                    should_apply = bool(eval(cond))
            except Exception:
                should_apply = False

        if should_apply:
            old_value = row.get(target_column)
            new_value = formula
            if formula.startswith("'") and formula.endswith("'"):
                new_value = formula[1:-1]
            elif formula.startswith('"') and formula.endswith('"'):
                new_value = formula[1:-1]
            else:
                try:
                    calc_formula = formula
                    try:
                        old_val = float(old_value) if old_value is not None and old_value != '' else 0
                    except Exception:
                        old_val = 0
                    calc_formula = calc_formula.replace("原值", str(old_val))
                    calc_formula = calc_formula.replace("value", str(old_val))
                    sorted_cols = sorted([c for c in columns if c != target_column], key=len, reverse=True)
                    for col in sorted_cols:
                        if col in calc_formula:
                            val = row.get(col)
                            try:
                                val = float(val) if val is not None and val != '' else 0
                            except Exception:
                                val = 0
                            calc_formula = calc_formula.replace(col, str(val))
                    calc_formula = re.sub(r'[^\d\s\.\+\-\*\/]+', ' ', calc_formula)
                    calc_formula = ' '.join(calc_formula.split())
                    if calc_formula.strip() and any(c in calc_formula for c in '+-*/'):
                        new_value = eval(calc_formula)
                except Exception:
                    new_value = formula
            row[target_column] = new_value
            modified_cells.append({"row": row_idx, "column": target_column, "old_value": old_value, "new_value": new_value})

        return {"cells": modified_cells}

    def _apply_row_formula(self, row: Dict, row_idx: int, rule: Dict, columns: List[str]) -> Dict:
        modified_cells = []
        target_column = rule.get("column")
        formula = rule.get("formula", "")
        if not target_column or target_column not in row:
            return {"cells": []}
        old_value = row.get(target_column)
        try:
            calc_formula = formula
            try:
                old_val = float(old_value) if old_value is not None and old_value != '' else 0
            except Exception:
                old_val = 0
            calc_formula = calc_formula.replace("原值", str(old_val))
            calc_formula = calc_formula.replace("value", str(old_val))
            calc_formula = re.sub(r'[^\d\s\.\+\-\*\/]+', ' ', calc_formula)
            calc_formula = ' '.join(calc_formula.split())
            if calc_formula.strip() and any(c in calc_formula for c in '+-*/'):
                new_value = eval(calc_formula)
            else:
                new_value = formula
        except Exception:
            new_value = formula
        row[target_column] = new_value
        modified_cells.append({"row": row_idx, "column": target_column, "old_value": old_value, "new_value": new_value})
        return {"cells": modified_cells}

    def _apply_cell_update(self, row: Dict, row_idx: int, rule: Dict) -> Dict:
        modified_cells = []
        target_column = rule.get("column")
        value = rule.get("value")
        if not target_column or target_column not in row:
            return {"cells": []}
        old_value = row.get(target_column)
        new_value = value
        if isinstance(value, str) and ('原值' in value or 'value' in value or any(c in value for c in '+-*/')):
            try:
                calc_formula = value
                try:
                    old_val = float(old_value) if old_value is not None and old_value != '' else 0
                except Exception:
                    old_val = 0
                calc_formula = calc_formula.replace("原值", str(old_val))
                calc_formula = calc_formula.replace("value", str(old_val))
                calc_formula = re.sub(r'[^\d\s\.\+\-\*\/]+', ' ', calc_formula)
                calc_formula = ' '.join(calc_formula.split())
                if calc_formula.strip() and any(c in calc_formula for c in '+-*/'):
                    new_value = eval(calc_formula)
            except Exception:
                new_value = value
        row[target_column] = new_value
        modified_cells.append({"row": row_idx, "column": target_column, "old_value": old_value, "new_value": new_value})
        return {"cells": modified_cells}

    def _evaluate_extract_formula(self, formula: str, row: Dict, columns: List[str]) -> str:
        try:
            substr_match = re.search(r'substr\s*\(\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', formula)
            if substr_match:
                col_name = substr_match.group(1)
                start = int(substr_match.group(2))
                length = int(substr_match.group(3))
                return str(row.get(col_name, ''))[start:start+length]

            concat_match = re.search(r'concat\s*\(([^)]+)\)', formula)
            if concat_match:
                values = []
                for arg in concat_match.group(1).split(','):
                    arg = arg.strip()
                    if arg in row:
                        values.append(str(row.get(arg, '')))
                    elif arg.startswith("'") or arg.startswith('"'):
                        values.append(arg[1:-1])
                    else:
                        values.append(arg)
                return ''.join(values)

            split_match = re.search(r'split\s*\(\s*(\w+)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\[\s*(\d+)\s*\]', formula)
            if split_match:
                col_value = str(row.get(split_match.group(1), ''))
                parts = col_value.split(split_match.group(2))
                idx = int(split_match.group(3))
                return parts[idx] if idx < len(parts) else ''

            if formula in row:
                return str(row.get(formula, ''))

            calc_formula = formula
            for col in sorted(columns, key=len, reverse=True):
                if col in calc_formula:
                    val = row.get(col, 0)
                    try:
                        val = float(val) if val is not None and val != '' else 0
                    except Exception:
                        val = 0
                    calc_formula = calc_formula.replace(col, str(val))
            calc_formula = re.sub(r'[^\d\s\.\+\-\*\/\(\)]+', ' ', calc_formula)
            calc_formula = ' '.join(calc_formula.split())
            if calc_formula.strip() and any(c in calc_formula for c in '+-*/'):
                return str(eval(calc_formula))
            return formula
        except Exception:
            return formula


# 全局单例
_editor_instance = None


def _get_editor() -> AITableEditor:
    global _editor_instance
    if _editor_instance is None:
        conf = _load_config()
        client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
        _editor_instance = AITableEditor(client, conf["model"])
    return _editor_instance


def ai_edit_table(sample_data: List[Dict], columns: List[str], user_request: str, full_data: List[Dict]) -> Dict[str, Any]:
    """AI智能改表主入口"""
    editor = _get_editor()
    analyze_result = editor.analyze_and_generate_rules(sample_data, columns, user_request)
    if not analyze_result.get("success"):
        return analyze_result
    rules = analyze_result.get("rules", {})
    apply_result = editor.apply_rules(full_data, columns, rules)
    if apply_result.get("success"):
        apply_result["description"] = analyze_result.get("description", "修改表格")
        apply_result["rules"] = rules
    return apply_result
