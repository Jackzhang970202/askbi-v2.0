from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "backend"
for path in [str(ROOT.parent), str(ROOT), str(BACKEND_ROOT)]:
    if path in sys.path:
        sys.path.remove(path)
for path in [str(ROOT.parent), str(ROOT), str(BACKEND_ROOT)]:
    sys.path.insert(0, path)

from backend.ask.api.excel_api import router as excel_router
from backend.ask.api.bi_api import router as bi_router
from backend.ask.api.skill_api import router as skill_router
from backend.ask.api.agent_api import router as agent_router
from backend.ask.api.team_api import router as team_router
from backend.ask.api.memory_api import router as memory_router
from backend.legacy_routes import router as legacy_router

APP_ROOT_PATH = "/askbi"
app = FastAPI(title="askbi-agno backend", version="2.0.0", root_path=APP_ROOT_PATH)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(excel_router, prefix="/excel")
app.include_router(bi_router)
app.include_router(skill_router, prefix="/skills")
app.include_router(agent_router, prefix="/agents")
app.include_router(team_router, prefix="/teams")
app.include_router(memory_router, prefix="/memory")
app.include_router(legacy_router)


@app.on_event("startup")
async def startup_init():
    from utils.db_utils import db_utils

    try:
        db_utils.create_tables()
        db_utils.create_default_admin()
    except Exception:
        pass

    # 幂等种子：内置技能与智能体
    try:
        from backend.ask.skills.skill_manager import skill_manager
        skill_manager.seed_builtin_skills()
    except Exception:
        pass

    try:
        from backend.ask.agents_config.agent_manager import agent_manager
        agent_manager.seed_builtin_agents()
    except Exception:
        pass


@app.get("/health")
async def health():
    return {"status": "ok", "service": "askbi-agno"}


@app.get("/chat/{chat_id}")
async def chat_spa_entry(chat_id: str):
    return RedirectResponse(url=f"{APP_ROOT_PATH}/", status_code=302)


@app.get("/memory")
async def memory_spa_entry():
    return RedirectResponse(url=f"{APP_ROOT_PATH}/", status_code=302)


if __name__ == "__main__":
    uvicorn.run("backend_api_agno:app", host="0.0.0.0", port=8002, reload=False)
