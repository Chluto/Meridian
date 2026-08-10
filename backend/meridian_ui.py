"""
Meridian 轻量中文研究界面（FastAPI）

独立服务：在 meridian 目录执行
    python -m backend.meridian_ui

提供：
    GET  /            中文任务提交表单
    POST /research    执行单 Agent 深度研究（report_type=meridian_report），返回中文报告

说明：多智能体深度研究路径（LangGraph）请通过 multi_agents.main 或后端 WebSocket 通道调用。
"""
import asyncio

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from gpt_researcher import GPTResearcher

app = FastAPI(title="Meridian 中文行业研究")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meridian · 中文行业研究</title>
<style>
:root{--ink:#22303f;--muted:#6b7a8c;--accent:#2c5282;--rule:#e3dfd6;--bg:#faf8f4;}
body{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:var(--bg);color:var(--ink);margin:0;line-height:1.7;}
.wrap{max-width:820px;margin:0 auto;padding:48px 24px;}
h1{font-size:26px;border-bottom:2px solid var(--accent);padding-bottom:10px;}
h1 small{font-size:14px;color:var(--muted);font-weight:400;}
label{display:block;margin:18px 0 6px;font-weight:600;}
input[type=text]{width:100%;padding:10px 12px;border:1px solid var(--rule);border-radius:4px;font-size:15px;box-sizing:border-box;}
button{margin-top:22px;padding:10px 32px;background:var(--accent);color:#fff;border:0;border-radius:4px;font-size:15px;cursor:pointer;}
button:disabled{opacity:.6;}
pre{background:#fff;border:1px solid var(--rule);border-radius:4px;padding:16px;white-space:pre-wrap;word-break:break-all;max-height:70vh;overflow-y:auto;font-size:13px;}
#status{color:var(--muted);font-size:13px;margin-top:10px;}
</style>
</head>
<body>
<div class="wrap">
<h1>Meridian<small> · 中文行业研究报告</small></h1>
<form id="f" action="/research" method="post">
<label for="query">研究主题</label>
<input type="text" id="query" name="query" required placeholder="例：低空经济产业链发展现状与投资机会" />
<label for="domains">限定行业域名（可选，逗号分隔）</label>
<input type="text" id="domains" name="domains" placeholder="例：caac.gov.cn,miit.gov.cn" />
<button type="submit" id="btn">开始研究</button>
</form>
<div id="status"></div>
<div id="result"></div>
</div>
<script>
const form=document.getElementById('f'),btn=document.getElementById('btn'),st=document.getElementById('status'),out=document.getElementById('result');
form.addEventListener('submit',async e=>{
  e.preventDefault();btn.disabled=true;st.textContent='研究中，请稍候（深度研究约需数分钟）...';out.textContent='';
  const fd=new FormData(form);
  const resp=await fetch('/research',{method:'POST',body:fd});
  const data=await resp.json();
  btn.disabled=false;
  if(data.error){st.textContent='错误：'+data.error;return;}
  st.textContent='完成，耗时 '+data.elapsed+' 秒';
  out.innerHTML='<h3>研究报告</h3><pre>'+data.report.replace(/</g,'&lt;')+'</pre>';
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return PAGE


@app.post("/research")
async def research(query: str = Form(...), domains: str = Form("")):
    import time
    start = time.time()
    try:
        query_domains = [d.strip() for d in domains.split(",") if d.strip()] or None
        researcher = GPTResearcher(
            query=query,
            report_type="meridian_report",
            query_domains=query_domains,
        )
        await researcher.conduct_research()
        report = await researcher.write_report()
        return {"report": report, "elapsed": round(time.time() - start, 1)}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "elapsed": round(time.time() - start, 1)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.meridian_ui:app", host="0.0.0.0", port=8010, reload=False)
