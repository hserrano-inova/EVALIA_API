from fastapi import APIRouter
from .user import router as userd
from .licitaciones import router as licita
from .ofertas import router as ofrt
from .evaluaciones import router as evalua

router = APIRouter()
router.include_router(userd)
router.include_router(licita)
router.include_router(ofrt)
router.include_router(evalua)