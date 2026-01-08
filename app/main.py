import os
import uuid
import base64
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse

from openai import OpenAI

from app.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.judge_schema import JudgeResult
from app.video_frames import extract_frames_from_bytes

app = FastAPI(title="Drill Judge API")

# Enkel in-memory jobstore (MVP)
JOBS: Dict[str, Dict[str, Any]] = {}

def to_data_url_jpeg(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

@app.get("/")
def root():
    return {"status": "ok", "message": "Drill Judge API running"}

@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    # Minimal uppladdningssida (valfri men skön)
    return """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Drill Judge</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 40px; max-width: 720px; }
          .card { padding: 16px; border: 1px solid #ddd; border-radius: 12px; }
          button { padding: 10px 14px; border-radius: 10px; border: 1px solid #333; background: #111; color: #fff; cursor: pointer; }
          pre { background: #f6f6f6; padding: 12px; border-radius: 10px; overflow:auto; }
        </style>
      </head>
      <body>
        <h1>Drill Judge</h1>
        <div class="card">
          <p>Ladda upp en video (mp4/mov). Du får ett job-id direkt, och resultatet visas när det är klart.</p>
          <input type="file" id="file" accept="video/*" />
          <button onclick="start()">Bedöm</button>
          <p id="status"></p>
          <pre id="out"></pre>
        </div>

        <script>
          async function start() {
            const f = document.getElementById('file').files[0];
            if (!f) { alert('Välj en video'); return; }

            document.getElementById('status').textContent = 'Startar jobb...';
            document.getElementById('out').textContent = '';

            const fd = new FormData();
            fd.append('video', f);

            const r = await fetch('/judge', { method: 'POST', body: fd });
            const j = await r.json();
            if (!r.ok) {
              document.getElementById('status').textContent = 'Fel: ' + (j.error || r.status);
              document.getElementById('out').textContent = JSON.stringify(j, null, 2);
              return;
            }

            const jobId = j.job_id;
            document.getElementById('status').textContent = 'Jobb skapat: ' + jobId + ' (bearbetar...)';

            // Poll resultat
            for (let i=0; i<120; i++) { // ~120 sek
              await new Promise(res => setTimeout(res, 1000));
              const rr = await fetch('/result/' + jobId);
              const jj = await rr.json();

              if (jj.status === 'done') {
                document.getElementById('status').textContent = 'Klart!';
                document.getElementById('out').textContent = JSON.stringify(jj.result, null, 2);
                return;
              }
              if (jj.status === 'error') {
                document.getElementById('status').textContent = 'Fel i jobb';
                document.getElementById('out').textContent = JSON.stringify(jj, null, 2);
                return;
              }
              document.getElementById('status').textContent = 'Bearbetar... (' + jj.status + ')';
            }

            document.getElementById('status').textContent = 'Tar längre tid än väntat. Testa igen eller kolla /result/' + jobId;
          }
        </script>
      </body>
    </html>
    """

@app.get("/result/{job_id}")
def get_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job_id finns inte"})
    # returnera status + ev resultat
    out = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "done":
        out["result"] = job["result"]
    if job["status"] == "error":
        out["error"] = job.get("error", "okänt fel")
    return JSONResponse(out)

@app.post("/judge")
async def judge_video(video: UploadFile = File(...)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse(status_code=500, content={"error": "OPENAI_API_KEY saknas"})

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    fps = int(os.getenv("FRAME_FPS", "1"))
    max_frames = int(os.getenv("MAX_FRAMES", "12"))
    max_seconds = int(os.getenv("MAX_SECONDS", "12"))

    # Skapa jobb
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "queued"}

    # Läs videon nu (snabbt) och starta background-task
    video_bytes = await video.read()

    async def run_job():
        try:
            JOBS[job_id]["status"] = "processing"

            # 1) Extrahera frames
            frame_paths = extract_frames_from_bytes(
                video_bytes,
                fps=fps,
                max_frames=max_frames,
                max_seconds=max_seconds,
            )
            if not frame_paths:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = "Kunde inte extrahera frames."
                return

            # 2) Bygg innehåll: text + bilder
            content = [{"type": "input_text", "text": USER_PROMPT}]
            for p in frame_paths:
                content.append({"type": "input_image", "image_url": to_data_url_jpeg(p)})

            # 3) OpenAI-anrop
            client = OpenAI(api_key=api_key)
            resp = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                text_format=JudgeResult,
            )

            result = resp.output_parsed.model_dump()

            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["result"] = result

        except Exception as e:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = str(e)

    # Starta bakgrundsjobb (utan att blocka requesten)
    import asyncio
    asyncio.create_task(run_job())

    return JSONResponse({"job_id": job_id, "status": "queued"})
