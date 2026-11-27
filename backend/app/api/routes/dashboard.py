from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.doctor import Doctor
from app.schemas.dashboard import DashboardResponse
from app.security.dependencies import get_current_doctor
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_dashboard_data(db, current_doctor.id)
