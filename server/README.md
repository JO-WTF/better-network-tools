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

直接编辑 `server/debug_route_matrix.py` 末尾 `if __name__ == "__main__":` 的本地参数，然后运行：

```bash
python -m server.debug_route_matrix
```

说明：
- 仍保留 `config.json` 读取设计，需在 `CONFIG_FILE` 指向的文件中提供：`appId`、`credential`、`tokenUrl`、`routeUrl`、`geocodeUrl`。
- `OUTPUT_FILE` 为空时，自动输出为与输入同目录的 `calculated_<输入文件名>`。
- 输出文件会追加 `导航距离(km)`、`导航时间(min)`，失败时附带错误列。
