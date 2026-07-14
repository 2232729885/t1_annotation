# T1 Annotation Service

课题四 T1 算法接口的 Python 实现，基于 FastAPI + 通义千问（DashScope OpenAI 兼容模式）。

对应规约文档（课题四后端仓库 `docs/` 目录）：
- `T1标注接口规约.md` —— 接口调用方式
- `T1_annotation_v0.6.json` / `T1_annotation_v0.6_README.md` —— 完整字段字典

## 三个接口

| 接口 | 用途 |
|---|---|
| `POST /annotate` | 内容标注：AIGC检测 + 6个高价值主观维度 + 5个基础客观维度 |
| `POST /annotate_account` | 账号类别判断 |
| `POST /annotate_event_heat` | 事件热度判断 |

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入真实的 DASHSCOPE_API_KEY

uvicorn app.main:app --reload --port 8001
```

启动后访问 `http://localhost:8001/docs` 看自动生成的接口文档（FastAPI/Swagger）。

## 目录结构

```
app/
  main.py                  FastAPI入口，三个路由
  config.py                环境变量配置
  llm_client.py             通义千问调用封装（JSON模式 + 重试 + 兜底解析）
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
  test_schemas.py            schema 冒烟测试（不需要真实API Key）
```

## 设计说明

- **JSON 字段用 camelCase**，跟课题四后端 Java 版 DTO（Jackson 序列化）保持一致；Python 代码内部用 snake_case，通过 `CamelModel`（`app/schemas/common.py`）的 alias 机制自动转换，两边都能正常访问。
- **大模型调用失败时会走 fallback**（`_build_fallback_response`），返回结构合法但 `qualityControl.needHumanReview=true` 的兜底响应，不会让调用方拿到一个报错或者不完整的JSON，具体每个接口的 fallback 逻辑在各自的 `services/*.py` 里。
- **`input_reference`（`/annotate`）/`account_reference`（`/annotate_account`）里的关键字段由服务端权威覆盖**，不完全依赖大模型自己回填是否正确（比如 `contentId`/`modalityCombination` 这些，服务端自己算得比大模型可靠）。
- 枚举字段（`ideologyLabel`/`stanceLabel`等）用 `str` 类型而不是 `Literal` 强校验——大模型偶尔的轻微用词偏差不应该导致整个请求直接报错，具体取值范围写在提示词和字段注释里。

## 测试

```bash
pytest
```

现有测试只覆盖 schema 解析（不需要真实API Key），没有覆盖真实大模型调用的端到端效果，接入真实Key之后建议用 `docs/` 目录下算法组拿到的真实数据样例（`T1请求体样例-真实Reddit数据.jsonl`）跑一遍人工核对效果。
