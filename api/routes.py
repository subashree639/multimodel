from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)


def create_api_router():
    return APIRouter()
