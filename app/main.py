from fastapi import FastAPI
from router import routes

fast_app = FastAPI()

fast_app.include_router(routes.api_router)

