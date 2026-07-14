"""
T1 自动标注服务 - FastAPI 入口。

三个接口：
  POST /annotate_content       内容标注
  POST /annotate_account_type  账号类别判断
  POST /annotate_event_heat    事件热度判断

对应 docs/T1标注接口规约.md（课题四后端仓库）。
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.annotate import AnnotateRequest, AnnotateResponse
from app.schemas.annotate_account import AnnotateAccountRequest, AnnotateAccountResponse
from app.schemas.annotate_event_heat import AnnotateEventHeatRequest, AnnotateEventHeatResponse
from app.services import account_service, annotate_service, event_heat_service

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="T1 Annotation Service",
    description="内容标注 / 账号类别判断 / 事件热度判断，课题四 T1 算法接口实现",
    version="0.6.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    FastAPI 默认422只把detail塞进响应体返回给调用方，自己的容器日志里不会打印具体原因。
    这里补一份服务端自己的日志，以后422发生时直接在这个服务的容器日志里就能看到详细原因，
    不用再靠调用方（Java后端）那边的异常堆栈去猜（后端那边如果这个调用被try-catch包住
    只记了warn甚至没记日志，两边都会看不到具体是哪个字段的问题）。
    """
    body = await request.body()
    logger.error(
        "422 Unprocessable Entity on %s %s\nvalidation errors: %s\nraw request body: %s",
        request.method, request.url.path, exc.errors(), body.decode("utf-8", errors="replace")[:5000],
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/annotate_content", response_model=AnnotateResponse)
def annotate(request: AnnotateRequest) -> AnnotateResponse:
    return annotate_service.annotate(request)


@app.post("/annotate_account_type", response_model=AnnotateAccountResponse)
def annotate_account(request: AnnotateAccountRequest) -> AnnotateAccountResponse:
    return account_service.annotate_account(request)


@app.post("/annotate_event_heat", response_model=AnnotateEventHeatResponse)
def annotate_event_heat(request: AnnotateEventHeatRequest) -> AnnotateEventHeatResponse:
    return event_heat_service.annotate_event_heat(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.service_port, reload=True)
