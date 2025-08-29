import os
import hashlib
from typing import Dict, Optional, Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

try:
    import resend  # type: ignore
except Exception:  # pragma: no cover
    resend = None  # graceful fallback when dependency not installed yet

FROM_EMAIL = os.getenv("FROM_EMAIL", "notify@example.com")
FROM_NAME = os.getenv("FROM_NAME", "MyApp")
APP_URL = os.getenv("APP_URL", "https://ium.app")

# template configs
TEMPLATES = {
    "verify_email": {
        "subject": "Verify your email address",
        "required_vars": ["user_name", "verify_url"],
        "optional_vars": ["otp"]
    },
    "order_created": {
        "subject": "Order #{order_id} created",
        "required_vars": ["order_id", "order_url", "pickup_or_delivery", "eta"],
        "optional_vars": []
    },
    "order_status": {
        "subject": "Order #{order_id} status update",
        "required_vars": ["order_id", "status", "eta"],
        "optional_vars": []
    },
    "order_delivered": {
        "subject": "Order #{order_id} delivered",
        "required_vars": ["order_id", "rating_url"],
        "optional_vars": []
    },
    "password_reset": {
        "subject": "Reset your password",
        "required_vars": ["reset_url"],
        "optional_vars": []
    }
}


def add_utm_parameters(url: str, template: str) -> str:
    """add UTM parameters to a URL for email tracking."""
    if not url or not url.startswith(('http://', 'https://')):
        return url
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # add UTM params
    query_params['utm_source'] = ['email']
    query_params['utm_medium'] = ['transactional']
    query_params['utm_campaign'] = [template]
    
    # convert back to query string
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def select_subject(template: str, variables: Dict[str, Any], locale: str = "en") -> str:
    """select and format subject line for a template with locale support."""
    if template not in TEMPLATES:
        return f"Notification from {FROM_NAME}"
    
    # locale-specific subjects
    subjects = {
        "verify_email": {
            "en": "Verify your email address",
            "ru": "Подтвердите ваш email адрес",
            "kk": "Электрондық поштаңызды растаңыз"
        },
        "order_created": {
            "en": "Order #{order_id} created",
            "ru": "Заказ №{order_id} создан",
            "kk": "Тапсырыс №{order_id} жасалды"
        },
        "order_status": {
            "en": "Order #{order_id} status update", 
            "ru": "Обновление статуса заказа №{order_id}",
            "kk": "Тапсырыс №{order_id} мәртебесі жаңартылды"
        },
        "order_delivered": {
            "en": "Order #{order_id} delivered",
            "ru": "Заказ №{order_id} доставлен",
            "kk": "Тапсырыс №{order_id} жеткізілді"
        },
        "password_reset": {
            "en": "Reset your password",
            "ru": "Сброс пароля",
            "kk": "Құпия сөзді қалпына келтіру"
        }
    }
    
    # get localized subject or fallback to English or default template
    if template in subjects:
        subject_template = subjects[template].get(locale, subjects[template].get("en", TEMPLATES[template]["subject"]))
    else:
        subject_template = TEMPLATES[template]["subject"]
    
    # simple variable substitution for subjects
    try:
        return subject_template.format(**variables)
    except (KeyError, ValueError):
        return subject_template


def render_template(template: str, variables: Dict[str, Any], locale: str = "en") -> str:
    """render HTML template with variables, UTM parameters, and locale support."""
    # add UTM params to all URLs in variables
    enhanced_vars = variables.copy()
    for key, value in variables.items():
        if isinstance(value, str) and key.endswith('_url'):
            enhanced_vars[key] = add_utm_parameters(value, template)
    
    # helper function to get localized text
    def get_text(key: str) -> str:
        texts = {
            "hello": {"en": "Hello", "ru": "Привет", "kk": "Сәлем"},
            "verify_email_desc": {"en": "Please verify your email address to complete your account setup.", "ru": "Пожалуйста, подтвердите свой email для завершения настройки аккаунта.", "kk": "Тіркелгіні орнатуды аяқтау үшін электрондық поштаңызды растаңыз."},
            "verification_code": {"en": "Your verification code", "ru": "Ваш код подтверждения", "kk": "Сіздің растау кодыңыз"},
            "verify_email_btn": {"en": "Verify Email", "ru": "Подтвердить Email", "kk": "Email растау"},
            "button_not_work": {"en": "If the button doesn't work, copy and paste this link", "ru": "Если кнопка не работает, скопируйте и вставьте эту ссылку", "kk": "Егер түйме жұмыс істемесе, осы сілтемені көшіріп жапсырыңыз"},
            "order_confirmed": {"en": "Order #{order_id} Confirmed!", "ru": "Заказ №{order_id} подтвержден!", "kk": "Тапсырыс №{order_id} расталды!"},
            "thank_you_order": {"en": "Thank you for your order. We're preparing it now.", "ru": "Спасибо за ваш заказ. Мы готовим его сейчас.", "kk": "Тапсырысыңыз үшін рахмет. Біз оны дайындап жатырмыз."},
            "type": {"en": "Type", "ru": "Тип", "kk": "Түрі"},
            "estimated_time": {"en": "Estimated time", "ru": "Предполагаемое время", "kk": "Болжалды уақыт"},
            "view_order": {"en": "View Order", "ru": "Посмотреть заказ", "kk": "Тапсырысты көру"},
            "pickup": {"en": "Pickup", "ru": "Самовывоз", "kk": "Өзіңіз алу"},
            "delivery": {"en": "Delivery", "ru": "Доставка", "kk": "Жеткізу"},
            "order_update": {"en": "Order #{order_id} Update", "ru": "Обновление заказа №{order_id}", "kk": "Тапсырыс №{order_id} жаңартылуы"},
            "status_updated": {"en": "Your order status has been updated to", "ru": "Статус вашего заказа обновлен до", "kk": "Тапсырысыңыздың мәртебесі жаңартылды"},
            "order_delivered_msg": {"en": "Order #{order_id} Delivered!", "ru": "Заказ №{order_id} доставлен!", "kk": "Тапсырыс №{order_id} жеткізілді!"},
            "delivered_thanks": {"en": "Your order has been successfully delivered. Thank you for choosing us!", "ru": "Ваш заказ успешно доставлен. Спасибо, что выбрали нас!", "kk": "Тапсырысыңыз сәтті жеткізілді. Бізді таңдағаныңыз үшін рахмет!"},
            "rate_experience": {"en": "How was your experience?", "ru": "Как вам понравился наш сервис?", "kk": "Біздің қызмет қалай ұнады?"},
            "rate_order": {"en": "Rate Your Order", "ru": "Оценить заказ", "kk": "Тапсырысты бағалау"},
            "password_reset_msg": {"en": "Password Reset Request", "ru": "Запрос на сброс пароля", "kk": "Құпия сөзді қалпына келтіру сұрауы"},
            "reset_desc": {"en": "You requested to reset your password. Click the button below to create a new password:", "ru": "Вы запросили сброс пароля. Нажмите кнопку ниже, чтобы создать новый пароль:", "kk": "Сіз құпия сөзді қалпына келтіруді сұрадыңыз. Жаңа құпия сөз жасау үшін төмендегі түймені басыңыз:"},
            "reset_password": {"en": "Reset Password", "ru": "Сбросить пароль", "kk": "Құпия сөзді қалпына келтіру"},
            "ignore_if_not_requested": {"en": "If you didn't request this, please ignore this email.", "ru": "Если вы не запрашивали это, пожалуйста, проигнорируйте это письмо.", "kk": "Егер сіз мұны сұрамаған болсаңыз, бұл хатты елемеңіз."}
        }
        return texts.get(key, {}).get(locale, texts.get(key, {}).get("en", ""))
    
    if template == "verify_email":
        user_name = enhanced_vars.get("user_name", "User")
        verify_url = enhanced_vars.get("verify_url", "#")
        otp = enhanced_vars.get("otp", "")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{get_text('hello')} {user_name}!</h2>
            <p>{get_text('verify_email_desc')}</p>
            {f'<p>{get_text("verification_code")}: <strong>{otp}</strong></p>' if otp else ''}
            <p><a href="{verify_url}" style="background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">{get_text('verify_email_btn')}</a></p>
            <p>{get_text('button_not_work')}: <a href="{verify_url}">{verify_url}</a></p>
        </div>
        """
        
    elif template == "order_created":
        order_id = enhanced_vars.get("order_id", "")
        order_url = enhanced_vars.get("order_url", "#")
        pickup_or_delivery = enhanced_vars.get("pickup_or_delivery", "pickup")
        eta = enhanced_vars.get("eta", "")
        
        # localize pickup/delivery type
        delivery_type_localized = get_text("pickup") if pickup_or_delivery.lower() == "pickup" else get_text("delivery")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{get_text('order_confirmed').format(order_id=order_id)}</h2>
            <p>{get_text('thank_you_order')}</p>
            <p><strong>{get_text('type')}:</strong> {delivery_type_localized}</p>
            <p><strong>{get_text('estimated_time')}:</strong> {eta}</p>
            <p><a href="{order_url}" style="background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">{get_text('view_order')}</a></p>
        </div>
        """
        
    elif template == "order_status":
        order_id = enhanced_vars.get("order_id", "")
        status = enhanced_vars.get("status", "")
        eta = enhanced_vars.get("eta", "")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{get_text('order_update').format(order_id=order_id)}</h2>
            <p>{get_text('status_updated')}: <strong>{status.title()}</strong></p>
            <p><strong>{get_text('estimated_time')}:</strong> {eta}</p>
        </div>
        """
        
    elif template == "order_delivered":
        order_id = enhanced_vars.get("order_id", "")
        rating_url = enhanced_vars.get("rating_url", "#")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{get_text('order_delivered_msg').format(order_id=order_id)}</h2>
            <p>{get_text('delivered_thanks')}</p>
            <p>{get_text('rate_experience')}</p>
            <p><a href="{rating_url}" style="background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">{get_text('rate_order')}</a></p>
        </div>
        """
        
    elif template == "password_reset":
        reset_url = enhanced_vars.get("reset_url", "#")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{get_text('password_reset_msg')}</h2>
            <p>{get_text('reset_desc')}</p>
            <p><a href="{reset_url}" style="background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">{get_text('reset_password')}</a></p>
            <p>{get_text('ignore_if_not_requested')}</p>
            <p>{get_text('button_not_work')}: <a href="{reset_url}">{reset_url}</a></p>
        </div>
        """
    else:
        html = "<p>Email notification</p>"
    
    return html


def send_email(
    template: str, 
    to: str, 
    variables: Dict[str, Any], 
    user_id: Optional[int] = None, 
    idempotency_key: Optional[str] = None,
    locale: str = "en"
) -> Dict[str, Any]:
    """
    Send transactional email using Resend API.
    
    Args:
        template: Email template name (verify_email, order_created, etc.)
        to: Recipient email address
        variables: Template variables
        user_id: Optional user ID for tracking
        idempotency_key: Optional key for preventing duplicate sends
        locale: Locale code for localized content (en, ru, kk)
        
    Returns:
        Dict with result including message_id from Resend
    """
    if resend is None:
        return {"status": "skipped", "reason": "resend_not_installed"}
    if not os.getenv("RESEND_API_KEY"):
        return {"status": "skipped", "reason": "resend_not_configured"}
    
    # check template
    if template not in TEMPLATES:
        return {"status": "error", "reason": "invalid_template", "template": template}
    
    # check required variables
    required_vars = TEMPLATES[template]["required_vars"]
    missing_vars = [var for var in required_vars if var not in variables]
    if missing_vars:
        return {"status": "error", "reason": "missing_variables", "missing": missing_vars}
    
    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        
        subject = select_subject(template, variables, locale)
        html = render_template(template, variables, locale)
        
        params = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
            "tags": [{"name": "category", "value": template}]
        }
        
        # add user_id tag if provided
        if user_id:
            params["tags"].append({"name": "user_id", "value": str(user_id)})
        
        result = resend.Emails.send(params)
        
        # extract message_id for idempotency tracking
        message_id = result.get("id") if isinstance(result, dict) else None
        
        return {
            "status": "sent",
            "message_id": message_id,
            "template": template,
            "recipient": to,
            "subject": subject
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "reason": "send_failed", 
            "error": str(e),
            "template": template,
            "recipient": to
        }


def send_html(to: str, subject: str, html: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Send an email via Resend if configured; otherwise, no-op.
    Compatibility function matching resend_client.py interface.
    """
    if resend is None:
        return {"status": "skipped", "reason": "resend_not_installed"}
    if not os.getenv("RESEND_API_KEY") or not FROM_EMAIL:
        # no-op fallback for dev environments
        return {"status": "skipped", "reason": "resend_not_configured"}

    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        params = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if tags:
            params["tags"] = [{"name": k, "value": str(v)} for k, v in tags.items()]
        
        result = resend.Emails.send(params)
        
        # return consistent format like send_email
        message_id = result.get("id") if isinstance(result, dict) else None
        return {
            "status": "sent",
            "message_id": message_id,
            "recipient": to,
            "subject": subject
        }
    except Exception as e:
        return {"status": "error", "reason": "send_failed", "error": str(e)}


def health_check() -> Dict[str, str]:
    """check email sender config and health."""
    if resend is None:
        return {"status": "unavailable", "reason": "resend_not_installed"}
    
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL")
    
    if not api_key:
        return {"status": "misconfigured", "reason": "missing_api_key"}
    if not from_email:
        return {"status": "misconfigured", "reason": "missing_from_email"}
    
    return {"status": "configured", "from_email": from_email, "from_name": FROM_NAME, "templates": len(TEMPLATES)}