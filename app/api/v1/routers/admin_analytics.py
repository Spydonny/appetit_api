from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, distinct

from app.core.security import require_manager, require_admin
from app.db.session import get_db
from app import models

router = APIRouter(prefix="/admin/analytics", tags=["admin"])


@router.get("/summary")
def summary(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    # parse date filters (gracefully ignore invalid)
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    orders_q = db.query(models.Order)
    if dt_from:
        orders_q = orders_q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        orders_q = orders_q.filter(models.Order.created_at <= dt_to)

    total_orders = orders_q.count()
    total_revenue = orders_q.with_entities(func.coalesce(func.sum(models.Order.total), 0)).scalar() or 0
    total_revenue = float(total_revenue)

    avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0.0

    # users
    total_users = db.query(models.User).filter(models.User.role == "user").count()

    # active users: distinct users with orders in selected range; if no range, last 30 days
    active_q = db.query(models.Order.user_id).filter(models.Order.user_id.isnot(None))
    if dt_from or dt_to:
        if dt_from:
            active_q = active_q.filter(models.Order.created_at >= dt_from)
        if dt_to:
            active_q = active_q.filter(models.Order.created_at <= dt_to)
    else:
        active_q = active_q.filter(models.Order.created_at >= datetime.utcnow() - timedelta(days=30))
    active_users = active_q.distinct().count()

    # today stats (UTC)
    start_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = start_today + timedelta(days=1)
    today_q = db.query(models.Order).filter(models.Order.created_at >= start_today, models.Order.created_at < end_today)
    orders_today = today_q.count()
    revenue_today = float(today_q.with_entities(func.coalesce(func.sum(models.Order.total), 0)).scalar() or 0)

    return {
        "total_orders": int(total_orders),
        "total_revenue": round(total_revenue, 2),
        "total_users": int(total_users),
        "active_users": int(active_users),
        "avg_order_value": avg_order_value,
        "orders_today": int(orders_today),
        "revenue_today": round(revenue_today, 2),
    }


@router.get("/orders-by-period")
def orders_by_period(
    period: str = Query("day", description="Period: day, week, month"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """orders aggregated by period. Returns a list for compatibility with SQLite in tests."""

    # parse dates (gracefully ignore invalid)
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # fetch minimal fields to aggregate in Python (cross-DB)
    q = db.query(models.Order.created_at, models.Order.total)
    if dt_from:
        q = q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        q = q.filter(models.Order.created_at <= dt_to)

    rows = q.all()

    # grouping helpers
    from collections import defaultdict
    buckets = defaultdict(lambda: {"orders_count": 0, "total_revenue": 0.0})

    def period_key(dt: datetime) -> str:
        if period == "week":
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period == "month":
            return f"{dt.year:04d}-{dt.month:02d}"
        else:
            # default to day
            return dt.date().isoformat()

    for created_at, total in rows:
        if not created_at:
            continue
        key = period_key(created_at)
        buckets[key]["orders_count"] += 1
        buckets[key]["total_revenue"] += float(total or 0)

    # build sorted list by period key (lexicographic works for our formatted keys)
    data = []
    for key in sorted(buckets.keys()):
        orders_count = buckets[key]["orders_count"]
        total_revenue = buckets[key]["total_revenue"]
        avg = round(total_revenue / orders_count, 2) if orders_count else 0
        data.append({
            "period": key,
            "orders_count": int(orders_count),
            "revenue": round(total_revenue, 2),
            "avg_order_value": avg,
        })

    return data


@router.get("/order-sources")
def order_sources(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """order sources grouped by fulfillment type (delivery/pickup/etc.). Returns a list for tests."""

    # parse dates
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # query minimal fields and aggregate in Python (SQLite friendly)
    q = db.query(models.Order.pickup_or_delivery, models.Order.total, models.Order.created_at)
    if dt_from:
        q = q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        q = q.filter(models.Order.created_at <= dt_to)

    rows = q.all()

    from collections import defaultdict
    buckets = defaultdict(lambda: {"count": 0, "total": 0.0})

    for pickup_or_delivery, total, _created_at in rows:
        key = pickup_or_delivery or "unknown"
        buckets[key]["count"] += 1
        buckets[key]["total"] += float(total or 0)

    total_orders = sum(v["count"] for v in buckets.values())

    # build list with percentages
    result_list = []
    for key in sorted(buckets.keys()):
        count = buckets[key]["count"]
        total = buckets[key]["total"]
        percentage = round((count / total_orders) * 100, 2) if total_orders else 0.0
        result_list.append({
            "pickup_or_delivery": key,
            "count": int(count),
            "total": round(total, 2),
            "percentage": percentage,
        })

    return result_list


@router.get("/utm-sources")
def utm_sources(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """uTM source analytics - orders and revenue grouped by traffic sources."""

    # parse dates
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # query UTM fields, total, and created_at
    q = db.query(
        models.Order.utm_source, 
        models.Order.utm_medium, 
        models.Order.utm_campaign,
        models.Order.total, 
        models.Order.created_at
    )
    if dt_from:
        q = q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        q = q.filter(models.Order.created_at <= dt_to)

    rows = q.all()

    from collections import defaultdict
    utm_buckets = defaultdict(lambda: {"count": 0, "total": 0.0, "campaigns": set()})
    
    total_orders = len(rows)
    total_revenue = 0.0

    for utm_source, utm_medium, utm_campaign, total, _created_at in rows:
        # create source key - prioritize utm_source, fallback to "direct"
        source_key = utm_source or "direct"
        
        utm_buckets[source_key]["count"] += 1
        revenue = float(total or 0)
        utm_buckets[source_key]["total"] += revenue
        total_revenue += revenue
        
        # track campaigns for this source
        if utm_campaign:
            utm_buckets[source_key]["campaigns"].add(utm_campaign)

    # build result list
    result_list = []
    for source_key in sorted(utm_buckets.keys()):
        bucket = utm_buckets[source_key]
        count = bucket["count"]
        source_revenue = bucket["total"]
        campaigns = list(bucket["campaigns"])
        
        percentage = round((count / total_orders) * 100, 2) if total_orders else 0.0
        revenue_percentage = round((source_revenue / total_revenue) * 100, 2) if total_revenue else 0.0
        avg_order_value = round(source_revenue / count, 2) if count else 0.0
        
        result_list.append({
            "utm_source": source_key,
            "orders_count": int(count),
            "revenue": round(source_revenue, 2),
            "orders_percentage": percentage,
            "revenue_percentage": revenue_percentage,
            "avg_order_value": avg_order_value,
            "campaigns": campaigns[:5],  # Limit to top 5 campaigns for brevity
            "campaign_count": len(campaigns),
        })

    # sort by revenue descending
    result_list.sort(key=lambda x: x["revenue"], reverse=True)
    
    return {
        "sources": result_list,
        "summary": {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "sources_count": len(utm_buckets),
        }
    }


@router.get("/repeat-customers")
def repeat_customers(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """repeat customers analytics with customer segmentation. SQLite-friendly aggregation."""

    # parse dates
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # base query
    q = db.query(models.Order.user_id, models.Order.created_at)
    if dt_from:
        q = q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        q = q.filter(models.Order.created_at <= dt_to)

    rows = q.all()
    total_orders = len(rows)

    if total_orders == 0:
        return {
            "total_orders": 0,
            "repeat_orders": 0,
            "first_time_orders": 0,
            "repeat_percentage": 0.0,
            # customer-centric keys expected by tests
            "total_customers": 0,
            "new_customers": 0,
            "repeat_customers": 0,
            "repeat_rate": 0.0,
            "avg_orders_per_customer": 0.0,
        }

    # aggregate per registered user (ignore guests without user_id for segmentation)
    from collections import defaultdict
    counts_by_user = defaultdict(int)
    for user_id, _created_at in rows:
        if user_id is not None:
            counts_by_user[user_id] += 1

    total_customers = len(counts_by_user)
    repeat_customers_cnt = sum(1 for c in counts_by_user.values() if c >= 2)
    new_customers = max(0, total_customers - repeat_customers_cnt)

    # orders breakdown
    repeat_orders = sum(max(0, c - 1) for c in counts_by_user.values())
    first_time_orders = total_orders - repeat_orders

    repeat_percentage = round((repeat_orders / total_orders) * 100, 2) if total_orders else 0.0
    repeat_rate = round((repeat_customers_cnt / total_customers) * 100, 2) if total_customers else 0.0
    avg_orders_per_customer = round((total_orders / total_customers), 2) if total_customers else 0.0

    return {
        "total_orders": int(total_orders),
        "repeat_orders": int(repeat_orders),
        "first_time_orders": int(first_time_orders),
        "repeat_percentage": repeat_percentage,
        # customer-centric keys
        "total_customers": int(total_customers),
        "new_customers": int(new_customers),
        "repeat_customers": int(repeat_customers_cnt),
        "repeat_rate": repeat_rate,
        "avg_orders_per_customer": avg_orders_per_customer,
    }



@router.get("/dish-popularity")
def dish_popularity(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None, description="Filter by user id"),
    type_: Optional[str] = Query(None, alias="type", description="fulfillment filter: delivery|pickup"),
    sort_by: str = Query("qty", description="qty|revenue|avg_price|name"),
    order: str = Query("desc", description="asc|desc"),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Dish popularity aggregated from OrderItem + Order with filters and sorting.
    Returns list of items with qty, revenue and avg_price. SQLite-friendly (aggregates in Python).
    """
    # parse dates
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # minimal select and filter in DB
    q = db.query(
        models.OrderItem.item_id,
        models.OrderItem.name_snapshot,
        models.OrderItem.qty,
        models.OrderItem.price_at_moment,
        models.Order.pickup_or_delivery,
        models.Order.user_id,
        models.Order.created_at,
    ).join(models.Order, models.OrderItem.order_id == models.Order.id)

    if dt_from:
        q = q.filter(models.Order.created_at >= dt_from)
    if dt_to:
        q = q.filter(models.Order.created_at <= dt_to)
    if user_id is not None:
        q = q.filter(models.Order.user_id == user_id)
    if type_ in {"delivery", "pickup"}:
        q = q.filter(models.Order.pickup_or_delivery == type_)

    rows = q.all()

    from collections import defaultdict
    agg = defaultdict(lambda: {"qty": 0, "revenue": 0.0, "name": "", "item_id": None})

    for item_id, name_snapshot, qty, price, _pickup_or_delivery, _uid, _created in rows:
        key = item_id if item_id is not None else f"name:{name_snapshot}"  # fallback by name when item_id missing
        rec = agg[key]
        rec["item_id"] = item_id
        rec["name"] = name_snapshot
        qv = int(qty or 0)
        pr = float(price or 0)
        rec["qty"] += qv
        rec["revenue"] += qv * pr

    # build list and compute avg price
    data = []
    for key, rec in agg.items():
        qty = rec["qty"]
        revenue = rec["revenue"]
        avg_price = round(revenue / qty, 2) if qty else 0.0
        data.append({
            "item_id": rec["item_id"],
            "name": rec["name"],
            "qty": int(qty),
            "revenue": round(revenue, 2),
            "avg_price": avg_price,
        })

    # sorting
    sort_key = {
        "qty": lambda x: x["qty"],
        "revenue": lambda x: x["revenue"],
        "avg_price": lambda x: x["avg_price"],
        "name": lambda x: (x["name"] or "").lower(),
    }.get(sort_by, lambda x: x["qty"])

    reverse = (order.lower() != "asc")
    data.sort(key=sort_key, reverse=reverse)

    return data[:limit]


@router.get("/marketing-metrics")
def marketing_metrics(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    spend_android: float = Query(0.0, ge=0),
    spend_ios: float = Query(0.0, ge=0),
    spend_web: float = Query(0.0, ge=0),
    installs_android: int = Query(0, ge=0),
    installs_ios: int = Query(0, ge=0),
    installs_web: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Financial analytics (CPI, ROI, CPA) combining DB stats and provided marketing inputs.
    - Uses DB to compute orders_count and revenue in the given period.
    - Computes per-platform CPI using provided installs and spend.
    - Computes CPA as spend/total_orders (proxy for acquisitions).
    - Computes ROI as (revenue - spend)/spend; handles zero safely.
    - Placeholder for GA4 streams (android/ios/web) — future integration can replace proxies.
    """
    # parse dates
    dt_from = None
    dt_to = None
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
        except Exception:
            dt_from = None
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
        except Exception:
            dt_to = None

    # DB totals in period
    oq = db.query(models.Order)
    if dt_from:
        oq = oq.filter(models.Order.created_at >= dt_from)
    if dt_to:
        oq = oq.filter(models.Order.created_at <= dt_to)

    orders_count = oq.count()
    revenue_total = float(oq.with_entities(func.coalesce(func.sum(models.Order.total), 0)).scalar() or 0.0)

    # helper safe divisions
    def safe_div(num: float, den: float) -> float:
        try:
            return round(num / den, 4) if den else 0.0
        except Exception:
            return 0.0

    # per-platform CPI
    cpi_android = safe_div(spend_android, installs_android)
    cpi_ios = safe_div(spend_ios, installs_ios)
    cpi_web = safe_div(spend_web, installs_web)

    # totals for spend/installs
    spend_total = float(spend_android + spend_ios + spend_web)
    installs_total = int(installs_android + installs_ios + installs_web)
    cpi_total = safe_div(spend_total, installs_total)

    # cPA (proxy) and ROI based on DB totals
    cpa_total = safe_div(spend_total, orders_count)
    roi_total = safe_div((revenue_total - spend_total), spend_total)

    return {
        "period": {
            "from": dt_from.isoformat() if dt_from else None,
            "to": dt_to.isoformat() if dt_to else None,
        },
        "db": {
            "orders_count": int(orders_count),
            "revenue": round(revenue_total, 2),
            "avg_order_value": round(revenue_total / orders_count, 2) if orders_count else 0.0,
        },
        "inputs": {
            "spend": {"android": spend_android, "ios": spend_ios, "web": spend_web, "total": spend_total},
            "installs": {"android": installs_android, "ios": installs_ios, "web": installs_web, "total": installs_total},
        },
        "metrics": {
            "cpi": {"android": cpi_android, "ios": cpi_ios, "web": cpi_web, "total": cpi_total},
            "cpa": {"total": cpa_total},
            "roi": {"total": roi_total},
        },
        "notes": [
            "CPI uses provided installs/spend per platform.",
            "CPA uses total spend divided by DB orders_count as proxy.",
            "ROI uses DB revenue vs total spend.",
            "Future: integrate GA4 streams (android/ios/web) to replace proxies.",
        ],
    }
