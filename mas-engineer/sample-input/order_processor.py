"""Order processing — applies discounts, calculates totals, sends notifications."""
import json
import smtplib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class OrderItem:
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


@dataclass
class Order:
    id: str
    customer_email: str
    customer_name: str
    items: list[OrderItem] = field(default_factory=list)
    coupon_code: str | None = None
    shipping_address: str | None = None


def process_order(order: Order, db: dict[str, Any]) -> dict[str, Any]:
    """Full order lifecycle: validate → calculate → apply discounts → save → notify."""
    # --- Validate coupon ---
    if order.coupon_code:
        coupon = db.get("coupons", {}).get(order.coupon_code)
        if not coupon:
            return {"success": False, "error": f"Coupon {order.coupon_code!r} not found"}
        if coupon.get("expires") and coupon["expires"] < "2026-07-29":
            return {"success": False, "error": "Coupon expired"}
        if coupon.get("usage_limit") and coupon.get("used_count", 0) >= coupon["usage_limit"]:
            return {"success": False, "error": "Coupon usage limit reached"}

    # --- Calculate subtotal ---
    subtotal = sum(it.quantity * it.unit_price for it in order.items)

    # --- Apply discount ---
    discount = Decimal("0")
    if order.coupon_code:
        coupon = db.get("coupons", {})[order.coupon_code]
        disc_type = coupon.get("type", "percentage")
        disc_val = Decimal(str(coupon.get("value", 0)))
        if disc_type == "percentage":
            discount = subtotal * (disc_val / Decimal("100"))
            if discount > Decimal(str(coupon.get("max_discount", "999999"))):
                discount = Decimal(str(coupon["max_discount"]))
        elif disc_type == "fixed":
            discount = disc_val
    # also apply a bulk discount: 5% if more than 10 items total
    total_qty = sum(it.quantity for it in order.items)
    if total_qty > 10:
        discount += subtotal * Decimal("0.05")

    subtotal_after_discount = max(Decimal("0"), subtotal - discount)

    # --- Calculate tax ---
    tax_rate = db.get("tax_rate", Decimal("0.08"))
    tax = subtotal_after_discount * tax_rate

    # --- Calculate shipping ---
    shipping = Decimal("0")
    if subtotal_after_discount < Decimal("50"):
        shipping = Decimal("5.99")
    elif subtotal_after_discount < Decimal("100"):
        shipping = Decimal("3.99")
    else:
        shipping = Decimal("0")

    total = subtotal_after_discount + tax + shipping

    # --- Save to db ---
    if "orders" not in db:
        db["orders"] = {}
    db["orders"][order.id] = {
        "subtotal": str(subtotal),
        "discount": str(discount),
        "tax": str(tax),
        "shipping": str(shipping),
        "total": str(total),
        "status": "confirmed",
    }

    # --- Send confirmation email ---
    msg = (
        f"Subject: Order {order.id} Confirmed\n\n"
        f"Hi {order.customer_name},\n\n"
        f"Your order (${total:.2f}) has been confirmed.\n"
        f"Items:\n"
    )
    for it in order.items:
        msg += f"  - {it.name} x{it.quantity} @ ${it.unit_price:.2f}\n"
    msg += f"\nSubtotal: ${subtotal:.2f}\n"
    msg += f"Discount: -${discount:.2f}\n"
    msg += f"Tax: ${tax:.2f}\n"
    msg += f"Shipping: ${shipping:.2f}\n"
    msg += f"Total: ${total:.2f}\n"

    smtp = db.get("smtp_server", "localhost")
    smtp_port = db.get("smtp_port", 25)
    try:
        with smtplib.SMTP(smtp, smtp_port) as server:
            sender = db.get("from_email", "orders@shop.example")
            server.sendmail(sender, [order.customer_email], msg)
    except Exception as e:
        return {"success": False, "error": f"Order saved but email failed: {e}"}

    return {"success": True, "order_id": order.id, "total": str(total)}
