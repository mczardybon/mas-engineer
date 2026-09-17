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


# ── Domain helpers ─────────────────────────────────────────────────────


def _validate_coupon(coupon_code: str, db: dict[str, Any]) -> dict[str, Any] | None:
    """Return an error dict if the coupon is invalid, otherwise None."""
    coupon = db.get("coupons", {}).get(coupon_code)
    if not coupon:
        return {"success": False, "error": f"Coupon {coupon_code!r} not found"}
    if coupon.get("expires") and coupon["expires"] < "2026-07-29":
        return {"success": False, "error": "Coupon expired"}
    if coupon.get("usage_limit") and coupon.get("used_count", 0) >= coupon["usage_limit"]:
        return {"success": False, "error": "Coupon usage limit reached"}
    return None


def _calculate_discount(
    coupon_code: str | None,
    subtotal: Decimal,
    db: dict[str, Any],
    total_qty: int,
) -> Decimal:
    """Compute coupon + bulk discount."""
    discount = Decimal("0")

    if coupon_code:
        coupon = db.get("coupons", {})[coupon_code]
        disc_type = coupon.get("type", "percentage")
        disc_val = Decimal(str(coupon.get("value", 0)))
        if disc_type == "percentage":
            discount = subtotal * (disc_val / Decimal("100"))
            max_disc = coupon.get("max_discount")
            if max_disc and discount > Decimal(str(max_disc)):
                discount = Decimal(str(max_disc))
        elif disc_type == "fixed":
            discount = disc_val

    # Bulk discount: 5 % if more than 10 items
    if total_qty > 10:
        discount += subtotal * Decimal("0.05")

    return discount


def _calculate_shipping(subtotal_after_discount: Decimal) -> Decimal:
    """Determine shipping cost based on order value."""
    if subtotal_after_discount < Decimal("50"):
        return Decimal("5.99")
    if subtotal_after_discount < Decimal("100"):
        return Decimal("3.99")
    return Decimal("0")


def _save_order(
    order_id: str,
    subtotal: Decimal,
    discount: Decimal,
    tax: Decimal,
    shipping: Decimal,
    total: Decimal,
    db: dict[str, Any],
) -> None:
    """Persist order to the in-memory database."""
    if "orders" not in db:
        db["orders"] = {}
    db["orders"][order_id] = {
        "subtotal": str(subtotal),
        "discount": str(discount),
        "tax": str(tax),
        "shipping": str(shipping),
        "total": str(total),
        "status": "confirmed",
    }


def _build_confirmation_email(
    order: Order,
    subtotal: Decimal,
    discount: Decimal,
    tax: Decimal,
    shipping: Decimal,
    total: Decimal,
) -> str:
    """Construct the plain-text e-mail body."""
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
    return msg


def _send_email(sender: str, recipient: str, msg: str, smtp: str, port: int) -> None:
    """Deliver the e-mail via SMTP."""
    with smtplib.SMTP(smtp, port) as server:
        server.sendmail(sender, [recipient], msg)


# ── Public entry point ─────────────────────────────────────────────────


def process_order(order: Order, db: dict[str, Any]) -> dict[str, Any]:
    """Full order lifecycle: validate → calculate → apply discounts → save → notify."""
    # --- Validate coupon ---
    if order.coupon_code:
        err = _validate_coupon(order.coupon_code, db)
        if err:
            return err

    # --- Calculate ---
    subtotal = sum(it.quantity * it.unit_price for it in order.items)
    total_qty = sum(it.quantity for it in order.items)
    discount = _calculate_discount(order.coupon_code, subtotal, db, total_qty)
    subtotal_after_discount = max(Decimal("0"), subtotal - discount)

    tax_rate = db.get("tax_rate", Decimal("0.08"))
    tax = subtotal_after_discount * tax_rate
    shipping = _calculate_shipping(subtotal_after_discount)
    total = subtotal_after_discount + tax + shipping

    # --- Save ---
    _save_order(order.id, subtotal, discount, tax, shipping, total, db)

    # --- Notify ---
    msg = _build_confirmation_email(order, subtotal, discount, tax, shipping, total)
    smtp = db.get("smtp_server", "localhost")
    smtp_port = db.get("smtp_port", 25)
    sender = db.get("from_email", "orders@shop.example")
    try:
        _send_email(sender, order.customer_email, msg, smtp, smtp_port)
    except Exception as e:
        return {"success": False, "error": f"Order saved but email failed: {e}"}

    return {"success": True, "order_id": order.id, "total": str(total)}
