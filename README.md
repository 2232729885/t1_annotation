# T1 Annotation Service

课题四 T1 算法接口的 Python 实现，基于 FastAPI，大模型走内网 vLLM 部署的 Qwen3（OpenAI 兼容接口，跟课题四后端连的是同一个模型服务）。

对应规约文档（课题四后端仓库 `docs/` 目录）：
- `T1标注接口规约.md` —— 接口调用方式
- `T1_annotation_v0.6.json` / `T1_annotation_v0.6_README.md` —— 完整字段字典

## 三个接口

| 接口 | 用途 |
|---|---|
| `POST /annotate` | 内容标注：AIGC检测 + 6个高价值主观维度 + 5个基础客观维度 |
| `POST /annotate_account` | 账号类别判断 |
| `POST /annotate_event_heat` | 事件热度判断 |

## 快速开始（本地）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env：填入内网 vLLM 的 LLM_BASE_URL（形如 http://<内网地址>:8000/v1）和 LLM_MODEL

uvicorn app.main:app --reload --port 8001
```

启动后访问 `http://localhost:8001/docs` 看自动生成的接口文档（FastAPI/Swagger）。

## 用 Docker 部署

```bash
docker build -t t1-annotation:latest .

# .env 参照 .env.example 先建好，填真实的 LLM_BASE_URL 等
docker run -d -p 8001:8001 --env-file .env --name t1-annotation t1-annotation:latest

# 如果 vLLM 部署在宿主机上（不是内网其他机器），容器内访问宿主机用 host.docker.internal
# （Linux 上可能需要 docker run 加 --add-host=host.docker.internal:host-gateway）
```

看日志 / 健康检查：

```bash
docker logs -f t1-annotation
curl http://localhost:8001/health
```

## 目录结构

```
app/
  main.py                  FastAPI入口，三个路由
  config.py                环境变量配置
  llm_client.py             大模型调用封装（OpenAI兼容接口，JSON模式 + 重试 + 兜底解析）
  prompts.py                三个接口的系统提示词
  schemas/
    common.py               驼峰命名基类
    annotate.py              /annotate 请求/响应
    annotate_account.py      /annotate_account 请求/响应
    annotate_event_heat.py   /annotate_event_heat 请求/响应
  services/
    annotate_service.py      /annotate 业务逻辑
    account_service.py       /annotate_account 业务逻辑
    event_heat_service.py    /annotate_event_heat 业务逻辑
tests/
  test_schemas.py            schema 冒烟测试（不需要真实连上vLLM）
Dockerfile
.dockerignore
```

## 设计说明

- **JSON 字段用 camelCase**，跟课题四后端 Java 版 DTO（Jackson 序列化）保持一致；Python 代码内部用 snake_case，通过 `CamelModel`（`app/schemas/common.py`）的 alias 机制自动转换，两边都能正常访问。
- **大模型调用失败时会走 fallback**（`_build_fallback_response`），返回结构合法但 `qualityControl.needHumanReview=true` 的兜底响应，不会让调用方拿到一个报错或者不完整的JSON，具体每个接口的 fallback 逻辑在各自的 `services/*.py` 里。
- **`input_reference`（`/annotate`）/`account_reference`（`/annotate_account`）里的关键字段由服务端权威覆盖**，不完全依赖大模型自己回填是否正确（比如 `contentId`/`modalityCombination` 这些，服务端自己算得比大模型可靠）。
- 枚举字段（`ideologyLabel`/`stanceLabel`等）用 `str` 类型而不是 `Literal` 强校验——大模型偶尔的轻微用词偏差不应该导致整个请求直接报错，具体取值范围写在提示词和字段注释里。
- **`llm_client.py` 会自动剥离 `<think>...</think>`**——Qwen3 是推理模型，vLLM 部署时如果没有关掉思考模式，返回内容前面可能带一段思考过程，这段会被自动去掉再解析JSON。
- **`LLM_USE_JSON_RESPONSE_FORMAT`**：vLLM 是否支持 `response_format={"type":"json_object"}` 取决于具体版本和启动参数，如果你们的 vLLM 部署不支持这个参数导致报错，在 `.env` 里把这个改成 `false`，代码会跳过这个参数，靠提示词 + 兜底解析（markdown围栏清理、JSON片段截取）来保证输出解析成JSON。

## 测试

```bash
pytest
```

现有测试只覆盖 schema 解析（不需要真实连上vLLM），没有覆盖真实大模型调用的端到端效果，接入真实模型之后建议用课题四后端仓库算法组拿到的真实数据样例（`T1请求体样例-真实Reddit数据.jsonl`）跑一遍人工核对效果。
