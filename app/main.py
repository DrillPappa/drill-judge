import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

from openai import OpenAI

from app.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.judge_schema import JudgeResult

app = FastAPI(title="Drill Judge API")

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Drill Judge API running"
    }

@app.post("/judge")
async def judge_video(video: UploadFile = File(...)):
    """
    Tar emot en drill-video och returnerar en bedömning
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse(
            status_code=500,
            content={"error": "OPENAI_API_KEY saknas"}
        )

    # Läs in videon (vi skickar den vidare som binär referens)
    video_bytes = await video.read()

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": USER_PROMPT
                        },
                        {
                            "type": "input_file",
                            "file": {
                                "filename": video.filename,
                                "bytes": video_bytes
                            }
                        }
                    ]
                }
            ],
            text_format=JudgeResult
        )

        result = response.output_parsed
        return JSONResponse(result.model_dump())

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

