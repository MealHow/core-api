from fastapi import APIRouter

from src.core.config import Settings, get_settings

router = APIRouter()
settings: Settings = get_settings()
