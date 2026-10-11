/**
 * Stage definitions and helpers for Khadira Textile Mills Order Tracking Flow
 */

export const DEFAULT_ORDER_STAGES = [
  {
    id: "stage-order-placed",
    label: "1. Order Confirmed",
    depth: 0,
    stageKey: "confirmed",
    badge: "PO Verified",
    description: "Buyer contract signed and tolerance percentage configured.",
  },
  {
    id: "stage-yarn-allocation",
    label: "Yarn Inventory Allocation",
    depth: 1,
    stageKey: "yarn",
    badge: "Raw Material",
    description: "Verifying warp and weft yarn kg availability in storehouse.",
  },
  {
    id: "stage-weaving-prep",
    label: "Warping & Beam Loading",
    depth: 1,
    stageKey: "warping",
    badge: "Shed Setup",
    description: "Yarn sizing, warping beam creeling, and loom setup.",
  },
  {
    id: "stage-loom-production",
    label: "2. Loom Weaving (Production)",
    depth: 0,
    stageKey: "weaving",
    badge: "Loom Shed",
    description: "Continuous greige fabric weaving on active looms.",
  },
  {
    id: "stage-roll-doffing",
    label: "Roll Doffing & Piece ID",
    depth: 1,
    stageKey: "doffing",
    badge: "Piece Tracking",
    description: "Fabric roll cut from loom, assigned serial piece barcode.",
  },
  {
    id: "stage-qc-inspection",
    label: "3. Quality Control (QC)",
    depth: 0,
    stageKey: "inspection",
    badge: "Inspection Frame",
    description: "4-Point defect grading, length measurement, and lab audit.",
  },
  {
    id: "stage-qc-passed",
    label: "Passed Metres Clearance",
    depth: 1,
    stageKey: "passed",
    badge: "Grade A/B",
    description: "Rolls verified against tolerance before warehouse transfer.",
  },
  {
    id: "stage-finished-warehouse",
    label: "4. Finished Goods Warehouse",
    depth: 0,
    stageKey: "in_store",
    badge: "Store Staged",
    description: "Inspected rolls stacked in FG store ready for packaging.",
  },
  {
    id: "stage-dispatch-gate",
    label: "5. Dispatch & Transit",
    depth: 0,
    stageKey: "dispatched",
    badge: "Gate Clearance",
    description: "Container loading, packing slip, and gate pass issued.",
  },
  {
    id: "stage-delivery-invoicing",
    label: "6. Delivered & Invoiced",
    depth: 0,
    stageKey: "delivered",
    badge: "Closed",
    description: "Buyer delivery confirmed and tax invoice reconciled.",
  },
];

/**
 * Determine the active stage index from order tracking status & stages
 */
export function getOrderStageIndex(order, stages = DEFAULT_ORDER_STAGES) {
  if (!order) return 0;
  const status = (order.status || "").toLowerCase();
  const stage = (order.current_stage || "").toLowerCase();

  if (status === "delivered") {
    const idx = stages.findIndex((s) => s.stageKey === "delivered");
    return idx !== -1 ? idx : stages.length - 1;
  }
  if (
    status === "production_complete" ||
    stage === "dispatched" ||
    (order.meters_by_stage && order.meters_by_stage.dispatched > 0)
  ) {
    const idx = stages.findIndex((s) => s.stageKey === "dispatched");
    if (idx !== -1) return idx;
  }
  if (
    stage === "in_store" ||
    (order.meters_by_stage && order.meters_by_stage.in_store > 0)
  ) {
    const idx = stages.findIndex((s) => s.stageKey === "in_store");
    if (idx !== -1) return idx;
  }
  if (
    stage === "inspection" ||
    stage === "awaiting_qc" ||
    (order.meters_by_stage && order.meters_by_stage.awaiting_qc > 0)
  ) {
    const idx = stages.findIndex((s) => s.stageKey === "inspection");
    if (idx !== -1) return idx;
  }
  if (
    status === "in_production" ||
    stage === "weaving" ||
    stage === "production" ||
    (order.meters_by_stage && order.meters_by_stage.produced > 0)
  ) {
    const idx = stages.findIndex((s) => s.stageKey === "weaving");
    if (idx !== -1) return idx;
  }
  if (status === "confirmed") {
    const idx = stages.findIndex((s) => s.stageKey === "yarn");
    return idx !== -1 ? idx : 1;
  }
  return 0;
}
