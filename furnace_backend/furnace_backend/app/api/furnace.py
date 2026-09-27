"""
退火炉全流程温度预测系统 API
集成加热/保温/降温三阶段Bi-LSTM模型
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.core import success_response, error_response
from app.services.furnace_service import FurnaceService

router = APIRouter(prefix="/furnace", tags=["furnace"])

furnace_service = FurnaceService()


@router.get("/current")
async def get_current():
    """获取当前传感器数据"""
    data = furnace_service.get_current()
    if not data:
        raise HTTPException(status_code=503, detail="数据未就绪")
    return success_response(data=data)


@router.get("/history")
async def get_history():
    """获取过去一小时历史数据"""
    data = furnace_service.get_history()
    if not data:
        raise HTTPException(status_code=503, detail="数据未就绪")
    return success_response(data=data)


@router.get("/prediction")
async def get_prediction():
    """获取温度预测和报警状态"""
    data = furnace_service.get_prediction()
    if not data:
        raise HTTPException(status_code=503, detail="数据未就绪")
    return success_response(data=data)


@router.get("/phases")
async def get_phases():
    """获取各阶段时间边界信息"""
    data = furnace_service.get_phases()
    return success_response(data=data)


@router.get("/alarms")
async def get_alarm_records(
    phase: Optional[str] = Query(None, description="按阶段筛选: heating/holding/cooling/unload"),
    acknowledged: Optional[bool] = Query(None, description="按确认状态筛选")
):
    """获取报警记录"""
    data = furnace_service.get_alarm_records(phase=phase, acknowledged=acknowledged)
    return success_response(data=data)


@router.put("/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: int):
    """确认单条报警"""
    ok = furnace_service.acknowledge_alarm(alarm_id)
    if not ok:
        return error_response(code=-1, message="报警记录不存在")
    return success_response(message="已确认")


@router.put("/alarms/acknowledge-all")
async def acknowledge_all_alarms():
    """确认全部报警"""
    count = furnace_service.acknowledge_all_alarms()
    return success_response(data={"count": count}, message=f"已确认 {count} 条报警")
