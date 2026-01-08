import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

from openai import OpenAI

from app.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.judge_schema import JudgeResult

app = FastAPI(title="Drill Judge API")

@app.get("/")
def root():
    return {"status": "ok", "message": "Drill Judge API running"}

@app.post("/judge")
async def judge_video(video: UploadFile = File(...)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse(status_code=500, content={"error": "OPENAI_API_KEY saknas"})

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    try:
        # 1) Läs videon
        video_bytes = await video.read()

        # 2) Ladda upp videon som en fil till OpenAI och få file_id
        uploaded = client.files.create(
            file=(video.filename or "video.mp4", video_bytes),
            purpose="assistants"
        )

        # 3) Kör bedömningen och referera filen via file_id
        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "input_text", "text": USER_PROMPT},
                    {"type": "input_file", "file_id": uploaded.id},
                ]},
            ],
            text_format=JudgeResult,
        )

        result = resp.output_parsed
        return JSONResponse(result.model_dump())

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
