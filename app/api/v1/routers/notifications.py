from fastapi import APIRouter
from app.schemas.notifications import EmailSendRequest, PushSendRequest
from app.services.email.email_sender import send_html
from app.services.push.fcm_admin import send_to_token

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/email")
def send_email(req: EmailSendRequest):
    res = send_html(to=req.to, subject=req.subject, html=req.html, tags=req.tags)
    return {"result": res}


@router.post("/push")
def send_push(req: PushSendRequest):
    res = send_to_token(req.token, title=req.title, body=req.body, data=req.data)
    return {"result": res}
