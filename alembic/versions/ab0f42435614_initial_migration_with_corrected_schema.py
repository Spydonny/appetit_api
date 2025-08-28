"""Initial migration with corrected schema

Revision ID: ab0f42435614
Revises: 
Create Date: 2025-08-28 16:57:16.421363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab0f42435614'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create all tables from scratch in correct dependency order
    
    # 1. Create independent tables (no foreign keys)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('dob', sa.String(length=32), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('is_email_verified', sa.Boolean(), nullable=False),
    sa.Column('is_phone_verified', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('external_pos_customer_id', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('phone')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=False)
    
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('name_translations', sa.JSON(), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('modification_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('name_translations', sa.JSON(), nullable=True),
    sa.Column('category', sa.String(length=16), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('promocodes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('discount_percent', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('min_order_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('max_uses', sa.Integer(), nullable=True),
    sa.Column('current_uses', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('per_user_limit', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    
    op.create_table('promo_batches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prefix', sa.String(length=16), nullable=False),
    sa.Column('length', sa.Integer(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('email_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('svix_id', sa.String(length=255), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('email_id', sa.String(length=255), nullable=True),
    sa.Column('recipient', sa.String(length=255), nullable=True),
    sa.Column('subject', sa.String(length=512), nullable=True),
    sa.Column('link', sa.String(length=1024), nullable=True),
    sa.Column('meta', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('svix_id')
    )
    
    # 2. Create tables that reference users
    op.create_table('devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('platform', sa.String(length=16), nullable=False),
    sa.Column('fcm_token', sa.String(length=512), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fcm_token', name='uq_devices_fcm_token')
    )
    
    op.create_table('saved_addresses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('address_text', sa.String(length=1024), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('label', sa.String(length=64), nullable=True),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_addresses_id'), 'saved_addresses', ['id'], unique=False)
    
    op.create_table('email_verifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('code_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('phone_verifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('code_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('carts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('banners',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('title_translations', sa.JSON(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('description_translations', sa.JSON(), nullable=True),
    sa.Column('image_url', sa.String(length=1024), nullable=False),
    sa.Column('link_url', sa.String(length=1024), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.DateTime(), nullable=True),
    sa.Column('end_date', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    sa.PrimaryKeyConstraint('id')
    )
    
    # 3. Create tables that reference categories
    op.create_table('menu_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('name_translations', sa.JSON(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('description_translations', sa.JSON(), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('image_url', sa.String(length=1024), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.Column('external_pos_id', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    
    # 4. Create orders table
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('pickup_or_delivery', sa.String(length=16), nullable=False),
    sa.Column('address_text', sa.String(length=1024), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lng', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('promocode_code', sa.String(length=64), nullable=True),
    sa.Column('promocode_id', sa.Integer(), nullable=True),
    sa.Column('paid', sa.Boolean(), nullable=False),
    sa.Column('payment_method', sa.String(length=16), nullable=False),
    sa.Column('utm_source', sa.String(length=64), nullable=True),
    sa.Column('utm_medium', sa.String(length=64), nullable=True),
    sa.Column('utm_campaign', sa.String(length=64), nullable=True),
    sa.Column('ga_client_id', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('external_pos_id', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['promocode_id'], ['promocodes.id']),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number', name='uq_orders_number')
    )
    
    # 5. Create tables that reference orders and menu_items
    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=True),
    sa.Column('name_snapshot', sa.String(length=255), nullable=False),
    sa.Column('qty', sa.Integer(), nullable=False),
    sa.Column('price_at_moment', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['menu_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('cart_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cart_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('qty', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['menu_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    # 6. Create modification tables
    op.create_table('order_item_modifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_item_id', sa.Integer(), nullable=False),
    sa.Column('modification_type_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['modification_type_id'], ['modification_types.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('cart_item_modifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cart_item_id', sa.Integer(), nullable=False),
    sa.Column('modification_type_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['cart_item_id'], ['cart_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['modification_type_id'], ['modification_types.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'updated_at')
    op.add_column('promocodes', sa.Column('max_redemptions', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('promocodes', sa.Column('active', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column('promocodes', sa.Column('min_subtotal', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True))
    op.add_column('promocodes', sa.Column('kind', sa.VARCHAR(length=16), autoincrement=False, nullable=False))
    op.add_column('promocodes', sa.Column('value', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=False))
    op.add_column('promocodes', sa.Column('valid_from', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('promocodes', sa.Column('valid_to', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'promocodes', type_='unique')
    op.drop_column('promocodes', 'updated_at')
    op.drop_column('promocodes', 'expires_at')
    op.drop_column('promocodes', 'is_active')
    op.drop_column('promocodes', 'current_uses')
    op.drop_column('promocodes', 'max_uses')
    op.drop_column('promocodes', 'min_order_amount')
    op.drop_column('promocodes', 'discount_percent')
    op.drop_column('promocodes', 'id')
    op.drop_column('promo_batches', 'updated_at')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.create_foreign_key(op.f('orders_promocode_code_fkey'), 'orders', 'promocodes', ['promocode_code'], ['code'])
    op.drop_column('orders', 'updated_at')
    op.drop_column('orders', 'promocode_id')
    op.drop_column('orders', 'phone')
    op.drop_column('order_items', 'updated_at')
    op.drop_column('order_items', 'created_at')
    op.drop_column('menu_items', 'updated_at')
    op.drop_column('menu_items', 'created_at')
    op.drop_column('menu_items', 'is_available')
    op.drop_column('menu_items', 'description_translations')
    op.drop_column('menu_items', 'name_translations')
    op.drop_column('email_verifications', 'updated_at')
    op.drop_column('email_events', 'updated_at')
    op.drop_column('devices', 'updated_at')
    op.drop_column('categories', 'updated_at')
    op.drop_column('categories', 'created_at')
    op.drop_column('categories', 'sort_order')
    op.drop_column('categories', 'is_active')
    op.drop_column('categories', 'name_translations')
    op.drop_column('categories', 'description')
    op.drop_table('order_item_modifications')
    op.drop_table('cart_item_modifications')
    op.drop_table('cart_items')
    op.drop_index(op.f('ix_saved_addresses_id'), table_name='saved_addresses')
    op.drop_table('saved_addresses')
    op.drop_table('phone_verifications')
    op.drop_table('carts')
    op.drop_table('banners')
    op.drop_table('modification_types')
    # ### end Alembic commands ###