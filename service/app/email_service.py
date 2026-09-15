from __future__ import annotations

import html
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .platform_models import EmailDelivery, EmailSenderIdentity, EmailSuppression
from .providers.resend_email import normalize_email

DEFAULT_FROM_EMAIL = "contato@app.mago-bot.com"
DEFAULT_FROM_NAME = "Mago Bot"
DEFAULT_REPLY_TO = "nao-responda@app.mago-bot.com"
DEFAULT_PUBLIC_BASE_URL = "https://app.mago-bot.com"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def default_from_email() -> str:
    return normalize_email(_env("EMAIL_DEFAULT_FROM", DEFAULT_FROM_EMAIL)) or DEFAULT_FROM_EMAIL


def default_reply_to() -> str:
    return normalize_email(_env("EMAIL_DEFAULT_REPLY_TO", DEFAULT_REPLY_TO)) or DEFAULT_REPLY_TO


def public_base_url() -> str:
    return _env("EMAIL_PUBLIC_BASE_URL", DEFAULT_PUBLIC_BASE_URL).rstrip("/")


def _sender_identity(db: Session, *, tenant_id: int | None, sender_email: str | None = None) -> EmailSenderIdentity | None:
    address = normalize_email(sender_email) if sender_email else default_from_email()
    if not address:
        return None
    queries = []
    if tenant_id is not None:
        queries.append(select(EmailSenderIdentity).where(
            EmailSenderIdentity.tenant_id == tenant_id,
            EmailSenderIdentity.sender_email == address,
            EmailSenderIdentity.status == "active",
        ))
    queries.append(select(EmailSenderIdentity).where(
        EmailSenderIdentity.tenant_id.is_(None),
        EmailSenderIdentity.sender_email == address,
        EmailSenderIdentity.status == "active",
    ))
    for query in queries:
        identity = db.scalar(query)
        if identity:
            return identity
    identity = EmailSenderIdentity(
        tenant_id=None,
        sender_email=address,
        sender_name=_env("EMAIL_DEFAULT_FROM_NAME", DEFAULT_FROM_NAME)[:180],
        reply_to=default_reply_to(),
        purpose="transactional",
        status="active",
    )
    try:
        with db.begin_nested():
            db.add(identity)
            db.flush()
        return identity
    except IntegrityError:
        return db.scalar(select(EmailSenderIdentity).where(
            EmailSenderIdentity.tenant_id.is_(None),
            EmailSenderIdentity.sender_email == address,
            EmailSenderIdentity.status == "active",
        ))


def _layout(*, title: str, preheader: str, body: str) -> tuple[str, str]:
    safe_title = html.escape(title)
    html_body = f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe_title}</title></head>
<body style="margin:0;background:#07111f;color:#e8f0ff;font-family:Arial,sans-serif;line-height:1.6">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0">{html.escape(preheader)}</div>
  <main style="max-width:620px;margin:0 auto;padding:40px 20px">
    <section style="background:#0e2037;border:1px solid #203b5c;border-radius:18px;padding:32px;box-shadow:0 18px 50px rgba(0,0,0,.25)">
      <div style="font-size:13px;letter-spacing:.18em;color:#62e6ff;font-weight:700">MAGO BOT</div>
      {body}
    </section>
    <p style="font-size:12px;color:#7f94ae;text-align:center;margin:22px 0 0">Mensagem automática. Este endereço não recebe respostas.</p>
  </main>
</body>
</html>"""
    text_body = f"MAGO BOT\n\n{title}\n\n{preheader}\n"
    return html_body, text_body


def render_message(message_type: str, *, recipient_name: str | None, token: str | None = None) -> tuple[str, str, str]:
    name = html.escape((recipient_name or "").strip() or "Olá")
    base_url = public_base_url()
    if message_type == "welcome":
        title = "Seu ambiente Mago Bot está pronto"
        preheader = "Bem-vindo ao control plane profissional de conversas."
        body = f"""<h1 style=\"font-size:28px;margin:24px 0 8px\">Bem-vindo, {name}.</h1>
<p>Seu ambiente do Mago Bot foi criado. A partir daqui você controla projetos, providers, API keys, quotas e webhooks em uma operação única.</p>
<p style=\"color:#9db2ca\">Mensagem automática de onboarding. Não responda este e-mail.</p>"""
    elif message_type == "email_verification":
        title = "Confirme seu e-mail no Mago Bot"
        preheader = "Mais um passo para ativar sua conta com segurança."
        url = f"{base_url}/admin?verify={html.escape(token or '')}"
        body = f"""<h1 style=\"font-size:28px;margin:24px 0 8px\">Confirme seu e-mail</h1>
<p>Olá, {name}. Clique no botão abaixo para confirmar o endereço e ativar seu ambiente.</p>
<p><a href=\"{url}\" style=\"display:inline-block;background:#62e6ff;color:#06101d;text-decoration:none;font-weight:700;border-radius:10px;padding:13px 18px\">Confirmar e-mail</a></p>
<p style=\"font-size:13px;color:#9db2ca\">Se o botão não abrir, acesse o portal Mago Bot e use o código recebido na URL.</p>"""
    elif message_type == "password_reset":
        title = "Redefina sua senha do Mago Bot"
        preheader = "Recebemos uma solicitação segura para trocar sua senha."
        url = f"{base_url}/admin?reset={html.escape(token or '')}"
        body = f"""<h1 style=\"font-size:28px;margin:24px 0 8px\">Redefinição de senha</h1>
<p>Olá, {name}. Se foi você, clique abaixo para continuar. O link expira em 24 horas.</p>
<p><a href=\"{url}\" style=\"display:inline-block;background:#62e6ff;color:#06101d;text-decoration:none;font-weight:700;border-radius:10px;padding:13px 18px\">Redefinir senha</a></p>
<p style=\"font-size:13px;color:#9db2ca\">Se você não solicitou isso, ignore esta mensagem. Sua senha continua protegida.</p>"""
    else:
        raise ValueError("unsupported transactional email type")
    html_body, text_body = _layout(title=title, preheader=preheader, body=body)
    return title, html_body, text_body + f"\nAcesse: {base_url}/admin\n"


def enqueue_email(
    db: Session,
    *,
    tenant_id: int | None,
    user_id: int | None,
    source_type: str,
    source_id: str,
    message_type: str,
    recipient_email: str,
    recipient_name: str | None,
    token: str | None = None,
    sender_email: str | None = None,
) -> bool:
    recipient = normalize_email(recipient_email)
    if not recipient:
        return False
    suppressed = db.scalar(select(EmailSuppression.id).where(EmailSuppression.email == recipient))
    if suppressed:
        return False
    subject, html_body, text_body = render_message(message_type, recipient_name=recipient_name, token=token)
    identity = _sender_identity(db, tenant_id=tenant_id, sender_email=sender_email)
    if not identity:
        return False
    row = EmailDelivery(
        tenant_id=tenant_id,
        user_id=user_id,
        sender_identity_id=identity.id,
        source_type=source_type,
        source_id=str(source_id),
        message_type=message_type,
        recipient_email=recipient,
        recipient_name=(recipient_name or "").strip()[:180] or None,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        status="pending",
        next_attempt_at=_now(),
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return False
    return True
