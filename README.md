# AWK-report-gnyx

安为康功能医学报告生成平台，当前优先实现 P02「肠道功能综合评估健康管理报告」端到端流程。

## 开发端口

- 前端 Vite / Electron Renderer：`5188`
- FastAPI 主服务：`8111`
- 禁止占用：`5173`、`8000-8010`

## 本地启动

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -r services\\api\\requirements.txt
npm install
npm run dev:api
npm run dev:web
```

访问前端：http://127.0.0.1:5188

访问后端健康检查：http://127.0.0.1:8111/health

