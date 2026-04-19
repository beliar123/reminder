from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from reminder.api.routers import auth, events, history, users

app = FastAPI(title="Reminder API", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(history.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
