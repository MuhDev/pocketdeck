from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from server.routers.api import router as api_router
from server.config import settings

app = FastAPI(title="PC Remote Control API")

# Allow CORS for development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Serve the frontend web directory
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this file from the project root or adjust the python path
    uvicorn.run("server.main:app", host=settings.server.host, port=settings.server.port, reload=True)
