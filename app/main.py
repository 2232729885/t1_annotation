"""
T1 自动标注服务 - FastAPI 入口。

三个接口：
  POST /annotate              内容标注
  POST /annotate_account      账号类别判断
  POST /annotate_event_heat   事件热度判断

对应 docs/T1标注接口规约.md（课题四后端仓库）。
"""
import logging

from fastapi import FastAPI

from app.config import get_settings
from app.schemas.annotate import AnnotateRequest, AnnotateResponse
from app.schemas.annotate_account import AnnotateAccountRequest, AnnotateAccountResponse
from app.schemas.annotate_event_heat import AnnotateEventHeatRequest, AnnotateEventHeatResponse
from app.services import account_service, annotate_service, event_heat_service

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="T1 Annotation Service",
    description="内容标注 / 账号类别判断 / 事件热度判断，课题四 T1 算法接口实现",
    version="0.6.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/annotate", response_model=AnnotateResponse)
def annotate(request: AnnotateRequest) -> AnnotateResponse:
    return annotate_service.annotate(request)


@app.post("/annotate_account", response_model=AnnotateAccountResponse)
def annotate_account(request: AnnotateAccountRequest) -> AnnotateAccountResponse:
    return account_service.annotate_account(request)


@app.post("/annotate_event_heat", response_model=AnnotateEventHeatResponse)
def annotate_event_heat(request: AnnotateEventHeatRequest) -> AnnotateEventHeatResponse:
    return event_heat_service.annotate_event_heat(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.service_port, reload=True)
