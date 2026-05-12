# Backend Server 启动说明

## 1) 环境准备

- Python 3.10+
- 建议在项目根目录创建虚拟环境

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 启动服务

在仓库根目录执行（推荐）：

```bash
python -m server.app
```

或进入 `server/` 目录后执行：

```bash
python app.py
```

服务默认监听 `0.0.0.0:8765`（可在配置中调整）。

## 3) 前端联调

前端通过 WebSocket 与后端通信，启动前端后将连接到：

- `ws://localhost:8765`

若你改了端口，请同步更新前端配置中的 WebSocket 地址。

## 4) 常见问题

- **ImportError / ModuleNotFoundError**：优先使用 `python -m server.app` 从仓库根目录启动。
- **端口占用**：修改后端监听端口后重启服务，并同步前端 WebSocket 地址。
- **依赖安装失败**：确认 Python 版本与 `pip install -r server/requirements.txt` 的执行环境一致。


## 5) 本地调试 custom 距离矩阵（CSV）

可直接用 custom 接口计算某个 CSV 文件中的起终点路线：

```bash
python -m server.debug_route_matrix   --input ./data/routes.csv   --output ./data/routes_with_result.csv   --start-col 起点   --end-col 终点   --input-mode coordinate   --app-id <your_app_id>   --credential <your_credential>   --token-url <your_token_url>   --route-url <your_route_url>
```

说明：
- `--input-mode coordinate` 时，起终点列为坐标字符串（兼容 `lng,lat` / `lat,lng`）。
- 输出文件会追加 `导航距离(km)`、`导航时间(min)`，失败时附带错误列。
