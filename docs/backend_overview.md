# Textile Mill ERP Backend Overview

## The Story
The team started from a retail shop ERP, which is built around buying finished products and selling them. A textile mill works differently: it buys raw yarn, runs it through machines, produces fabric rolls, checks them, stores them and ships them. So everything retail-specific (loyalty points, POS, promotions, product categories) was removed and replaced with mill concepts.

## How the Code is Organised
Three layers, each with one job:

- `models/`: defines the data (tables for items, orders, machines, rolls, invoices).
- `services/`: holds the rules (what’s allowed and what isn’t).
- `api/`: is the set of endpoints that the outside world calls.

Plus a few support files: login and sessions, a permissions file for who can do what, a seed file for demo data, and migrations for the database structure.

## The Five Workflows

1. **Stock:** Yarn quantities are never edited directly. Every change is written as a ledger entry (received, issued to production, fabric in, fabric out), so there’s always a history. Yarn is stored in grams as whole numbers to avoid decimal rounding errors, and stock can’t go below zero. There are two fixed stores: `RAW` for yarn and `FIN` for finished fabric.
2. **Yarn arrives:** The store keeper creates a purchase order. When the truck arrives, receiving it creates a receipt and a yarn lot (e.g. `LOT-2026-00001`), and adds the yarn to `RAW`. Every later roll points back to its lot, so you can say which supplier’s yarn went into which roll.
3. **Order and yarn check:** Office staff create a buyer order in meters. Before it can be confirmed, the system works out the yarn needed (meters x the fabric’s yarn per meter x 1000 for grams) and compares it with the stock in `RAW`. If there isn’t enough, confirmation is refused with an “insufficient yarn” error.
4. **Production and rolls:** The supervisor assigns the order to a machine and starts a run. As it moves through the stages, yarn is taken out of stock. At the last stage the rolls are registered, each with its own number (`ROLL-000001`, `ROLL-000002`) and starting status awaiting QC. The QC inspector then passes (and the roll goes into the `FIN` store), sends for rework, or rejects it, and a rejected roll can never be sold.
5. **Dispatch and invoice:** The store keeper picks rolls for a buyer and enters the vehicle and driver details. On confirmation, the rolls become dispatched, finished stock goes down, and an invoice is generated automatically from the meters shipped. A database rule says a roll can appear in only one dispatch, which is the double-dispatch protection.

## Security
Six roles (admin, owner, store, floor supervisor, QC, office), and every endpoint checks the role first. Login uses hashed passwords and a secure session cookie.

## The Git Part
A teammate had already pushed frontend scaffolding to the remote. Instead of overwriting it, the backend went onto its own branch so both can be merged later through a pull request.

## Key Verifications
- QC statuses are strictly: `pass`, `rework`, and `reject`.
- The yarn check happens when an order is confirmed.
- Roll QR labels exist.
- The uniqueness rule on dispatched rolls is actively enforced.
