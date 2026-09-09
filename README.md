# fastapishorturl 部署文档

FastAPI 短链服务部署指南。适用于本地开发、单机生产部署。

---

## 1. 环境要求

| 依赖     | 版本                                    |
| -------- | --------------------------------------- |
| Python   | ≥ 3.12                                  |
| 包管理器 | uv（推荐）或 pip                        |
| 数据库   | SQLite（默认，零配置）/ 可选 PostgreSQL |

---

## 2. 获取代码与安装依赖

```bash
# 1. 克隆或拷贝项目到服务器
git clone <repo_url> && cd fastapiShortURL

# 2. 创建虚拟环境并安装依赖（推荐 uv）
uv sync

# 或用 pip
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS
pip install -e .
```

---

## 3. 配置环境变量

项目通过 `.env` 读取配置。**私密信息不写入代码**，请从模板创建并填写：

```bash
cp .env_example .env
```

`.env_example` 内容及说明：

```
APP_NAME=fastapishorturl        # 应用名
APP_VERSION=1.0.0               # 应用版本
ASYNC_DATABASE_URL=sqlite+aiosqlite:///short.db   # 数据库连接串
JWT_SECRET_KEY=...              # JWT 签名密钥（必填，须更换为随机强密钥）
JWT_ALGORITHM=HS256             # JWT 签名算法
```

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> ⚠️ **安全须知**
>
> - `.env` 已被 `.gitignore` 忽略，**切勿提交到仓库**；仓库只提交 `.env_example`。
> - 生产环境务必更换 `JWT_SECRET_KEY`，否则任何拿到源码的人都能伪造登录令牌。
> - 若改用 PostgreSQL，连接串示例：
>   `postgresql+asyncpg://user:pass@host:5432/shorturl`（需另装 `asyncpg`）。

---

## 4. 启动应用

**开发模式（自动重载）**：

```bash
cd src
uv run uvicorn fastapishorturl.main:app --host 0.0.0.0 --port 8000 --reload
```

**生产模式（多进程）**：

```bash
cd src
uv run uvicorn fastapishorturl.main:app --host 0.0.0.0 --port 8000 --workers 4
```

> 说明：本项目包入口是 `fastapishorturl`（见 `pyproject.toml`），`main.py` 中的
> `app = FastAPI(...)` 即为 ASGI 应用对象，Uvicorn 从 `src` 目录以
> `fastapishorturl.main:app` 启动。数据库表会在应用启动（startup 事件）时自动创建。

启动后：

- 服务地址：`http://<host>:8000`
- 交互式 API 文档：`http://<host>:8000/docs`
- 健康跳转测试：`http://<host>:8000/`（短链跳转）

---

## 4.x 短链的生成与使用

### 目录模板库 `short.db`

> 本项目随源码附带一个**模板数据库** `src/fastapishorturl/short.db`，
> 已内置一张可登录的演示账号与几条测试短链，克隆后可直接体验。

| 资源     | 内容                                                                              |
| -------- | --------------------------------------------------------------------------------- |
| 演示账号 | `admin`（密码 `admin123456`）                                                     |
| 测试短链 | `RKCRtYD` → python.org、`fVDwiI8` → fastapi.tiangolo.com、`8lsqmuz` → example.com |

> ⚠️ 模板库自带演示密码，仅供本地体验。部署生产环境请**重新注册用户**并忽略/重建该库。

### 1. 创建账号（注册）

```
POST /api/v1/user/register
Body(JSON): {"username": "admin", "password": "admin123456"}
```

### 2. 生成短链

当前**没有创建短链的 HTTP 接口**，需要通过数据库写入一条 `short_url` 记录
（`short_tag` 可用于 `utils` 的随机生成逻辑，也可自定义空格别名）。示例 SQL：

```sql
INSERT INTO short_url (short_tag, short_url, long_url, visits_count, created_by, msg_context)
VALUES ('abc123', 'http://127.0.0.1:8000/abc123', 'https://www.python.org', 0, 'admin', '测试');
```

写库后即可访问短链：`http://127.0.0.1:8000/abc123`。

### 3. 使用短链（访问跳转）

```
GET /{short_tag}
```

例如访问 `http://127.0.0.1:8000/RKCRtYD`，服务会：

1. 用 `short_tag` 查询 `short_url` 表；
2. 命中则访问次数 `visits_count + 1`，并 302 跳转到对应的 `long_url`；
3. 未命中返回"没有对应短链信息记录"。

命令行验证：

```bash
curl -I http://127.0.0.1:8000/RKCRtYD
```

---

## 5. 生产部署建议

### 5.1 进程守护（Windows 可用 NSSM / RunAsService）

后台常驻运行 Uvicorn，或用进程管理工具托管：

```bash
# Linux + systemd 示例：/etc/systemd/system/fastapishorturl.service
[Unit]
Description=FastAPI ShortURL
After=network.target

[Service]
WorkingDirectory=/opt/fastapiShortURL/src
ExecStart=/opt/fastapiShortURL/.venv/bin/uvicorn fastapishorturl.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fastapishorturl
```

### 5.2 反向代理 + HTTPS（Nginx 示例）

```nginx
server {
    listen 80;
    server_name your.domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your.domain.com;

    ssl_certificate     /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5.3 数据与备份

- 默认数据库为 `short.db`（SQLite 单文件），位于启动时的工作目录（`src/`）。
- 备份：直接拷贝 `short.db` 即可；迁移到 PostgreSQL 则用数据库自身的备份机制。
- 建议将数据库文件存放在独立目录并用脚本定期备份。

### 5.4 上线检查清单

- [ ] 已 `cp .env_example .env` 并更换 `JWT_SECRET_KEY`
- [ ] 确认 `.env` 未被 git 追踪
- [ ] `uv sync` 依赖安装成功，`import` 无误
- [ ] `/docs` 可访问，注册/登录/短链跳转流程正常
- [ ] 生产环境关闭 `--reload`，开启 `--workers`

---

## 6. 常见问题（FAQ）

- **启动报错 `JWT_SECRET_KEY` 缺失**：说明 `.env` 未创建或该变量未设置，`cp .env_example .env` 后填写。
- **表如何创建**：应用 startup 事件自动 `create_all`，无需手动建表。
- **端口被占用**：改用其他 `--port`，并同步修改反向代理目标。
- **短链跳转不生效**：确认已往 `short_url` 表写入 `short_tag` 数据（暂无创建短链的 HTTP 接口，需先落库）。
