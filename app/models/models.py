from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text, Float, UniqueConstraint, JSON, func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

# helper function for default timestamps
now = func.now()


# helpers
now = datetime.utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    dob: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    external_pos_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="user")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    saved_addresses: Mapped[list["SavedAddress"]] = relationship("SavedAddress", back_populates="user", cascade="all, delete-orphan")
    email_verifications: Mapped[list["EmailVerification"]] = relationship("EmailVerification", back_populates="user")
    phone_verifications: Mapped[list["PhoneVerification"]] = relationship("PhoneVerification", back_populates="user")
    cart: Mapped["Cart"] = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")


class SavedAddress(Base):
    __tablename__ = "saved_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    address_text: Mapped[str] = mapped_column(String(1024))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g., "Home", "Work", "Other"
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User] = relationship("User", back_populates="saved_addresses")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("fcm_token", name="uq_devices_fcm_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    platform: Mapped[str] = mapped_column(String(16))  # android|ios|web
    fcm_token: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User | None] = relationship("User", back_populates="devices")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English", "ru": "Russian", "kk": "Kazakh"}
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    name_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English name", "ru": "Russian name", "kk": "Kazakh name"}
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English desc", "ru": "Russian desc", "kk": "Kazakh desc"}
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    external_pos_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    category: Mapped[Category | None] = relationship("Category", back_populates="items")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="percent")  # percent|amount
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # From migration
    value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_order_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # From migration
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # From migration
    current_uses: Mapped[int] = mapped_column(Integer, default=0)  # From migration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # From migration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # From migration
    per_user_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    # --- Backward-compatible alias properties ---
    # active <-> is_active
    @property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = bool(value)

    # used_count -> current_uses
    @property
    def used_count(self) -> int:
        return self.current_uses

    @used_count.setter
    def used_count(self, value: int) -> None:
        self.current_uses = int(value) if value is not None else 0

    # max_redemptions <-> max_uses
    @property
    def max_redemptions(self) -> int | None:
        return self.max_uses

    @max_redemptions.setter
    def max_redemptions(self, value: int | None) -> None:
        self.max_uses = value if value is None else int(value)

    # min_subtotal <-> min_order_amount
    @property
    def min_subtotal(self) -> float | None:
        return float(self.min_order_amount) if self.min_order_amount is not None else None

    @min_subtotal.setter
    def min_subtotal(self, value: float | None) -> None:
        self.min_order_amount = value if value is None else float(value)

    # valid_to <-> expires_at
    @property
    def valid_to(self):
        return self.expires_at

    @valid_to.setter
    def valid_to(self, value) -> None:
        self.expires_at = value

    # valid_from placeholder (not persisted in current schema)
    @property
    def valid_from(self):
        return None

    @valid_from.setter
    def valid_from(self, value) -> None:
        # No-op to accept incoming payloads without breaking
        pass

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="promocode")


class PromoBatch(Base):
    __tablename__ = "promo_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prefix: Mapped[str] = mapped_column(String(16))
    length: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("number", name="uq_orders_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    pickup_or_delivery: Mapped[str] = mapped_column(String(16))  # delivery|pickup
    address_text: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="NEW")  # NEW|COOKING|ON_WAY|DELIVERED|CANCELLED
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    promocode_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promocode_id: Mapped[int | None] = mapped_column(ForeignKey("promocodes.id"), nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_method: Mapped[str] = mapped_column(String(16), default="cod")  # cod|online
    utm_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ga_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    external_pos_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User | None] = relationship("User", back_populates="orders")
    promocode: Mapped[Promocode | None] = relationship("Promocode", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True)
    name_snapshot: Mapped[str] = mapped_column(String(255))
    qty: Mapped[int] = mapped_column(Integer)
    price_at_moment: Mapped[float] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    menu_item: Mapped[MenuItem | None] = relationship("MenuItem", back_populates="order_items")
    modifications: Mapped[list["OrderItemModification"]] = relationship("OrderItemModification", back_populates="order_item", cascade="all, delete-orphan")




class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(255))
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User | None] = relationship("User", back_populates="email_verifications")


class PhoneVerification(Base):
    __tablename__ = "phone_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    phone: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(255))
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User | None] = relationship("User", back_populates="phone_verifications")


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    svix_id: Mapped[str] = mapped_column(String(255), unique=True)  # Unique event ID from Svix
    type: Mapped[str] = mapped_column(String(64))  # email.sent, email.opened, etc.
    email_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Resend email ID
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    link: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # For click events
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Additional event data
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class ModificationType(Base):
    __tablename__ = "modification_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    name_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English", "ru": "Russian", "kk": "Kazakh"}
    category: Mapped[str] = mapped_column(String(16))  # 'sauce' or 'removal'
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # True for default sauces
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    modifications: Mapped[list["OrderItemModification"]] = relationship("OrderItemModification", back_populates="modification_type")


class OrderItemModification(Base):
    __tablename__ = "order_item_modifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"))
    modification_type_id: Mapped[int] = mapped_column(ForeignKey("modification_types.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(16))  # 'add' or 'remove'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    order_item: Mapped[OrderItem] = relationship("OrderItem", back_populates="modifications")
    modification_type: Mapped[ModificationType] = relationship("ModificationType", back_populates="modifications")


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User] = relationship("User", back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"))
    qty: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    menu_item: Mapped[MenuItem] = relationship("MenuItem")
    modifications: Mapped[list["CartItemModification"]] = relationship("CartItemModification", back_populates="cart_item", cascade="all, delete-orphan")


class CartItemModification(Base):
    __tablename__ = "cart_item_modifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_item_id: Mapped[int] = mapped_column(ForeignKey("cart_items.id", ondelete="CASCADE"))
    modification_type_id: Mapped[int] = mapped_column(ForeignKey("modification_types.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(16))  # 'add' or 'remove'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    cart_item: Mapped[CartItem] = relationship("CartItem", back_populates="modifications")
    modification_type: Mapped[ModificationType] = relationship("ModificationType")


class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    title_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English", "ru": "Russian", "kk": "Kazakh"}
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"en": "English desc", "ru": "Russian desc", "kk": "Kazakh desc"}
    image_url: Mapped[str] = mapped_column(String(1024))  # WebP format image URL
    link_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # Optional link for banner click
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # For ordering banners
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When banner becomes active
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When banner expires
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    creator: Mapped[User] = relationship("User")


# update CartItem to include modifications relationship
CartItem.modifications = relationship("CartItemModification", back_populates="cart_item", cascade="all, delete-orphan")












