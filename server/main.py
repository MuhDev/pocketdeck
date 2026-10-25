from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from server.routers.api import router as api_router
from server.config import settings

app = FastAPI(title="PocketDeck API")

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
    from server.setup_helper import print_connection_card
    print_connection_card(settings.server.port)
    try:
        uvicorn.run("server.main:app", host=settings.server.host, port=settings.server.port, reload=False)
    except OSError as e:
        if getattr(e, "winerror", None) == 10048 or "10048" in str(e):
            print(f"\n[!] Port {settings.server.port} is already in use!")
            print("    PocketDeck is already running on this PC.")
            print(f"    Open your browser and go to: http://localhost:{settings.server.port}\n")
        else:
            raise
