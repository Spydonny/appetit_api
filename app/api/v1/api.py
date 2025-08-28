from fastapi import APIRouter

from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import devices as devices_router
from app.api.v1.routers import menu as menu_router
from app.api.v1.routers import promo as promo_router
from app.api.v1.routers import cart as cart_router
from app.api.v1.routers import orders as orders_router
from app.api.v1.routers import users as users_router
from app.api.v1.routers import notifications as notifications_router
from app.api.v1.routers import auth_email as auth_email_router
from app.api.v1.routers import auth_phone as auth_phone_router
from app.api.v1.routers import maps as maps_router
from app.api.v1.routers import payments as payments_router
from app.api.v1.routers import modifications as modifications_router
from app.api.v1.routers import admin_orders as admin_orders_router
from app.api.v1.routers import admin_analytics as admin_analytics_router
from app.api.v1.routers import admin_promo as admin_promo_router
from app.api.v1.routers import admin_push as admin_push_router
from app.api.v1.routers import admin_banners as admin_banners_router
from app.api.v1.routers import admin_business_hours as admin_business_hours_router
from app.api.v1.routers import admin_integrations as admin_integrations_router
from app.api.v1.routers import admin_localizations as admin_localizations_router
from app.api.v1.routers import admin_users as admin_users_router
from app.api.v1.routers import webhooks_resend as webhooks_resend_router

# role-based routes
from app.api.v1.routers import manager as manager_router
from app.api.v1.routers import courier as courier_router

router = APIRouter()

# public/auth routes
router.include_router(auth_router.router)
router.include_router(devices_router.router)
router.include_router(menu_router.router)
router.include_router(promo_router.router)
router.include_router(cart_router.router)
router.include_router(orders_router.router)
router.include_router(users_router.router)
router.include_router(notifications_router.router)
router.include_router(auth_email_router.router)
router.include_router(auth_phone_router.router)
router.include_router(maps_router.router)
router.include_router(payments_router.router)
router.include_router(modifications_router.router)

# webhook routes
router.include_router(webhooks_resend_router.router)

# admin routes
router.include_router(admin_orders_router.router)
router.include_router(admin_analytics_router.router)
router.include_router(admin_promo_router.router)
router.include_router(admin_push_router.router)
router.include_router(admin_banners_router.router)
router.include_router(admin_business_hours_router.router)
router.include_router(admin_integrations_router.router)
router.include_router(admin_localizations_router.router)
router.include_router(admin_users_router.router)

# role-based routes
router.include_router(manager_router.router)
router.include_router(courier_router.router)
