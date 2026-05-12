<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/15d643b5-564b-4fee-91af-4f0dc28c4433

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`


## Backend 启动

后端在 `server/` 目录下，快速启动：

```bash
python -m server.app
```

更完整的后端启动说明见：`server/README.md`。


本地文件调试可直接运行：`python debug_route_matrix.py`（读取 `config.json`）。


### 前端启动常见错误

若执行 `npm run dev` 出现：`Cannot find package 'vite'`，说明前端依赖未正确安装。

请在仓库根目录执行：

```bash
npm install
```

若仍报错，再执行：

```bash
rm -rf node_modules package-lock.json
npm install
```
