# Checkout Pixel — Tracking Spec

**Source:** spec-checkout-pixel
**Status:** live

## Events
| Event | Fires on | Key params |
|---|---|---|
| `view_item` | product page load | item_id, price |
| `add_to_cart` | add-to-cart click | item_id, qty |
| `begin_checkout` | checkout page load | cart_value |
| `purchase` | order confirmation page | order_id, value, currency |

## Rules
- The checkout pixel fires a **`purchase`** event on the order confirmation page,
  once per order_id (deduped server-side on order_id).
- Currency is always sent in ISO-4217 (e.g. USD).
- No PII in params. Email is hashed (SHA-256) if passed.

## Owner
Growth engineering. Changes require an A/B-safe rollout.
