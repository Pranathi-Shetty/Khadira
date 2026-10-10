"""Role and permission matrix for Khadira."""

ROLES: dict[str, dict] = {
    "admin": {
        "label": "Administrator",
        "permissions": "*",  # all
    },
    "owner": {
        "label": "Mill Owner",
        "permissions": "*",
    },
    "store": {
        "label": "Store Keeper",
        "permissions": [
            "items.read", "items.write",
            "purchasing.read", "purchasing.write",
            "inventory.read", "inventory.write",
            "rolls.read",
            "dispatch.read",
            "reports.read",
        ],
    },
    "floor_supervisor": {
        "label": "Floor Supervisor",
        "permissions": [
            "items.read",
            "machines.read",
            "production.read", "production.write",
            "rolls.read", "rolls.write",
            "reports.read",
        ],
    },
    "qc": {
        "label": "QC Inspector",
        "permissions": [
            "items.read",
            "rolls.read",
            "qc.read", "qc.write",
            "reports.read",
        ],
    },
    "office": {
        "label": "Office Staff",
        "permissions": [
            "items.read",
            "partners.read", "partners.write",
            "orders.read", "orders.write",
            "dispatch.read", "dispatch.write",
            "finance.read", "finance.write",
            "reports.read",
        ],
    },
}


def permissions_for(role: str) -> set[str]:
    entry = ROLES.get(role)
    if entry is None:
        return set()
    perms = entry["permissions"]
    if perms == "*":
        # Build the full set from all non-wildcard roles
        all_perms: set[str] = set()
        for r, v in ROLES.items():
            if v["permissions"] != "*":
                all_perms.update(v["permissions"])
        # Plus admin-only ones
        all_perms.update([
            "users.read", "users.write",
            "settings.read", "settings.write",
            "machines.read", "machines.write",
        ])
        return all_perms
    return set(perms)
