from fastapi import APIRouter

from core.config import get_settings, Settings

router = APIRouter()
settings: Settings = get_settings()
