from fastapi import FastAPI, APIRouter, Security
from src.security.authentication import verify_api_key

router = APIRouter(dependencies=[Security(verify_api_key)])
print("Router created successfully")
