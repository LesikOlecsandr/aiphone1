from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Estimate
from app.schemas.device import DeviceRead
from app.schemas.estimate import EstimateResponse
from app.services.device_matcher import DeviceMatcherService
from app.services.price_calculator import PriceCalculator
from app.services.vision_service import VisionService

router = APIRouter(tags=["estimate"])


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_repair_cost(
    request: Request,
    model_name: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> EstimateResponse:
    """Принимает модель и фото повреждения, затем возвращает оценку стоимости ремонта."""

    print(
        "[REQUEST] POST /estimate "
        f"from {request.client.host if request.client else 'unknown'} "
        f"model={model_name!r} filename={photo.filename!r}"
    )

    matcher = DeviceMatcherService(db)
    calculator = PriceCalculator(db)
    vision_service = VisionService()

    device = matcher.find_best_match(model_name)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Указанная модель не найдена в поддерживаемом каталоге.",
        )

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл изображения пустой.",
        )

    try:
        vision_result = vision_service.analyze_damage(
            image_bytes=image_bytes,
            mime_type=photo.content_type or "image/jpeg",
        )
        if not vision_result.is_smartphone:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="На изображении не распознан смартфон.",
            )

        if vision_result.damage_category == "unknown":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Не удалось уверенно определить тип повреждения. Нужна фотография лучшего качества.",
            )

        calculation = calculator.calculate(vision_result, device)
        response = EstimateResponse(
            requested_model=model_name,
            matched_device=DeviceRead.model_validate(device),
            vision_result=vision_result,
            price_range=calculation.price_range,
            recommended_price=calculation.recommended_price,
            markup_factor=calculation.markup_factor,
        )
        _save_estimate_log(
            db=db,
            requested_model=model_name,
            matched_model=f"{device.brand} {device.model_name}",
            device_id=device.id,
            response=response,
            status_code=status.HTTP_200_OK,
        )
        return response
    except HTTPException as exc:
        _save_failed_estimate_log(
            db=db,
            requested_model=model_name,
            matched_model=f"{device.brand} {device.model_name}",
            device_id=device.id,
            error_message=str(exc.detail),
            status_code=exc.status_code,
        )
        raise
    except Exception as exc:
        _save_failed_estimate_log(
            db=db,
            requested_model=model_name,
            matched_model=f"{device.brand} {device.model_name}",
            device_id=device.id,
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


def _save_estimate_log(
    db: Session,
    requested_model: str,
    matched_model: str,
    device_id: int,
    response: EstimateResponse,
    status_code: int,
) -> None:
    """Сохраняет успешную оценку в таблицу аналитического журнала."""

    log = Estimate(
        requested_model_name=requested_model,
        matched_model_name=matched_model,
        device_id=device_id,
        ai_verdict=response.vision_result.technical_summary,
        damage_category=response.vision_result.damage_category,
        confidence_score=response.vision_result.confidence_score,
        min_price=response.price_range.min_price,
        max_price=response.price_range.max_price,
        currency=response.price_range.currency,
        is_smartphone=response.vision_result.is_smartphone,
        status_code=status_code,
    )
    db.add(log)
    db.commit()


def _save_failed_estimate_log(
    db: Session,
    requested_model: str,
    matched_model: str | None,
    device_id: int | None,
    error_message: str,
    status_code: int,
) -> None:
    """Сохраняет неуспешную попытку оценки для последующего анализа качества сервиса."""

    log = Estimate(
        requested_model_name=requested_model,
        matched_model_name=matched_model,
        device_id=device_id,
        ai_verdict=error_message,
        damage_category="unknown",
        confidence_score=0.0,
        min_price=None,
        max_price=None,
        currency="PLN",
        is_smartphone=False,
        status_code=status_code,
    )
    db.add(log)
    db.commit()
