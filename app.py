import time
from uuid import UUID

from beanie import init_beanie
from fastapi import APIRouter, Depends, HTTPException
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.config.app_config import get_settings
from src.controllers import user_controller, bot_controller, admin_controller, guest_controller
from src.controllers.auth_controller import auth_router
from src.controllers.bot_controller import bot_router
from src.controllers.knowledge_controller import knowledge_router
from src.controllers.query_controller import query_router
from src.db_vector.chat_model import generate_stream
from src.dtos.schema_in.query import GeneratePayload
from src.models.all_models import Bot, Query, Knowledge, Chat, File
from src.models.all_models import User
from src.security import get_current_user
from src.services.chat_service import ChatService
from src.services.query_service import QueryService
from src.utils.minio_util import create_bucket_if_not_exist

# Initialize FastAPI application and settings
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

import json


@app.websocket("/ws/bots/{bot_id}/chats/{chat_id}/generate_stream")
async def websocket_generate_stream2(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            print(f"Received data: {data}")
            payload1 = json.loads(data)
            query_id = payload1['query_id']
            query = await Query.find_one(Query.query_id == query_id)
            if not query:
                raise HTTPException(status_code=404, detail="Query not found")
            payload = GeneratePayload(
                query_id=query_id,
                query=payload1['query'],
                context=payload1['context'],
                conversation=payload1['conversation']
            )
            full_text = ""
            start_time = time.time()
            async for chunk in generate_stream(payload.query, payload.context, payload.conversation):
                print(chunk)
                if chunk.choices[0].delta.content is not None:
                    full_text += chunk.choices[0].delta.content
                    await websocket.send_json({
                        "message": chunk.choices[0].delta.content,
                        "finish_reason": None,
                        "full_text": full_text
                    })
                else:
                    query.answer.completion_token = chunk.usage.completion_tokens
                    query.answer.prompt_token = chunk.usage.prompt_tokens
                    query.answer.total_time = time.time() - start_time
                    query.answer.content = full_text
                    await query.save()
            await websocket.send_json({
                "message": "Stream completed successfully",
                "finish_reason": "stop",
                "full_text": full_text
            })
        except WebSocketDisconnect:
            print("WebSocket disconnected")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            await websocket.send_json({
                "message": str(e),
                "finish_reason": "error",
                "full_text": str(e)
            })
            break

    print("WebSocket connection closed")


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://localhost", "http://localhost:8068", ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()
api_router.include_router(auth_router, prefix='/auth', tags=["auth"])
api_router.include_router(user_controller.user_router, prefix='/users', tags=["users"])
api_router.include_router(admin_controller.admin_user_router, prefix='/admins/users', tags=["admins users"])
api_router.include_router(bot_controller.chat_bot_router, prefix='/chats-bot', tags=["chats bots"])
api_router.include_router(bot_controller.knowledge_bot_router, prefix='/knowledges-bot',
                          tags=["knowledges bots"])
api_router.include_router(admin_controller.admin_bot_router, prefix='/admins/bots', tags=["admins bots"])
api_router.include_router(query_router, prefix='/queries', tags=["chat queries"])
api_router.include_router(bot_router, prefix='/bots', tags=["users bots"])
api_router.include_router(knowledge_router, prefix='/knowledges', tags=["knowledges"])
app.include_router(guest_controller.guest_router, prefix='/guest', tags=["guest"])
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": (
                f"Failed method {request.method} at URL {request.url}."
                f" Exception message is {exc!r}."
            )
        },
    )


async def startup_event():
    db_client = AsyncIOMotorClient(settings.MONGO_CONNECTION_STRING).kltn
    await init_beanie(
        database=db_client,
        document_models=[Knowledge, Bot, Query, User, Chat, File]
    )
    create_bucket_if_not_exist()


async def log_request_middleware(request: Request, call_next):
    request_start_time = time.monotonic()
    response = await call_next(request)
    request_duration = time.monotonic() - request_start_time
    log_data = {
        "method": request.method,
        "path": request.url.path,
        "duration": request_duration
    }
    print(log_data)
    return response


app.middleware("http")(log_request_middleware)

app.add_event_handler("startup", startup_event)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="localhost", port=settings.BACKEND_PORT, reload=True)
