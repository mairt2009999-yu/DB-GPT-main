import logging
from typing import Optional

from fastapi import Header

from dbgpt._private.pydantic import BaseModel
from dbgpt_app.microservice.context import get_current_request_context

logger = logging.getLogger(__name__)


class UserRequest(BaseModel):
    user_id: Optional[str] = None
    user_no: Optional[str] = None
    real_name: Optional[str] = None
    # same with user_id
    user_name: Optional[str] = None
    user_channel: Optional[str] = None
    role: Optional[str] = "normal"
    nick_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    nick_name_like: Optional[str] = None


def get_user_from_headers(user_id: Optional[str] = Header(None)):
    try:
        request_context = get_current_request_context()
        resolved_user_id = request_context.user_id or user_id
        resolved_sys_code = request_context.sys_code
        resolved_roles = request_context.roles
        # Mock User Info
        if resolved_user_id:
            return UserRequest(
                user_id=resolved_user_id,
                user_name=resolved_user_id,
                user_no=resolved_user_id,
                role=",".join(resolved_roles) if resolved_roles else "admin",
                nick_name=resolved_user_id,
                real_name=resolved_user_id,
                user_channel=resolved_sys_code,
            )
        else:
            return UserRequest(
                user_id="001", role="admin", nick_name="dbgpt", real_name="dbgpt"
            )
    except Exception as e:
        logging.exception("Authentication failed!")
        raise Exception(f"Authentication failed. {str(e)}")
