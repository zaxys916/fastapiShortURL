# 项目未引用模块清理操作文档

- 日期：2026-09-09
- 项目：fastapishorturl（FastAPI 短链服务）
- 仓库分支：master（首次提交）
- 操作类型：未引用模块清理（源码层 + 依赖层）

---

## 1. 清理前模块清单

`src/fastapishorturl/` 下全部源码模块及其引用状态：

| 模块 | 引用方 | 是否被引用 |
|------|--------|:---:|
| `main.py` | —（应用入口） | ✅ 引用 |
| `api/user.py` | `main.py` | ✅ |
| `api/short.py` | `main.py` | ✅ |
| `services/user.py` | `api/user.py` | ✅ |
| `services/short.py` | `api/short.py` | ✅ |
| `models/model.py` | `main.py`、`services/user.py`、`services/short.py` | ✅ |
| `db/database.py` | `dependencies`、`models`、`main` | ✅ |
| `config/config.py` | `db/database.py` | ✅ |
| `dependencies/__init__.py` | `api/user.py`、`api/short.py` | ✅ |
| `utils/passlib_hepler.py` | `api/user.py` | ✅ |
| `utils/auth_helper.py` | `api/user.py` | ✅ |
| `utils/random_helper.py` | **无** | ❌ 未引用 |
| `schemas/__init__.py`（`SingleShortUrlCreate`） | **无** | ❌ 未引用 |

依赖包（`pyproject.toml`）：

| 依赖 | 使用点 | 是否被引用 |
|------|--------|:---:|
| `fastapi[standard]` | 框架 | ✅ |
| `sqlalchemy` | ORM | ✅ |
| `pydantic-settings` | `config/config.py` | ✅ |
| `python-jose[cryptography]` | `utils/auth_helper.py` | ✅ |
| `aiosqlite` | `db/database.py`（异步驱动） | ✅ |
| `bcrypt` | `utils/passlib_hepler.py` | ✅ |
| `passlib` | **无**（`passlib_hepler.py` 已改用 `bcrypt`） | ❌ 未引用 |

---

## 2. 清理后模块清单

`src/fastapishorturl/` 剩余源码模块：
`common init`：`__init__.py`、`api/__init__.py`、`config/__init__.py`、`db/__init__.py`、`models/__init__.py`、`services/__init__.py`、`utils/__init__.py`
逻辑模块：`main.py`、`api/user.py`、`api/short.py`、`services/user.py`、`services/short.py`、`models/model.py`、`db/database.py`、`config/config.py`、`dependencies/__init__.py`、`utils/passlib_hepler.py`、`utils/auth_helper.py`

已删除：
- `utils/random_helper.py`
- `schemas/`（含 `__init__.py` 与 `SingleShortUrlCreate`）

已移除依赖：
- `passlib`（同步更新 `pyproject.toml` 与 `uv.lock`）

额外修正：
- `.gitignore` 增加 `*.db` / `*.sqlite` / `*.sqlite3`，避免运行时数据库入库。

---

## 3. 清理步骤说明

1. **扫描识别**：对 `src/fastapishorturl/` 全部 `.py` 文件做全量 grep，建立引用矩阵，识别出无任何引用的模块。
2. **二次确认**：检查各 `__init__.py` 是否存在聚合导出、是否被 `main.py` 等入口间接引用，确认 `random_helper`、`schemas` 无实际引用关系，`passlib` 无任何 `import`（源码中唯一 `passlib` 匹配为其自研模块名 `passlib_hepler.py`）。
3. **删除**：删除 `utils/random_helper.py`、`schemas/__init__.py`，并移除清空后的 `schemas` 空目录。
4. **依赖同步**：从 `pyproject.toml` 移除 `passlib`，执行 `uv lock` 重新生成 `uv.lock`（确认 `passlib` 已不在 lock 中）。
5. **回归验证**：`import fastapishorturl.main` 成功，应用可正常加载。
6. **文档与提交**：生成本文档，提交本次变更。

---

## 4. 风险评估

| 风险 | 等级 | 说明与缓解 |
|------|:---:|------|
| 误删未来将要使用的工具函数 | 低 | `generate_short_url` 目前无任何代码调用，若后续实现“创建短链”接口可直接从 git 历史恢复。 |
| `passlib` 被隐式依赖 | 低 | 跨全库 grep 无任何 import，`passlib_hepler.py` 已改用标准库 `bcrypt`。若依赖移除导致环境不一致，可回滚（见第 5 节）。 |
| 删除后导入失败 | 低 | 已实测 `import fastapishorturl.main` 通过；`schemas`/`random_helper` 不在任何引用链上。 |
| 误提交运行时数据库 | 低 | 已在 `.gitignore` 排除 `*.db`。 |

整体风险评估：**低**，不影响现有注册/登录/跳转等已启用功能。

---

## 5. 回滚方案

> 因当前仓库为首次提交（无历史），回滚采用「备份恢复」为主。

**方式 A：git 历史恢复（推荐）**
清理内容已提交。如需恢复被删文件：
```bash
git log --oneline --diff-filter=D   # 查看删除记录
git checkout <commit>^ -- src/fastapishorturl/utils/random_helper.py
git checkout <commit>^ -- src/fastapishorturl/schemas/
```
说明：将某次提交前一状态对应的文件还原到工作区（`<commit>^` 为该提交的父提交）。若首章提交前删除项已存在，则直接从本提交文件内容手工重建。

**方式 B：恢复 `passlib` 依赖**
```bash
# 在 pyproject.toml dependencies 中重新加入
"passlib>=1.7.4"
# 然后
uv sync          # 或 uv add passlib
# 若继续使用 passlib，需将 utils/passlib_hepler.py 改回基于 passlib 的实现
```

**方式 C：数据库文件**
`short.db` 为运行数据，已 gitignore；如需保留原数据请勿删除本地 `short.db`，它不受本次清理影响。

---

## 6. 提交信息

首次提交，信息建议：
`chore: 清理未引用模块（schemas/random_helper）并移除无用依赖 passlib`