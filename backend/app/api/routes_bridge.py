"""Identity Bridge API."""

from fastapi import APIRouter
from app.services.identity_bridge import IdentityBridgeService
from app.config.settings import settings

router = APIRouter(prefix="/bridge", tags=["bridge"])

@router.get("/live-map")
def get_live_identity_map():
    """Returns the real-time mapping of OS PIDs to MySQL Connection IDs."""
    bridge = IdentityBridgeService(
        host=settings.mysql_host,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database="information_schema"
    )
    mapping = bridge.build_pid_to_connection_map()
    
    # Format the result nicely
    result = []
    for pid, conn_id in mapping.items():
        result.append({
            "os_pid": pid,
            "mysql_connection_id": conn_id
        })
        
    return {"status": "success", "active_bridges": len(result), "mapping": result}
