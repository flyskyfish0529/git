from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import backend
import MBTI_back
import get_schools_agents
import password

origins = MBTI_back.origins
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],              # 允许所有方法
    allow_headers=["*"],              # 允许所有头
)
@app.post('/api/orange/questions')
async def create_questions():
    return await MBTI_back.create_questions()  # 添加 await

@app.post('/api/orange/result')
async def choice(choice: MBTI_back.Choice):
    return await MBTI_back.choice(choice)  # 添加 await

@app.post('/api/orange/clear')
async def clear():
    return await MBTI_back.clear()  # 添加 await

@app.post('/api/orange/seek')
async def seek(mbti_type: MBTI_back.Type):
    return await MBTI_back.seek(mbti_type)  # 添加 await

@app.post("/api/orange/student")
async def student(input: get_schools_agents.InputMessage):
    return await get_schools_agents.student(input)  # 添加 await

@app.post("/api/orange/smart_recommend")
async def smart_recommend():
    result = await get_schools_agents.smart_recommend()
    return JSONResponse(content=result, status_code=200)

@app.post("/process")
async def process(request: Request):
    return await backend.process(request)

@app.post("/get_dynamic_kg")
async def get_dynamic_kg(request: Request):
    return await backend.get_dynamic_kg(request)

@app.post("/api/orange/register")
async def register(thisuser:password.user):
    return await password.reg(thisuser)

@app.post("/api/orange/loader")
async def load(thisuser:password.user):
    return await password.judge(thisuser)

@app.post("/api/orange/reset")
async def set(thisuser:password.user):
    return await password.change(thisuser)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)