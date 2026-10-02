import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from ..config import get_settings
from ..mailer import send_mail
from ..ratelimit import limiter

router = APIRouter(prefix="/api", tags=["public"])


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=10, max_length=4000)
    website: str | None = ""  # honeypot; real visitors never fill it


@router.post("/contact")
@limiter.limit(lambda: get_settings().contact_rate_limit)
def contact(request: Request, body: ContactIn):
    if body.website:
        return {"ok": True}  # silently drop bot submissions
    try:
        name = re.sub(r"[\r\n]+", " ", body.name).strip()
        send_mail(
            subject=f"Website enquiry from {name}",
            body=f"Name: {name}\nEmail: {body.email}\n\n{body.message}\n",
            reply_to=str(body.email),
        )
    except Exception:
        raise HTTPException(502, "Your message could not be sent. Please email us directly.")
    # Nothing is stored: the email is the only record.
    return {"ok": True}
