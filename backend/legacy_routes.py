from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasources.datasource_manager import datasource_manager
from utils.auth_utils import TOKEN_CACHE, generate_token, get_current_user, is_admin_or_manager, require_admin, require_auth
from utils.db_utils import db_utils
from utils.schema_generator import generate_schema_for_datasource, save_schema_to_refer
from config.config_db import TABLE_REPORTS

sys_path = str(ROOT)
router = APIRouter()


def _clean_json_value(v):
    try:
        import math
        import pandas as pd
        if pd.isna(v):
            return ""
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return ""
    except Exception:
        pass
    return v


def _clean_json_rows(rows):
    return [{k: _clean_json_value(v) for k, v in row.items()} for row in rows]


def _require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise PermissionError("未登录")
    return user


from datasources.knowledge_manager import knowledge_manager
from core.suggestion_generator import SuggestionGenerator


@router.get("/knowledge_bases")
async def list_knowledge_bases():
    try:
        return JSONResponse(content={"success": True, "knowledge_bases": knowledge_manager.list_kbs()})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/knowledge_bases")
async def add_knowledge_base(request: Request):
    try:
        body = await request.json()
        result = knowledge_manager.add_kb(body.get("id"), body.get("name"), body.get("type", "rag"), body.get("description", ""), body.get("api_url", ""), body.get("headers", {}))
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/knowledge_bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    try:
        return JSONResponse(content=knowledge_manager.remove_kb(kb_id))
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/reports/generate")
async def generate_report(request: Request):
    from config.config_handler import load_model_client
    from core.report_runner import ReportRunner
    try:
        user = _require_user(request)
        user_id = user.get("id")
        body = await request.json()
        chat_id = body.get("chat_id")
        report_name = body.get("report_name", "个人维度出勤报表")
        user_rule = body.get("rule", "")
        if not chat_id:
            return JSONResponse(content={"success": False, "error": "chat_id 不能为空"}, status_code=400)
        configs = db_utils.list_global_configs("report_rule", user_id, True)
        report_config = next((cfg for cfg in configs if cfg.get("name") == report_name and cfg.get("is_enabled")), None)
        if not report_config:
            return JSONResponse(content={"success": False, "error": f"未找到启用的报表规则: {report_name}"}, status_code=404)
        rule_data = json.loads(report_config.get("content", "{}"))
        rule = user_rule or rule_data.get("rule", "")
        headers = rule_data.get("headers", [])
        if not rule:
            return JSONResponse(content={"success": False, "error": "报表规则不能为空"}, status_code=400)
        if not db_utils.get_chat_session(chat_id):
            return JSONResponse(content={"success": False, "error": f"会话不存在: {chat_id}"}, status_code=404)
        model_client = load_model_client()
        from backend.ask.services.progress_service import progress_service
        progress_service.init(chat_id)
        report_runner = ReportRunner(model_client, user_id=user_id, progress_hook=lambda t: progress_service.append_text(chat_id, t))
        excel_path = await report_runner.generate_report(chat_id=chat_id, rule_name=report_name, rule=rule, headers=headers)
        progress_service.done(chat_id)
        now_str = __import__("datetime").datetime.now().isoformat()
        metadata = {"type": "report_file", "report_name": report_name, "original_chat_id": chat_id, "rule_name": report_name, "file_path": excel_path, "generated_at": now_str}
        metadata_id = f"report_{chat_id}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}"
        db_utils.save_general_metadata(metadata_id, chat_id, metadata)
        return JSONResponse(content={"success": True, "filename": os.path.basename(excel_path), "file_path": excel_path, "report_name": report_name, "generated_at": now_str})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/reports/download/{chat_id}/{filename}")
async def download_report(chat_id: str, filename: str, request: Request, token: str = None):
    try:
        user = get_current_user(request)
        if not user and token:
            token_data = TOKEN_CACHE.get(token)
            if token_data:
                user = db_utils.get_user_by_id(token_data.get("id"))
        if not user:
            return JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)
        file_path = os.path.join(sys_path, "report_files", f"user_{user.get('id')}", chat_id, filename)
        if not os.path.exists(file_path):
            return JSONResponse(content={"success": False, "error": "文件不存在"}, status_code=404)
        return FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/reports/list/{chat_id}")
async def list_reports(request: Request, chat_id: str, token: str = None):
    try:
        user = get_current_user(request)
        if not user and token:
            user_info = TOKEN_CACHE.get(token)
            if user_info:
                user = db_utils.get_user_by_id(user_info.get("id") or user_info.get("user_id"))
        if not user:
            return JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)
        metadata_list = db_utils.get_metadata_by_chat_id(chat_id)
        reports = []
        for meta in metadata_list:
            content = meta.get("general_content", {})
            if content.get("type") == "report_file":
                reports.append({"filename": os.path.basename(content.get("file_path", "")), "report_name": content.get("report_name", ""), "generated_at": content.get("generated_at", "")})
        return JSONResponse(content={"success": True, "reports": reports})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/generate")
async def generate_fixed_report(request: Request):
    try:
        user = _require_user(request)
        user_id = user.get("id")
        user_prefix = f"user_{user_id}"
        form_data = await request.form()
        detail_file = form_data.get("detail_file")
        summary_file = form_data.get("summary_file")
        report_type = form_data.get("report_type", "人事考勤报表")
        report_type_map = {"hr_attendance": "人事考勤报表", "dept_attendance": "部门维度考勤报表", "multi_month_hr": "多月个人维度报表", "multi_month_dept": "多月部门维度报表", "人事考勤报表": "人事考勤报表", "部门维度考勤报表": "部门维度考勤报表", "多月个人维度报表": "多月个人维度报表", "多月部门维度报表": "多月部门维度报表"}
        report_type = report_type_map.get(report_type, report_type)
        if not detail_file or not summary_file:
            return JSONResponse(content={"success": False, "error": "请上传明细表和汇总表"}, status_code=400)
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"report_{timestamp}"
        report_dir = os.path.join(sys_path, "report_files", user_prefix, report_id)
        sources_dir = os.path.join(report_dir, "sources")
        os.makedirs(sources_dir, exist_ok=True)
        detail_path = os.path.join(sources_dir, detail_file.filename)
        summary_path = os.path.join(sources_dir, summary_file.filename)
        with open(detail_path, "wb") as f:
            f.write(await detail_file.read())
        with open(summary_path, "wb") as f:
            f.write(await summary_file.read())
        file_name_map = {"部门维度考勤报表": "部门维度考勤报表.xlsx", "多月个人维度报表": "多月个人维度报表.xlsx", "多月部门维度报表": "多月部门维度报表.xlsx"}
        display_file_name = file_name_map.get(report_type, "人力考勤报表.xlsx")
        output_filename = f"{report_type}_{timestamp}.xlsx"
        output_path = os.path.join(report_dir, output_filename)
        if report_type == "部门维度考勤报表":
            from core.dept_report_generator import generate_dept_report
            result = generate_dept_report(detail_path, summary_path, output_path)
        elif report_type == "多月个人维度报表":
            from core.multi_month_report_generator import generate_multi_month_report_from_raw
            result = generate_multi_month_report_from_raw(detail_path, summary_path, output_path)
        elif report_type == "多月部门维度报表":
            from core.multi_month_dept_report_generator import generate_multi_month_dept_report_from_raw
            result = generate_multi_month_dept_report_from_raw(detail_path, summary_path, output_path)
        else:
            from core.report_generator import generate_hr_attendance_report
            result = generate_hr_attendance_report(detail_path, summary_path, output_path)
        if not result.get("success"):
            return JSONResponse(content={"success": False, "error": result.get("message", "报表生成失败")}, status_code=500)
        db_utils.save_report(report_id=report_id, user_id=user_id, report_type=report_type, detail_file=detail_file.filename, summary_file=summary_file.filename, original_file=output_filename, file_path=report_dir, row_count=result.get("row_count", 0), column_count=result.get("column_count", 0), yellow_cells_count=result.get("yellow_cells_count", 0), problem_count=result.get("problem_count", 0))
        return JSONResponse(content={"success": True, "report_id": report_id, "report_type": report_type, "row_count": result.get("row_count", 0), "column_count": result.get("column_count", 0), "yellow_cells_count": result.get("yellow_cells_count", 0), "problem_count": result.get("problem_count", 0), "summary_text": result.get("summary_text", ""), "preview_data": result.get("preview_data", [])[:10], "columns": result.get("columns", []), "file_path": output_path, "display_file_name": display_file_name, "generated_at": __import__("datetime").datetime.now().isoformat()})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/desensitize")
async def toggle_report_desensitize(request: Request):
    try:
        user = _require_user(request)
        body = await request.json()
        report_id = body.get("report_id")
        enable = body.get("enable", True)
        column_config = body.get("column_config")
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        report_dir = report_record.get("file_path", "")
        original_file = report_record.get("original_file")
        original_path = os.path.join(report_dir, original_file)
        import pandas as pd
        if enable:
            from utils.desensitize import auto_detect_column_desensitize, desensitize_dataframe_by_columns
            df = pd.read_excel(original_path)
            column_config = column_config or report_record.get("desensitize_columns") or auto_detect_column_desensitize(df.columns.tolist())
            masked_df = desensitize_dataframe_by_columns(df, column_config)
            timestamp = report_id.replace("report_", "")
            desensitized_filename = f"人事考勤报表_脱敏_{timestamp}.xlsx"
            desensitized_path = os.path.join(report_dir, desensitized_filename)
            masked_df.to_excel(desensitized_path, index=False)
            db_utils.execute_query(
                f"UPDATE {TABLE_REPORTS} SET desensitized_file = %s, is_desensitized = TRUE, desensitize_columns = %s WHERE report_id = %s",
                (desensitized_filename, json.dumps(column_config), report_id)
            )
            preview_data = _clean_json_rows(masked_df.head(10).to_dict(orient="records"))
            return JSONResponse(content={"success": True, "message": "脱敏完成", "desensitized_file_path": desensitized_path, "is_desensitized": True, "preview_data": preview_data, "columns": masked_df.columns.tolist(), "column_config": column_config})
        for f in os.listdir(report_dir):
            if "脱敏" in f:
                os.remove(os.path.join(report_dir, f))
        db_utils.execute_query(
            f"UPDATE {TABLE_REPORTS} SET desensitized_file = NULL, is_desensitized = FALSE WHERE report_id = %s",
            (report_id,)
        )
        df = pd.read_excel(original_path)
        preview_data = _clean_json_rows(df.head(10).to_dict(orient="records"))
        return JSONResponse(content={"success": True, "message": "已取消脱敏", "is_desensitized": False, "preview_data": preview_data, "columns": df.columns.tolist()})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/desensitize/methods")
async def get_desensitize_methods():
    try:
        from utils.desensitize import get_available_desensitize_methods
        return JSONResponse(content={"success": True, "methods": get_available_desensitize_methods()})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/desensitize/preview")
async def preview_desensitize_columns(request: Request, report_id: str):
    try:
        _require_user(request)
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        import pandas as pd
        from utils.desensitize import auto_detect_column_desensitize
        original_path = os.path.join(report_record.get("file_path", ""), report_record.get("original_file"))
        df = pd.read_excel(original_path)
        columns = df.columns.tolist()
        suggested_config = auto_detect_column_desensitize(columns)
        return JSONResponse(content={"success": True, "columns": columns, "suggested_config": suggested_config, "saved_config": report_record.get("desensitize_columns"), "is_desensitized": report_record.get("is_desensitized", False)})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/ask")
async def create_report_ask_session(request: Request):
    try:
        user = _require_user(request)
        user_id = user.get("id")
        body = await request.json()
        report_id = body.get("report_id")
        use_desensitized = body.get("use_desensitized", False)
        if not report_id:
            return JSONResponse(content={"success": False, "error": "缺少 report_id"}, status_code=400)
        existing_metadata = db_utils.get_general_metadata(f"report_ask_{report_id}")
        if existing_metadata:
            existing_chat_id = existing_metadata.get("chat_id")
            if existing_chat_id and db_utils.get_chat_session(existing_chat_id):
                datasource_name = existing_metadata.get("datasource_name", "")
                return JSONResponse(content={"success": True, "chat_id": existing_chat_id, "datasource_name": datasource_name, "display_name": f"报表数据_{report_id[-8:]}", "is_existing": True})
        report_dir = os.path.join(sys_path, "report_files", f"user_{user_id}", report_id)
        if not os.path.exists(report_dir):
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        file_to_use = None
        for f in os.listdir(report_dir):
            if f.endswith(".xlsx") and ((use_desensitized and "脱敏" in f) or (not use_desensitized and "脱敏" not in f)):
                file_to_use = f
                break
        if not file_to_use:
            return JSONResponse(content={"success": False, "error": "报表文件不存在"}, status_code=404)
        file_path = os.path.join(report_dir, file_to_use)
        datasource_display_name = f"报表数据_{report_id[-8:]}"
        datasource_storage_key = f"user_{user_id}:{datasource_display_name}"
        import pandas as pd
        xl = pd.ExcelFile(file_path)
        actual_sheet = "报表数据" if "报表数据" in xl.sheet_names else (xl.sheet_names[0] if xl.sheet_names else "Sheet1")
        ds_config = {"files": [file_to_use], "file_configs": {file_to_use: {"table_header_rows": "1", "sub_name_rows": "", "sheet_name": actual_sheet}}, "file_dir": report_dir, "skip_preprocess": True}
        existing = datasource_manager.get_datasource(datasource_storage_key)
        if not existing:
            datasource_manager.add_datasource(datasource_display_name, "excel", ds_config, "0", user_id)
        else:
            datasource_manager.update_datasource_files(datasource_storage_key, report_dir, [file_to_use], ds_config["file_configs"], skip_preprocess=True)
        chat_id = f"excel_ask_{__import__('uuid').uuid4().hex[:8]}_{int(time.time())}"
        db_utils.insert_chat_session(chat_id, "0", datasource_storage_key, user_id)
        split_dir = os.path.join(sys_path, "split_files", f"user_{user_id}")
        chat_split_dir = os.path.join(split_dir, chat_id)
        os.makedirs(chat_split_dir, exist_ok=True)
        import shutil
        shutil.copy2(file_path, os.path.join(chat_split_dir, file_to_use))
        ask_metadata = {"type": "report_ask_session", "report_id": report_id, "chat_id": chat_id, "use_desensitized": use_desensitized, "datasource_name": datasource_storage_key, "created_at": __import__('datetime').datetime.now().isoformat()}
        db_utils.save_general_metadata(f"report_ask_{report_id}", chat_id, ask_metadata)
        return JSONResponse(content={"success": True, "chat_id": chat_id, "datasource_name": datasource_storage_key, "display_name": datasource_display_name})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/list")
async def list_user_reports(request: Request):
    try:
        user = _require_user(request)
        user_id = user.get("id")
        is_admin = user.get("role") == "admin"
        reports = db_utils.list_reports(user_id=None if is_admin else user_id)
        for report in reports:
            report_dir = report.get("file_path", "")
            if report_dir and os.path.exists(report_dir):
                report["has_desensitized"] = report.get("is_desensitized", False) and bool(report.get("desensitized_file"))
                report["source_files"] = []
                sources_dir = os.path.join(report_dir, "sources")
                if os.path.exists(sources_dir):
                    report["source_files"] = os.listdir(sources_dir)
        return JSONResponse(content={"success": True, "reports": reports})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/report/{report_id}")
async def delete_report(report_id: str, request: Request):
    try:
        user = _require_user(request)
        user_id = user.get("id")
        is_admin = user.get("role") == "admin"
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        if not is_admin and report_record.get("user_id") != user_id:
            return JSONResponse(content={"success": False, "error": "无权删除此报表"}, status_code=403)
        report_dir = report_record.get("file_path", "")
        if report_dir and os.path.exists(report_dir):
            import shutil
            shutil.rmtree(report_dir)
        db_utils.delete_report(report_id)
        datasource_storage_key = f"user_{user_id}:报表数据_{report_id[-8:]}"
        if datasource_manager.get_datasource(datasource_storage_key):
            datasource_manager.remove_datasource(datasource_storage_key)
        return JSONResponse(content={"success": True, "message": "报表已删除"})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.put("/report/{report_id}/rename")
async def rename_report(report_id: str, request: Request):
    try:
        user = _require_user(request)
        user_id = user.get("id")
        is_admin = user.get("role") == "admin"
        body = await request.json()
        new_name = body.get("display_file_name", "").strip()
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        if not is_admin and report_record.get("user_id") != user_id:
            return JSONResponse(content={"success": False, "error": "无权修改此报表"}, status_code=403)
        success = db_utils.update_report_name(report_id, new_name)
        return JSONResponse(content={"success": success, "message": "重命名成功" if success else "重命名失败", "display_file_name": new_name}, status_code=200 if success else 500)
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/preview/{report_id}")
async def preview_report_data(report_id: str, request: Request, token: str = None):
    try:
        user = get_current_user(request)
        if not user and token:
            token_data = TOKEN_CACHE.get(token)
            if token_data:
                user = db_utils.get_user_by_id(token_data.get("id"))
        if not user:
            return JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)
        import pandas as pd
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        report_dir = report_record.get("file_path", "")
        file_to_preview = report_record.get("desensitized_file") if report_record.get("is_desensitized") and report_record.get("desensitized_file") else report_record.get("original_file")
        if not file_to_preview:
            return JSONResponse(content={"success": False, "error": "未找到报表文件"}, status_code=404)
        df = pd.read_excel(os.path.join(report_dir, file_to_preview))
        preview_data = _clean_json_rows(df.head(10).to_dict(orient="records"))
        return JSONResponse(content={"success": True, "preview_data": preview_data, "columns": df.columns.tolist(), "row_count": len(df), "column_count": len(df.columns), "is_desensitized": report_record.get("is_desensitized", False)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/download/{report_id}")
async def download_fixed_report(report_id: str, request: Request, desensitized: bool = False, token: str = None):
    try:
        user = get_current_user(request)
        if not user and token:
            token_data = TOKEN_CACHE.get(token)
            if token_data:
                user = db_utils.get_user_by_id(token_data.get("id"))
        if not user:
            return JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)
        report_dir = os.path.join(sys_path, "report_files", f"user_{user.get('id')}", report_id)
        if not os.path.exists(report_dir):
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        target_file = None
        for f in os.listdir(report_dir):
            if f.endswith(".xlsx") and ((desensitized and "脱敏" in f) or (not desensitized and "脱敏" not in f)):
                target_file = f
                break
        if not target_file:
            return JSONResponse(content={"success": False, "error": "报表文件不存在"}, status_code=404)
        report_info = db_utils.get_report(report_id)
        if report_info and report_info.get("display_file_name"):
            download_filename = report_info.get("display_file_name")
            if not download_filename.endswith(".xlsx"):
                download_filename += ".xlsx"
        elif report_info and report_info.get("report_type") == "部门维度考勤报表":
            download_filename = "部门维度考勤报表.xlsx"
        else:
            download_filename = "人力考勤报表.xlsx"
        return FileResponse(path=os.path.join(report_dir, target_file), filename=download_filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/report/download-info/{report_id}")
async def get_report_download_info(report_id: str, request: Request):
    try:
        _require_user(request)
        report_info = db_utils.get_report(report_id)
        if not report_info:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        filename = report_info.get("display_file_name") or report_info.get("original_file") or "报表.xlsx"
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        return JSONResponse(content={"success": True, "filename": filename, "report_id": report_id})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/ask-question")
async def ask_report_question(request: Request):
    try:
        body = await request.json()
        report_id = body.get("report_id")
        question = body.get("question")
        memory_count = body.get("memory_count", 0)
        if not report_id or not question:
            return JSONResponse(content={"success": False, "error": "缺少 report_id 或 question"}, status_code=400)
        user = _require_user(request)
        user_id = user.get("id")
        report_dir = os.path.join(sys_path, "report_files", f"user_{user_id}", report_id)
        if not os.path.exists(report_dir):
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        file_to_use = None
        for f in os.listdir(report_dir):
            if f.endswith(".xlsx") and "脱敏" not in f:
                file_to_use = f
                break
        if not file_to_use:
            return JSONResponse(content={"success": False, "error": "报表文件不存在"}, status_code=404)
        file_path = os.path.join(report_dir, file_to_use)
        from backend.ask.api.excel_api import ask_api
        chat_id = f"excel_{__import__('uuid').uuid4().hex[:8]}_{int(time.time())}"
        db_utils.insert_chat_session(chat_id, "0", f"user_{user_id}:报表数据_{report_id[-8:]}", user_id)
        split_dir = os.path.join(sys_path, "split_files", f"user_{user_id}", chat_id)
        os.makedirs(split_dir, exist_ok=True)
        import shutil
        copied_path = os.path.join(split_dir, file_to_use)
        shutil.copy2(file_path, copied_path)
        db_utils.save_general_metadata(f"excel_upload_{chat_id}", chat_id, {"excel_paths": [copied_path], "title": "Excel 分析", "timestamp": int(time.time() * 1000)})
        return await ask_api(request, {"chatid": chat_id, "question": question, "memory_count": memory_count})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/ai-edit")
async def ai_edit_report(request: Request):
    try:
        body = await request.json()
        sample_data = body.get("sample_data", [])
        columns = body.get("columns", [])
        user_request = body.get("user_request", "")
        full_data = body.get("full_data", [])
        if not user_request or not columns or not full_data:
            return JSONResponse(content={"success": False, "error": "缺少必要参数"}, status_code=400)
        from services.ai_table_editor import ai_edit_table
        result = ai_edit_table(sample_data, columns, user_request, full_data)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/report/create")
async def create_report_alias(request: Request):
    return await generate_fixed_report(request)


@router.get("/report/full-data/{report_id}")
async def get_report_full_data(report_id: str, request: Request, token: str = None):
    try:
        user = get_current_user(request)
        if not user and token:
            token_data = TOKEN_CACHE.get(token)
            if token_data:
                user = db_utils.get_user_by_id(token_data.get("id"))
        if not user:
            return JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)
        import pandas as pd
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        file_to_read = report_record.get("desensitized_file") if report_record.get("is_desensitized") and report_record.get("desensitized_file") else report_record.get("original_file")
        df = pd.read_excel(os.path.join(report_record.get("file_path", ""), file_to_read))
        return JSONResponse(content={"success": True, "data": _clean_json_rows(df.to_dict(orient="records")), "columns": df.columns.tolist()})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.put("/report/update/{report_id}")
async def update_report_data(report_id: str, request: Request):
    try:
        _require_user(request)
        import pandas as pd
        report_record = db_utils.get_report(report_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "报表不存在"}, status_code=404)
        body = await request.json()
        df = pd.DataFrame(body.get("data", []), columns=body.get("columns", []))
        file_to_update = report_record.get("desensitized_file") if report_record.get("is_desensitized") and report_record.get("desensitized_file") else report_record.get("original_file")
        file_path = os.path.join(report_record.get("file_path", ""), file_to_update)
        df.to_excel(file_path, index=False)
        db_utils.update_report_row_count(report_id, len(df))
        return JSONResponse(content={"success": True, "row_count": len(df)})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/dashboard/generate")
async def generate_dashboard(request: Request):
    try:
        import re
        user = _require_user(request)
        user_id = user.get("id")
        user_prefix = f"user_{user_id}"
        form_data = await request.form()
        personal_file = form_data.get("personal_file")
        dept_file = form_data.get("dept_file")
        month = form_data.get("month", None)
        if not personal_file or not dept_file:
            return JSONResponse(content={"success": False, "error": "请上传个人维度和部门维度Excel文件"}, status_code=400)
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        dashboard_id = f"dashboard_{timestamp}"
        dashboard_dir = os.path.join(sys_path, "dashboard_files", user_prefix, dashboard_id)
        sources_dir = os.path.join(dashboard_dir, "sources")
        os.makedirs(sources_dir, exist_ok=True)
        personal_path = os.path.join(sources_dir, personal_file.filename)
        dept_path = os.path.join(sources_dir, dept_file.filename)
        with open(personal_path, "wb") as f:
            f.write(await personal_file.read())
        with open(dept_path, "wb") as f:
            f.write(await dept_file.read())
        template_dir = os.path.join(sys_path, "dashboard_preview")
        sys.path.insert(0, template_dir)
        from generate_dashboard import generate_data_from_both, save_data_js
        sys.path.pop(0)
        personal_data, dept_data, month_out = generate_data_from_both(personal_path, dept_path, month=month)
        if month_out is None:
            for fn in [personal_file.filename, dept_file.filename]:
                match = re.search(r"(\d{4}年\d{1,2}月)", fn)
                if match:
                    month_out = match.group(1)
                    break
            if month_out is None:
                month_out = __import__("datetime").datetime.now().strftime("%Y年%m月")
        save_data_js(personal_data, dept_data, dashboard_dir, month_out)
        row_count = len(personal_data)
        style_dir = os.path.join(template_dir, "style4_business_cyan")
        with open(os.path.join(style_dir, "index.html"), "r", encoding="utf-8") as f:
            html_template = f.read()
        with open(os.path.join(style_dir, "css", "style.css"), "r", encoding="utf-8") as f:
            css_content = f.read()
        with open(os.path.join(style_dir, "js", "dashboard.js"), "r", encoding="utf-8") as f:
            js_dashboard = f.read()
        with open(os.path.join(template_dir, "shared", "echarts.min.js"), "r", encoding="utf-8") as f:
            echarts_content = f.read()
        with open(os.path.join(dashboard_dir, "shared", "data.js"), "r", encoding="utf-8") as f:
            data_js = f.read()
        merged_html = html_template.replace('<link rel="stylesheet" href="css/style.css">', f'<style>\n{css_content}\n</style>').replace('<script src="../shared/echarts.min.js"></script>', '<script>' + echarts_content + '</script>').replace('<script src="../shared/data.js"></script>', '<script>' + data_js + '</script>').replace('<script src="js/dashboard.js"></script>', '<script>' + js_dashboard + '</script>')
        html_filename = f"{dashboard_id}.html"
        html_path = os.path.join(dashboard_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(merged_html)
        db_utils.save_report(report_id=dashboard_id, user_id=user_id, report_type="dashboard", detail_file=personal_file.filename, summary_file="", original_file=html_filename, file_path=dashboard_dir, row_count=row_count, column_count=0, yellow_cells_count=0, problem_count=0)
        return JSONResponse(content={"success": True, "dashboard_id": dashboard_id, "row_count": row_count, "month": month_out, "display_file_name": f"人力资源效能分析大屏_{month_out}", "generated_at": __import__("datetime").datetime.now().isoformat()})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/dashboard/static/{dashboard_id}/screenshot")
async def screenshot_dashboard(dashboard_id: str, request: Request, title: str = ""):
    try:
        report_info = db_utils.get_report(dashboard_id)
        if not report_info:
            return JSONResponse(content={"error": "大屏不存在"}, status_code=404)
        dashboard_dir = report_info.get("file_path", "")
        html_files = [f for f in os.listdir(dashboard_dir) if f.endswith(".html")]
        if not html_files:
            return JSONResponse(content={"error": "HTML文件不存在"}, status_code=404)
        html_path = os.path.join(dashboard_dir, html_files[0])
        from playwright.async_api import async_playwright
        display_title = title if title else report_info.get("display_file_name", "人力资源效能分析大屏")
        safe_title = display_title.replace("'", "\\'").replace('"', '\\"')
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="chrome")
            page = await browser.new_page(viewport={"width": 2560, "height": 1440})
            await page.goto(f"file:///{html_path.replace(os.sep, '/')}", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            await page.evaluate(f"var h1 = document.querySelector('.header-title h1'); if (h1) h1.textContent = '{safe_title}'; document.title = '{safe_title}';")
            await page.wait_for_timeout(500)
            png_data = await page.screenshot(full_page=True, type="png")
            await browser.close()
        return StreamingResponse(iter([png_data]), media_type="image/png", headers={"Content-Disposition": f'attachment; filename="{dashboard_id}.png"'})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/dashboard/static/{dashboard_id}/{path:path}")
async def serve_dashboard_static(dashboard_id: str, path: str, request: Request):
    import mimetypes
    report_info = db_utils.get_report(dashboard_id)
    if not report_info:
        return JSONResponse(content={"success": False, "error": "大屏不存在"}, status_code=404)
    dashboard_dir = report_info.get("file_path", "")
    file_path = os.path.realpath(os.path.join(dashboard_dir, path))
    dashboard_dir_real = os.path.realpath(dashboard_dir)
    if not file_path.startswith(dashboard_dir_real):
        return JSONResponse(content={"success": False, "error": "非法路径"}, status_code=403)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return JSONResponse(content={"success": False, "error": "文件不存在"}, status_code=404)
    content_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(file_path, media_type=content_type or "application/octet-stream")


@router.get("/dashboard/list")
async def list_dashboards(request: Request):
    try:
        user = _require_user(request)
        dashboards = [r for r in db_utils.list_reports(user_id=user.get("id")) if r.get("report_type") == "dashboard"]
        return JSONResponse(content={"success": True, "dashboards": dashboards})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/dashboard/{dashboard_id}")
async def delete_dashboard(dashboard_id: str, request: Request):
    try:
        user = _require_user(request)
        report_record = db_utils.get_report(dashboard_id)
        if not report_record:
            return JSONResponse(content={"success": False, "error": "大屏不存在"}, status_code=404)
        if report_record.get("user_id") != user.get("id"):
            return JSONResponse(content={"success": False, "error": "无权删除此大屏"}, status_code=403)
        dashboard_dir = report_record.get("file_path", "")
        if dashboard_dir and os.path.exists(dashboard_dir):
            import shutil
            shutil.rmtree(dashboard_dir)
        db_utils.delete_report(dashboard_id)
        return JSONResponse(content={"success": True, "message": "大屏已删除"})
    except PermissionError as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/")
async def read_root():
    return JSONResponse(content={"message": "AskBI Backend API", "version": "1.0.0"})



@router.get("/datasources")
async def list_datasources(request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        all_datasources = datasource_manager.list_datasources()
        users_list = db_utils.list_users()
        user_map = {u["id"]: u["username"] for u in users_list}
        for ds in all_datasources:
            owner_id = ds.get("owner_id")
            ds["owner_username"] = user_map.get(owner_id, f"用户{owner_id}") if owner_id else "系统管理员"
        filtered = all_datasources if can_view_all else [ds for ds in all_datasources if ds.get("owner_id") == user_id and user_id is not None]
        return JSONResponse(content={"success": True, "datasources": filtered})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/datasources")
async def add_datasource(request: Request):
    try:
        user = get_current_user(request)
        owner_id = user.get("id") if user else None
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            name = body.get("name")
            ds_type = body.get("type")
            config = body.get("config", {})
            knowledge_id = body.get("knowledge_id", "0")
        else:
            form_data = await request.form()
            name = form_data.get("name")
            ds_type = form_data.get("type")
            knowledge_id = form_data.get("knowledge_id", "0")
            config = {}
            if ds_type == "excel":
                files = form_data.getlist("file")
                header_rows = form_data.getlist("table_header_rows")
                sub_name_rows = form_data.getlist("sub_name_rows")
                if files:
                    user_prefix = f"user_{owner_id}" if owner_id else "admin"
                    ds_file_dir = os.path.join(ROOT, "datasources", "excel_files", user_prefix, name)
                    os.makedirs(ds_file_dir, exist_ok=True)
                    all_file_names = []
                    all_file_configs = {}
                    for i, f in enumerate(files):
                        file_path = os.path.join(ds_file_dir, f.filename)
                        with open(file_path, "wb") as buffer:
                            content = await f.read()
                            buffer.write(content)
                        all_file_names.append(f.filename)
                        all_file_configs[f.filename] = {
                            "table_header_rows": header_rows[i] if i < len(header_rows) else "",
                            "sub_name_rows": sub_name_rows[i] if i < len(sub_name_rows) else "",
                        }
                    config["files"] = all_file_names
                    config["file_configs"] = all_file_configs
                    config["file_dir"] = ds_file_dir
        result = datasource_manager.add_datasource(name, ds_type, config, knowledge_id, owner_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/datasources/{name}")
async def delete_datasource(name: str):
    try:
        return JSONResponse(content=datasource_manager.remove_datasource(name))
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/datasources")
async def delete_datasource_query(name: str = Query(...)):
    try:
        return JSONResponse(content=datasource_manager.remove_datasource(name))
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/datasources/batch_delete")
async def batch_delete_datasources(request: Request):
    try:
        body = await request.json()
        names = body.get("names", [])
        if not names or not isinstance(names, list):
            return JSONResponse(content={"success": False, "error": "请提供要删除的数据源名称列表"}, status_code=400)
        success_count = 0
        failed_items = []
        for name in names:
            try:
                result = datasource_manager.remove_datasource(name)
                if result.get("success"):
                    success_count += 1
                else:
                    failed_items.append({"name": name, "error": result.get("message", "删除失败")})
            except Exception as e:
                failed_items.append({"name": name, "error": str(e)})
        return JSONResponse(content={"success": success_count > 0, "deleted_count": success_count, "failed_items": failed_items})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/datasources/{name}")
async def get_datasource(name: str):
    try:
        ds = datasource_manager.get_datasource(name)
        return JSONResponse(content={"success": bool(ds), "datasource": ds} if ds else {"success": False, "error": "数据源不存在"}, status_code=200 if ds else 404)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/datasources/{name}/test")
async def test_datasource(name: str):
    try:
        # 1. 先测试连通性
        test_result = datasource_manager.test_datasource(name)
        if not test_result.get("success"):
            return JSONResponse(content=test_result)

        # 2. 连通后自动刷新元数据
        loop = __import__("asyncio").get_event_loop()
        ds = datasource_manager.get_datasource(name)
        is_cross_schema = ds.get("is_cross_schema", False) if ds else False

        if is_cross_schema:
            schemas = datasource_manager.get_datasource_schemas(name)
            connector = datasource_manager.get_connector(name)
            if hasattr(connector, "get_cross_schema_metadata"):
                schema_data = connector.get_cross_schema_metadata(schemas)
            else:
                schema_data = {"is_cross_schema": True, "schemas": schemas, "table_index": [], "tables": {}}
                for schema in schemas:
                    single_schema_data = await loop.run_in_executor(None, generate_schema_for_datasource, name, schema)
                    for table_name, table_info in single_schema_data.get("tables", {}).items():
                        full_name = f"{schema}.{table_name}"
                        schema_data["tables"][full_name] = table_info
                        schema_data["table_index"].append({"full_name": full_name, "schema": schema, "table": table_name, "comment": table_info.get("comment", "")})
        else:
            schema_data = await loop.run_in_executor(None, generate_schema_for_datasource, name)

        table_count = len(schema_data.get("tables", {})) if schema_data else 0

        if schema_data and table_count > 0:
            # 数据库类型：同时存入数据库和 refer 文件夹
            storage_info = []
            if ds and ds.get("type") != "excel":
                db_utils.upsert_chat_knowledge(name, schema_data=schema_data)
                storage_info.append("database")
            # Excel 类型和数据库类型都存一份到 refer 文件夹（便于文件备份和离线使用）
            save_path = await loop.run_in_executor(None, save_schema_to_refer, name, schema_data)
            storage_info.append("file")

            test_result["metadata_refreshed"] = True
            test_result["tables_count"] = table_count
            test_result["storage"] = storage_info
            test_result["message"] = f"连接成功，已刷新元数据 ({table_count} 个表)"
        else:
            test_result["metadata_refreshed"] = False
            test_result["message"] = f"连接成功，但未找到表结构"

        return JSONResponse(content=test_result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": f"测试连通性成功，但刷新元数据失败: {str(e)}"}, status_code=500)


@router.post("/datasources/{name}/generate_metadata")
async def generate_metadata(name: str):
    try:
        loop = __import__("asyncio").get_event_loop()
        ds = datasource_manager.get_datasource(name)
        is_cross_schema = ds.get("is_cross_schema", False) if ds else False
        if is_cross_schema:
            schemas = datasource_manager.get_datasource_schemas(name)
            connector = datasource_manager.get_connector(name)
            if hasattr(connector, "get_cross_schema_metadata"):
                schema_data = connector.get_cross_schema_metadata(schemas)
            else:
                schema_data = {"is_cross_schema": True, "schemas": schemas, "table_index": [], "tables": {}}
                for schema in schemas:
                    single_schema_data = await loop.run_in_executor(None, generate_schema_for_datasource, name, schema)
                    for table_name, table_info in single_schema_data.get("tables", {}).items():
                        full_name = f"{schema}.{table_name}"
                        schema_data["tables"][full_name] = table_info
                        schema_data["table_index"].append({"full_name": full_name, "schema": schema, "table": table_name, "comment": table_info.get("comment", "")})
        else:
            schema_data = await loop.run_in_executor(None, generate_schema_for_datasource, name)
        if not schema_data or not schema_data.get("tables"):
            return JSONResponse(content={"success": False, "error": "未能在数据源中找到任何有效的表"}, status_code=400)
        if ds and ds.get("type") != "excel":
            db_utils.upsert_chat_knowledge(name, schema_data=schema_data)
            return JSONResponse(content={"success": True, "message": "元数据生成并已存入数据库", "tables_count": len(schema_data.get("tables", {})), "storage": "database", "is_cross_schema": is_cross_schema})
        save_path = await loop.run_in_executor(None, save_schema_to_refer, name, schema_data)
        return JSONResponse(content={"success": True, "message": "元数据生成成功 (Excel 文件存储)", "tables_count": len(schema_data.get("tables", {})), "schema_file": save_path, "storage": "file"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/datasources/{name}/tables")
async def list_tables(name: str):
    try:
        return JSONResponse(content={"success": True, "tables": datasource_manager.get_tables(name)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/datasources/{name}/tables/{schema}/{table}/columns")
async def list_columns(name: str, schema: str, table: str):
    try:
        return JSONResponse(content={"success": True, "columns": datasource_manager.get_table_columns(name, schema, table)})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/refer/schema")
async def get_schema_metadata(datasource_name: str = Query(...)):
    try:
        data = None
        knowledge = db_utils.get_chat_knowledge(datasource_name)
        if knowledge and knowledge.get("schema_data"):
            data = knowledge["schema_data"]
        if not data:
            from utils.schema_generator import safe_refer_name
            safe_name = safe_refer_name(datasource_name)
            schema_file = os.path.join("refer", safe_name, f"{safe_name}_metadata.json")
            if os.path.exists(schema_file):
                with open(schema_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
        if not data:
            return JSONResponse(content={"success": False, "error": f"未找到数据源 '{datasource_name}' 的元数据。请先执行元数据生成。", "tables": {}, "total_tables": 0, "datasource_name": datasource_name}, status_code=404)
        tables_info = {}
        for table_name, table_info in data.get("tables", {}).items():
            tables_info[table_name] = {"comment": table_info.get("comment", ""), "columns": table_info.get("columns", []), "sample_data": table_info.get("sample_data", [])[:5]}
        return JSONResponse(content={"success": True, "tables": tables_info, "total_tables": len(tables_info), "datasource_name": datasource_name})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/global_configs")
async def list_global_configs(request: Request, category: str = None):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        can_view_all = is_admin_or_manager(user)
        configs = db_utils.list_global_configs(category, user_id, can_view_all)
        return JSONResponse(content={"success": True, "configs": configs})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/global_configs")
async def save_global_config(request: Request):
    try:
        user = get_current_user(request)
        user_id = user.get("id") if user else None
        body = await request.json()
        success = db_utils.upsert_global_config(body.get("category"), body.get("name"), body.get("content"), body.get("is_enabled", True), body.get("id"), body.get("scope_type", "universal"), body.get("scope_datasources", []), user_id)
        return JSONResponse(content={"success": success, "message": "保存成功" if success else "保存失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.delete("/global_configs/{config_id}")
async def delete_global_config(config_id: int):
    try:
        success = db_utils.delete_global_config(config_id)
        return JSONResponse(content={"success": success, "message": "删除成功" if success else "删除失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.patch("/global_configs/{config_id}/toggle")
async def toggle_global_config(config_id: int, request: Request):
    try:
        body = await request.json()
        success = db_utils.toggle_global_config(config_id, body.get("is_enabled"))
        return JSONResponse(content={"success": success, "message": "状态已更新" if success else "更新失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/knowledge/global")
async def get_global_knowledge():
    try:
        file_path = os.path.join(ROOT, "knowledge", "global_rules.txt")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")
        return JSONResponse(content={"success": True, "content": content, "path": file_path})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/knowledge/global")
async def save_global_knowledge(request: Request):
    try:
        body = await request.json()
        file_path = os.path.join(ROOT, "knowledge", "global_rules.txt")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.get("content") or "")
        return JSONResponse(content={"success": True, "message": "保存成功"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/knowledge/temp/{datasource_name}")
async def get_temp_knowledge(datasource_name: str):
    try:
        data = db_utils.get_chat_knowledge(datasource_name)
        return JSONResponse(content={"success": True, "content": data.get("content", "") if data else "", "vocabulary": data.get("vocabulary", []) if data else [], "reference_sql": data.get("reference_sql", []) if data else []})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/knowledge/temp")
async def save_temp_knowledge(request: Request):
    try:
        body = await request.json()
        success = db_utils.upsert_chat_knowledge(body.get("datasource_name"), content=body.get("content"), vocabulary=body.get("vocabulary"), reference_sql=body.get("reference_sql"))
        return JSONResponse(content={"success": success, "message": "保存成功" if success else "保存失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
        user = db_utils.verify_user(body.get("username", "").strip(), body.get("password", ""))
        if not user:
            return JSONResponse(content={"success": False, "error": "用户名或密码错误"}, status_code=401)
        token = generate_token()
        TOKEN_CACHE[token] = user
        return JSONResponse(content={"success": True, "token": token, "user": user})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/auth/logout")
async def logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        TOKEN_CACHE.pop(auth_header[7:], None)
    return JSONResponse(content={"success": True, "message": "已登出"})


@router.get("/auth/me")
async def get_current_user_info(request: Request):
    user = get_current_user(request)
    return JSONResponse(content={"success": True, "user": user}) if user else JSONResponse(content={"success": False, "error": "未登录"}, status_code=401)


@router.get("/auth/users")
async def list_users(request: Request):
    try:
        require_admin(request)
        return JSONResponse(content={"success": True, "users": db_utils.list_users()})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=403 if "权限" in str(e) else 500)


@router.post("/auth/users")
async def create_user(request: Request):
    try:
        require_admin(request)
        body = await request.json()
        return JSONResponse(content=db_utils.create_user(body.get("username", "").strip(), body.get("password", ""), body.get("role", "user")))
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=403 if "权限" in str(e) else 500)


@router.delete("/auth/users/{user_id}")
async def delete_user(user_id: int, request: Request):
    try:
        require_admin(request)
        success = db_utils.delete_user(user_id)
        return JSONResponse(content={"success": success, "message": "删除成功" if success else "删除失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=403 if "权限" in str(e) else 500)


@router.patch("/auth/users/{user_id}/password")
async def update_user_password(user_id: int, request: Request):
    try:
        require_admin(request)
        body = await request.json()
        success = db_utils.update_user_password(user_id, body.get("new_password", ""))
        return JSONResponse(content={"success": success, "message": "密码更新成功" if success else "密码更新失败"}, status_code=200 if success else 500)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=403 if "权限" in str(e) else 500)


@router.post("/suggestions")
async def get_suggestions(request: Request):
    try:
        body = await request.json()
        chat_id = body.get("chat_id")
        file_name = body.get("file_name", "未知文件")
        sheet_name = body.get("sheet_name", "Sheet1")
        columns = body.get("columns", [])
        sample_data = body.get("sample_data")
        qa_history = body.get("qa_history")
        if not chat_id:
            return JSONResponse(content={"success": False, "error": "缺少 chat_id"}, status_code=400)
        if not columns:
            return JSONResponse(content={"success": False, "error": "缺少列信息"}, status_code=400)
        generator = SuggestionGenerator()
        questions = await generator.generate_for_excel(file_name=file_name, sheet_name=sheet_name, columns=columns, sample_data=sample_data, qa_history=qa_history)
        return JSONResponse(content={"success": True, "suggestions": questions})
    except Exception:
        try:
            from core.suggestion_generator import _fallback_questions
            fallback = _fallback_questions(body.get("columns", []) if 'body' in locals() else [])
        except Exception:
            fallback = ['这张表有多少行数据？', '可以先做一个数据概览吗？', '哪些字段最值得关注？', '这张表有没有异常值？']
        return JSONResponse(content={"success": True, "suggestions": fallback, "fallback": True})
