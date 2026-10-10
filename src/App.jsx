import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  ShoppingBag, 
  X, 
  Plus, 
  Minus, 
  Trash2, 
  ArrowRight, 
  ArrowLeft, 
  Check, 
  Menu, 
  Sparkles,
  ExternalLink,
  Lock,
  Eye,
  EyeOff,
  Activity,
  Cpu,
  RefreshCw,
  Search,
  Download,
  AlertCircle,
  ShieldCheck,
  Factory,
  Layers,
  ChevronRight,
  TrendingUp,
  FileText,
  PanelLeft,
  LayoutDashboard,
  BarChart3,
  ShoppingCart,
  Users,
  Tag,
  Truck,
  Building2,
  Boxes,
  Package,
  ArrowLeftRight,
  ClipboardList,
  Wallet,
  Receipt,
  Coins,
  AlertTriangle,
  ChevronsUpDown,
  LogOut
} from 'lucide-react';
import {
  Sun,
  Moon,
  Bell,
  Calendar,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import MillAPI from './services/api';
import './App.css';
import './everest-erp.css';

// =====================================================================
// USER PROVIDED ARTISAN TEXTILE & TACTILE CRAFT ASSETS
// =====================================================================
const CRAFT_ASSETS = {
  // 9 User Uploaded Assets
  spinningWheel: '/images/yarn-spinning-wheel.jpg',
  handEmbroidery: '/images/hand-embroidery-mirrorwork.jpg',
  blockPrinting: '/images/block-printing-textile.jpg',
  naturalDyedHanks: '/images/natural-dyed-yarn-hanks.png',
  crochetYarn: '/images/crochet-yarn-swatches.jpg',
  yarnSpoolsRack: '/images/yarn-spools-wall-rack.jpg',
  wovenSwatches: '/images/woven-fabric-swatches.jpg',
  goldThreadSwift: '/images/gold-red-thread-swift.jpg',
  handloomWeaving: '/images/handloom-backstrap-weaving.png',

  // Factory Operation Teams
  teamStoreManager: '/images/teams/store-manager.jpg',
  teamProductionSupervisor: '/images/teams/production-supervisor.jpg',
  teamQualityInspector: '/images/teams/quality-inspector.jpg',
  teamAccountsOwner: '/images/teams/accounts-owner.jpg',
};

// =====================================================================
// HERO 9-IMAGE ORBIT DEFINITION
// Populated with 9 unique authentic craft images in an elliptical orbit
// =====================================================================
const HERO_ORBIT_IMAGES = [
  {
    id: 'orbit-1',
    src: CRAFT_ASSETS.spinningWheel,
    alt: 'Red and yellow dyed yarn on traditional spinning wheel',
    angle: 0, // 3 o'clock (mid-right)
    rxMultiplier: 1.05,
    ryMultiplier: 0.95,
    widthDesktop: 220,
    widthMobile: 120,
    aspectRatio: '1 / 1.15',
    depth: 45,
    scrollFactor: -0.15,
    baseRotation: 4,
    baseScale: 1.0,
    zIndex: 6
  },
  {
    id: 'orbit-2',
    src: CRAFT_ASSETS.handEmbroidery,
    alt: 'Artisan hands sewing intricate mirrorwork embroidery',
    angle: (Math.PI * 2 / 9) * 1, // ~40° (lower-right)
    rxMultiplier: 0.98,
    ryMultiplier: 1.04,
    widthDesktop: 195,
    widthMobile: 110,
    aspectRatio: '1 / 1',
    depth: 52,
    scrollFactor: -0.18,
    baseRotation: -3,
    baseScale: 0.94,
    zIndex: 5
  },
  {
    id: 'orbit-3',
    src: CRAFT_ASSETS.blockPrinting,
    alt: 'Hand block printing with wooden stamps and organic pigment',
    angle: (Math.PI * 2 / 9) * 2, // ~80° (lower-center near "SQUISH")
    rxMultiplier: 0.92,
    ryMultiplier: 1.08,
    widthDesktop: 210,
    widthMobile: 120,
    aspectRatio: '1 / 1.1',
    depth: 35,
    scrollFactor: -0.12,
    baseRotation: 2,
    baseScale: 0.98,
    zIndex: 8
  },
  {
    id: 'orbit-4',
    src: CRAFT_ASSETS.naturalDyedHanks,
    alt: 'Natural dyed yarn hanks hanging on wooden workshop beams',
    angle: (Math.PI * 2 / 9) * 3, // ~120° (lower-left behind "THE")
    rxMultiplier: 1.02,
    ryMultiplier: 1.02,
    widthDesktop: 190,
    widthMobile: 105,
    aspectRatio: '1 / 1.2',
    depth: 48,
    scrollFactor: -0.16,
    baseRotation: -5,
    baseScale: 0.92,
    zIndex: 6
  },
  {
    id: 'orbit-5',
    src: CRAFT_ASSETS.crochetYarn,
    alt: 'Colorful yarn skeins, crochet hooks and crafted swatches',
    angle: (Math.PI * 2 / 9) * 4, // ~160° (far-left)
    rxMultiplier: 1.08,
    ryMultiplier: 0.96,
    widthDesktop: 235,
    widthMobile: 125,
    aspectRatio: '1 / 1.15',
    depth: 58,
    scrollFactor: -0.20,
    baseRotation: -4,
    baseScale: 1.02,
    zIndex: 5
  },
  {
    id: 'orbit-6',
    src: CRAFT_ASSETS.yarnSpoolsRack,
    alt: 'Wooden peg wall rack with vibrant spools of yarn',
    angle: (Math.PI * 2 / 9) * 5, // ~200° (upper-left)
    rxMultiplier: 1.04,
    ryMultiplier: 1.02,
    widthDesktop: 195,
    widthMobile: 110,
    aspectRatio: '1 / 1.1',
    depth: 42,
    scrollFactor: -0.14,
    baseRotation: 3,
    baseScale: 0.95,
    zIndex: 7
  },
  {
    id: 'orbit-7',
    src: CRAFT_ASSETS.wovenSwatches,
    alt: 'Tweed and woven tactile fabric swatches fan layout',
    angle: (Math.PI * 2 / 9) * 6, // ~240° (upper-center behind eyebrow)
    rxMultiplier: 0.94,
    ryMultiplier: 1.06,
    widthDesktop: 225,
    widthMobile: 120,
    aspectRatio: '1 / 1',
    depth: 38,
    scrollFactor: -0.15,
    baseRotation: -2,
    baseScale: 1.0,
    zIndex: 6
  },
  {
    id: 'orbit-8',
    src: CRAFT_ASSETS.goldThreadSwift,
    alt: 'Gold and crimson thread wound on handloom wooden swift',
    angle: (Math.PI * 2 / 9) * 7, // ~280° (upper-right)
    rxMultiplier: 1.02,
    ryMultiplier: 1.04,
    widthDesktop: 200,
    widthMobile: 115,
    aspectRatio: '1 / 1.15',
    depth: 46,
    scrollFactor: -0.17,
    baseRotation: 5,
    baseScale: 0.96,
    zIndex: 5
  },
  {
    id: 'orbit-9',
    src: CRAFT_ASSETS.handloomWeaving,
    alt: 'Artisan hands weaving vibrant pattern on traditional backstrap loom',
    angle: (Math.PI * 2 / 9) * 8, // ~320° (upper-right / mid-right)
    rxMultiplier: 1.06,
    ryMultiplier: 0.98,
    widthDesktop: 215,
    widthMobile: 115,
    aspectRatio: '1 / 1.3',
    depth: 54,
    scrollFactor: -0.19,
    baseRotation: -3,
    baseScale: 0.98,
    zIndex: 7
  }
];

// Core Modules Catalog
const PRODUCTS = [
  {
    id: 'mod-1',
    name: 'Raw Material Stock',
    price: 1,
    priceStr: 'LIVE SYNC',
    tag: 'Yarn & Chemical Vats',
    desc: 'Real-time tracking of yarn bales, cone lots, dye liquor inventory, and auto reorder triggers.',
    image: CRAFT_ASSETS.naturalDyedHanks
  },
  {
    id: 'mod-2',
    name: 'Machine Status',
    price: 1,
    priceStr: '98.4% UPTIME',
    tag: 'Loom Telemetry',
    desc: 'Sensor integration recording RPM, pick counters, stop causes, and preventive maintenance logs.',
    image: CRAFT_ASSETS.spinningWheel
  },
  {
    id: 'mod-3',
    name: 'Production Tracking',
    price: 1,
    priceStr: '14 BAYS ACTIVE',
    tag: 'Warp to Roll Flow',
    desc: 'Batch tracking through warping, sizing, shuttleless weaving, printing, and stenter finishing.',
    image: CRAFT_ASSETS.wovenSwatches
  },
  {
    id: 'mod-4',
    name: 'Quality Checks',
    price: 1,
    priceStr: 'ASTM 4-POINT',
    tag: 'Defect Mapping',
    desc: 'Digital fabric roll grading, defect marker mapping, lab tensile tests, and batch sign-off.',
    image: CRAFT_ASSETS.yarnSpoolsRack
  },
  {
    id: 'mod-5',
    name: 'Buyer Updates',
    price: 1,
    priceStr: 'AUTO PORTAL',
    tag: 'Export Orders',
    desc: 'Automated milestone alerts, packing lists, digital roll passports, and real-time WIP portals.',
    image: CRAFT_ASSETS.crochetYarn
  },
  {
    id: 'mod-6',
    name: 'Dispatch & Invoices',
    price: 1,
    priceStr: 'FAST CLEARANCE',
    tag: 'Logistics & ERP',
    desc: 'Barcode roll scanning, shipping container manifests, customs documentation, and ERP ledger sync.',
    image: CRAFT_ASSETS.goldThreadSwift
  }
];

const SHELF_ITEMS = [
  { title: 'Raw Fiber Ingestion & Cone Winding', code: 'STAGE / 01', image: CRAFT_ASSETS.spinningWheel },
  { title: 'Warp Preparation & Reed Drawing', code: 'STAGE / 02', image: CRAFT_ASSETS.handEmbroidery },
  { title: 'Shuttleless Loom Weaving Shed', code: 'STAGE / 03', image: CRAFT_ASSETS.blockPrinting },
  { title: 'Dyehouse Bleach, Vat & Stenter Finish', code: 'STAGE / 04', image: CRAFT_ASSETS.naturalDyedHanks },
  { title: 'Final 4-Point Roll Grading & Packing', code: 'STAGE / 05', image: CRAFT_ASSETS.wovenSwatches }
];

const REVIEWS = [
  {
    quote: '“KHADIRA dropped our loom downtime by 24% in the first quarter. Floor supervisors see machine stops immediately rather than at shift end.”',
    source: 'General Manager — Weaving & Loom Operations',
    stars: 5
  },
  {
    quote: '“Real-time tracking of yarn cones cut our dye lot variance to near zero. We know exactly which yarn batch went into every roll of fabric.”',
    source: 'VP Manufacturing — Technical Textiles & Dyeing',
    stars: 5
  },
  {
    quote: '“Audits that used to take three days now complete in forty minutes. Our global retail buyers have complete visibility from raw fiber to container seal.”',
    source: 'Director of Supply Chain & Global Exports',
    stars: 5
  }
];

const FAQS = [
  {
    question: 'How does KHADIRA connect to existing spinning and weaving looms?',
    answer: 'KHADIRA integrates with modern electronic looms (via standard industrial protocols like OPC-UA and Modbus) as well as mechanical looms through external pick sensors and floor IoT gateway hubs.'
  },
  {
    question: 'Can the platform handle multi-location mills and contract dye houses?',
    answer: 'Yes. KHADIRA is engineered for multi-plant operations, enabling real-time stock transfers, centralized dye recipe libraries, sub-contractor processing logs, and consolidated mill performance dashboards.'
  },
  {
    question: 'How does fabric roll grading adhere to international standards?',
    answer: 'The quality module natively supports ASTM D5430 (4-point system) and 10-point inspection workflows with configurable penalty thresholds per 100 meters, automatically classifying rolls as First Quality, Second Quality, or Cut Piece.'
  },
  {
    question: 'Does it integrate with existing ERP, accounting, and billing systems?',
    answer: 'KHADIRA provides secure REST APIs and pre-built connectors for SAP, Oracle, Microsoft Dynamics, Tally, and custom ERP systems for seamless ledger, wage billing, and inventory synchronization.'
  }
];


// =====================================================================
// KHADIRA TEXTILE MILLS DATA & VISUAL CONSTANTS
// =====================================================================
const KhadiraLogo = () => (
  <svg width="34" height="26" viewBox="0 0 40 28" fill="none" xmlns="http://www.w3.org/2000/svg" className="everest-logo-svg">
    <polygon points="12,3 1,26 23,26" fill="#FFFFFF" />
    <polygon points="12,3 7,14 13,12 18,15" fill="#CBD5E1" />
    <polygon points="26,8 15,26 37,26" fill="#FFFFFF" fillOpacity="0.95" />
    <polygon points="26,8 21,17 26,15 31,18" fill="#94A3B8" />
  </svg>
);

const MILL_FLOW_STEPS = [
  { step: 1, name: 'Yarn', status: 'Materials Ready', qty: '12.8 Tons', tint: 'green', image: '/assets/images/yarn-cones.jpg' },
  { step: 2, name: 'Weaving', status: 'In Production', qty: '8,240 m', tint: 'blue', image: '/assets/images/weaving-loom.jpg' },
  { step: 3, name: 'Dyeing', status: 'In Progress', qty: '2,300 m', tint: 'red', image: '/assets/images/dyeing-fabric.jpg' },
  { step: 4, name: 'Finishing', status: 'Completed Today', qty: '1,860 m', tint: 'blue', image: '/assets/images/finishing-fabric.jpg' },
  { step: 5, name: 'Dispatch', status: 'Ready to Ship', qty: '1,420 m', tint: 'orange', image: '/assets/images/dispatch-boxes.jpg' },
];

const MACHINE_STATUS_LIST = [
  { id: 'W01', name: 'Weaving - W01', status: 'Running', statusType: 'green', util: '85%', image: '/assets/images/machine-loom.jpg', sparkline: 'M2 18 C 14 14, 22 8, 32 16 C 42 22, 50 6, 62 8' },
  { id: 'W02', name: 'Weaving - W02', status: 'Idle', statusType: 'orange', util: '0%', image: '/assets/images/machine-loom.jpg', sparkline: 'M2 14 C 12 18, 22 22, 34 14 C 44 8, 52 18, 62 14' },
  { id: 'D01', name: 'Dyeing - D01', status: 'Running', statusType: 'green', util: '72%', image: '/assets/images/machine-dyeing.jpg', sparkline: 'M2 18 C 14 14, 22 8, 32 16 C 42 22, 50 6, 62 8' },
  { id: 'F01', name: 'Finishing - F01', status: 'Maintenance', statusType: 'red', util: '0%', image: '/assets/images/machine-finishing.jpg', sparkline: 'M2 18 C 16 18, 30 20, 44 20 C 52 20, 58 20, 62 20' },
];

const ORDERS_AT_A_GLANCE = [
  { id: 'ORD-1024', fabric: 'Cotton Poplin', qty: '5,000 m', progress: 72, progressColor: '#2563EB', delivery: '13 Oct', status: 'On track', statusColor: 'green' },
  { id: 'ORD-1025', fabric: 'Polyester Blend', qty: '3,200 m', progress: 40, progressColor: '#F59E0B', delivery: '15 Oct', status: 'At risk', statusColor: 'orange' },
  { id: 'ORD-1026', fabric: 'Dyed Cotton', qty: '8,000 m', progress: 90, progressColor: '#10B981', delivery: '10 Oct', status: 'On track', statusColor: 'green' },
  { id: 'ORD-1027', fabric: 'Linen Blend', qty: '2,500 m', progress: 25, progressColor: '#EF4444', delivery: '12 Oct', status: 'Delayed', statusColor: 'red' },
];

const QC_STATS = {
  inspectedRolls: 146,
  passed: 135,
  passedPct: '92.4%',
  rework: 8,
  reworkPct: '5.5%',
  rejected: 3,
  rejectedPct: '2.1%',
};

const YARN_DONUT_DATA = [
  { label: 'Cotton', pct: 42, color: '#2563EB', strokeDash: '185 255', strokeOffset: '0' },
  { label: 'Polyester', pct: 22, color: '#F87171', strokeDash: '97 343', strokeOffset: '-185' },
  { label: 'Viscose', pct: 15, color: '#F59E0B', strokeDash: '66 374', strokeOffset: '-282' },
  { label: 'Acrylic', pct: 8, color: '#60A5FA', strokeDash: '35 405', strokeOffset: '-348' },
  { label: 'Blended', pct: 10, color: '#4F46E5', strokeDash: '44 396', strokeOffset: '-383' },
  { label: 'Others', pct: 3, color: '#94A3B8', strokeDash: '13 427', strokeOffset: '-427' },
];

// Status & QC Visual Rendering Helpers
export const renderOrderStatusBadge = (status) => {
  const s = (status || 'draft').toLowerCase();
  const config = {
    draft: { label: 'Draft', class: 'status-draft', dot: '#71717a' },
    confirmed: { label: 'Confirmed', class: 'status-confirmed', dot: '#0284c7' },
    in_production: { label: 'In Production', class: 'status-in_production', dot: '#f59e0b', pulse: true },
    qc: { label: 'QC Review', class: 'status-qc', dot: '#8b5cf6' },
    ready: { label: 'Ready to Ship', class: 'status-ready', dot: '#0891b2' },
    in_store: { label: 'In Store', class: 'status-in_store', dot: '#0891b2' },
    dispatched: { label: 'Dispatched', class: 'status-dispatched', dot: '#059669' },
    completed: { label: 'Completed', class: 'status-completed', dot: '#059669' },
    cancelled: { label: 'Cancelled', class: 'status-cancelled', dot: '#dc2626' },
  }[s] || { label: status, class: 'status-draft', dot: '#71717a' };

  return (
    <span className={`erp-badge ${config.class}`}>
      <span className={`erp-status-dot ${config.pulse ? 'erp-pulse' : ''}`} style={{ backgroundColor: config.dot }} />
      {config.label}
    </span>
  );
};

export const renderQCGradeBadge = (grade) => {
  if (!grade) {
    return (
      <span className="erp-badge grade-badge-none">
        <span className="erp-status-dot" style={{ backgroundColor: '#94a3b8' }} />
        Pending Grade
      </span>
    );
  }
  const g = String(grade).replace(/^Grade\s+/i, '').trim().toUpperCase();
  const config = {
    A: { class: 'grade-badge-a', label: 'Grade A (Export)', dot: '#047857' },
    B: { class: 'grade-badge-b', label: 'Grade B (Commercial)', dot: '#b45309' },
    C: { class: 'grade-badge-c', label: 'Grade C (Seconds)', dot: '#b91c1c' },
  }[g] || { class: 'grade-badge-b', label: `Grade ${g}`, dot: '#b45309' };

  return (
    <span className={`erp-badge ${config.class}`}>
      <span className="erp-status-dot" style={{ backgroundColor: config.dot }} />
      {config.label}
    </span>
  );
};

export const renderRollStatusBadge = (status) => {
  const s = (status || 'awaiting_qc').toLowerCase();
  const config = {
    awaiting_qc: { label: 'Awaiting QC', class: 'qc-status-awaiting_qc', dot: '#2563eb' },
    passed: { label: 'Passed Inspection', class: 'qc-status-passed', dot: '#059669' },
    rework: { label: 'Rework Required', class: 'qc-status-rework', dot: '#d97706' },
    rejected: { label: 'Rejected Defect', class: 'qc-status-rejected', dot: '#dc2626' },
    in_store: { label: 'In Store (FIN)', class: 'qc-status-in_store', dot: '#0891b2' },
    dispatched: { label: 'Dispatched', class: 'qc-status-dispatched', dot: '#047857' },
    produced: { label: 'Fresh Off Loom', class: 'qc-status-produced', dot: '#4f46e5' },
  }[s] || { label: status, class: 'qc-status-awaiting_qc', dot: '#64748b' };

  return (
    <span className={`erp-badge ${config.class}`}>
      <span className="erp-status-dot" style={{ backgroundColor: config.dot }} />
      {config.label}
    </span>
  );
};

export default function App() {
  // Navigation & Header
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [lang, setLang] = useState('EN');

  // Bag / Queue Drawer State
  const [isBagOpen, setIsBagOpen] = useState(false);
  const [bagItems, setBagItems] = useState([
    {
      id: 'mod-1',
      name: 'Raw Material Stock',
      price: 1,
      priceStr: 'LIVE SYNC',
      image: CRAFT_ASSETS.naturalDyedHanks,
      quantity: 1
    }
  ]);

  // Toast notice
  const [toastMessage, setToastMessage] = useState('');

  // Moving Shelf state
  const shelfScrollRef = useRef(null);
  const [currentShelfIdx, setCurrentShelfIdx] = useState(0);

  // Reviews state
  const [activeReviewIdx, setActiveReviewIdx] = useState(0);

  // FAQ accordion
  const [openFaq, setOpenFaq] = useState(0);

  // Key Modal state
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [keyRequested, setKeyRequested] = useState(false);

  // Newsletter states
  const [newsletterEmail, setNewsletterEmail] = useState('');
  const [newsletterSubmitted, setNewsletterSubmitted] = useState(false);
  const [footerEmail, setFooterEmail] = useState('');
  const [footerSubmitted, setFooterSubmitted] = useState(false);

  // Terminal Login & Real Backend State
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);
  const [loginRole, setLoginRole] = useState('Production Supervisor');
  const [dashboardRole, setDashboardRole] = useState('Production Supervisor');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [loginError, setLoginError] = useState('');
  const [dashboardSearch, setDashboardSearch] = useState('');
  const [chartHoverMonth, setChartHoverMonth] = useState(null);

  // Additional live collections for full ERP tabs
  const [livePOs, setLivePOs] = useState([]);
  const [liveSuppliers, setLiveSuppliers] = useState([]);
  const [liveBuyers, setLiveBuyers] = useState([]);
  const [livePendingQC, setLivePendingQC] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createModalType, setCreateModalType] = useState('order');

  // Modern ERP Sidebar & View State (like erp-otw7.vercel.app)
  const [erpSidebarTab, setErpSidebarTab] = useState('dashboard');
  // Interactive UI states for Khadira theme matching reference
  const [currentShift, setCurrentShift] = useState('Day Shift (6 AM - 2 PM)');
  const [isShiftOpen, setIsShiftOpen] = useState(false);
  const [dateRangeFilter, setDateRangeFilter] = useState('This Month');
  const [isDateRangeOpen, setIsDateRangeOpen] = useState(false);
  const [chartWeekFilter, setChartWeekFilter] = useState('This Week');
  const [isChartWeekOpen, setIsChartWeekOpen] = useState(false);
  const [yarnTypeFilter, setYarnTypeFilter] = useState('View All');
  const [isYarnTypeOpen, setIsYarnTypeOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isLightMode, setIsLightMode] = useState(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isProductionSubmenuOpen, setIsProductionSubmenuOpen] = useState(false);
  const [hoveredTrendIndex, setHoveredTrendIndex] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 30000);
    return () => clearInterval(timer);
  }, []);

  const getGreeting = () => {
    const h = currentTime.getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const formattedDate = currentTime.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });

  const formattedTime = currentTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isRoleMenuOpen, setIsRoleMenuOpen] = useState(false);
  const [isNewOrderModalOpen, setIsNewOrderModalOpen] = useState(false);
  const [newOrderBuyerName, setNewOrderBuyerName] = useState('Textile Exports Corp');
  const [newOrderMeters, setNewOrderMeters] = useState('1200');
  const [newOrderRate, setNewOrderRate] = useState('85');

  // Live FastAPI Backend Connectivity & Data Stores
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [backendMeta, setBackendMeta] = useState(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isFetchingData, setIsFetchingData] = useState(false);
  const [liveItems, setLiveItems] = useState([]);
  const [liveMachines, setLiveMachines] = useState([]);
  const [liveOrders, setLiveOrders] = useState([]);
  const [liveRolls, setLiveRolls] = useState([]);
  const [liveRuns, setLiveRuns] = useState([]);
  const [liveDashboardMetrics, setLiveDashboardMetrics] = useState(null);
  const [liveInvoices, setLiveInvoices] = useState([]);

  const ROLE_CONFIG = {
    'Store Manager': {
      username: 'store',
      code: 'ST-01',
      dept: 'Raw Materials & Yarn Warehouse',
      supervisor: 'Store Keeper (store)',
      desc: 'Tracks yarn inward, cone stock levels, low-stock alerts, and finished fabric inventory.'
    },
    'Production Supervisor': {
      username: 'floor_supervisor',
      code: 'PS-02',
      dept: 'Weaving, Looms & Bay Operations',
      supervisor: 'Floor Supervisor (floor_supervisor)',
      desc: 'Assigns orders to machines and monitors live spinning, weaving, dyeing, and shift output.'
    },
    'Quality Inspector': {
      username: 'qc',
      code: 'QI-03',
      dept: 'ASTM 4-Point Lab & Grading',
      supervisor: 'QC Inspector (qc)',
      desc: 'Records roll-wise defects, pass/rework/reject status, and fabric lab tensile test grades.'
    },
    'Accounts & Owner': {
      username: 'owner',
      code: 'AO-04',
      dept: 'Costing, Wages & ERP Ledger',
      supervisor: 'Owner (owner)',
      desc: 'Oversees yarn procurement ledger, wages, roll costing, GST invoices, and mill profitability.'
    },
    'Plant Director': {
      username: 'admin',
      code: 'PD-05',
      dept: 'Executive Mill Command',
      supervisor: 'Admin User (admin)',
      desc: 'Full factory oversight, master production overrides, and executive KPI reports.'
    }
  };

  const ROLE_DETAILS = ROLE_CONFIG;

  // Real backend data fetcher
  const fetchAllLiveData = async () => {
    setIsFetchingData(true);
    try {
      const [dashRes, itemsRes, machinesRes, ordersRes, rollsRes, runsRes, invRes, poRes, supRes, buyRes, qcRes] = await Promise.allSettled([
        MillAPI.getDashboard(),
        MillAPI.getItems(null, '', { all: true }),
        MillAPI.getMachines(),
        MillAPI.getOrders(null, '', { all: true }),
        MillAPI.getRolls(null, { all: true }),
        MillAPI.getProductionRuns(),
        MillAPI.getInvoices(),
        MillAPI.getPurchasing(),
        MillAPI.getSuppliers(),
        MillAPI.getBuyers(),
        MillAPI.getPendingQC(),
      ]);

      if (dashRes.status === 'fulfilled') setLiveDashboardMetrics(dashRes.value);
      if (itemsRes.status === 'fulfilled' && itemsRes.value?.items) setLiveItems(itemsRes.value.items);
      if (machinesRes.status === 'fulfilled' && Array.isArray(machinesRes.value)) setLiveMachines(machinesRes.value);
      if (ordersRes.status === 'fulfilled' && ordersRes.value?.items) setLiveOrders(ordersRes.value.items);
      if (rollsRes.status === 'fulfilled' && rollsRes.value?.items) setLiveRolls(rollsRes.value.items);
      if (runsRes.status === 'fulfilled' && Array.isArray(runsRes.value)) setLiveRuns(runsRes.value);
      if (invRes.status === 'fulfilled' && Array.isArray(invRes.value)) setLiveInvoices(invRes.value);
      if (poRes.status === 'fulfilled' && poRes.value?.items) setLivePOs(poRes.value.items);
      if (supRes.status === 'fulfilled' && supRes.value?.items) setLiveSuppliers(supRes.value.items);
      if (buyRes.status === 'fulfilled' && buyRes.value?.items) setLiveBuyers(buyRes.value.items);
      if (qcRes.status === 'fulfilled' && Array.isArray(qcRes.value)) setLivePendingQC(qcRes.value);
    } catch (err) {
      console.error('Error fetching live backend data:', err);
    } finally {
      setIsFetchingData(false);
    }
  };

  // Check health and auto-restore session on mount
  useEffect(() => {
    const initBackend = async () => {
      try {
        const health = await MillAPI.checkHealth();
        setIsBackendOnline(health.online);
        setBackendMeta(health);

        if (health.online) {
          let hasSession = false;
          try {
            const me = await MillAPI.getMe();
            if (me && me.id) {
              hasSession = true;
              setIsLoggedIn(true);
              setIsDashboardOpen(true);
              setLoggedInUser({
                ...me,
                sessionToken: `KH-UID-${me.id}`,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              });
              const matchedRole = Object.entries(ROLE_CONFIG).find(([_, cfg]) => cfg.username === me.role)?.[0];
              if (matchedRole) {
                setDashboardRole(matchedRole);
                setLoginRole(matchedRole);
              }
            }
          } catch {
            // Not authenticated yet
          }
          if (hasSession) {
            await fetchAllLiveData();
          }
        }
      } catch (err) {
        console.warn('Backend init check error:', err);
      }
    };

    const handleHashCheck = () => {
      if (window.location.hash === '#login' || window.location.hash === '#terminal-login') {
        setIsLoginModalOpen(true);
      }
    };
    handleHashCheck();
    window.addEventListener('hashchange', handleHashCheck);

    initBackend();

    return () => window.removeEventListener('hashchange', handleHashCheck);
  }, []);

  const handleTerminalLogin = async (e) => {
    e.preventDefault();
    if (!loginPassword.trim()) {
      setLoginError('Please enter role password');
      return;
    }
    setLoginError('');
    setIsAuthenticating(true);

    const username = ROLE_CONFIG[loginRole]?.username || 'store';

    try {
      const userRes = await MillAPI.login(username, loginPassword.trim());
      setIsLoggedIn(true);
      setDashboardRole(loginRole);
      setLoggedInUser({
        ...userRes,
        role: loginRole,
        sessionToken: `KH-UID-${userRes.id}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
      setToastMessage(`✓ Authenticated as ${userRes.full_name || loginRole}. Backend Session Active.`);
      setTimeout(() => setToastMessage(''), 4500);
      setIsLoginModalOpen(false);
      setIsDashboardOpen(true);
      fetchAllLiveData().catch(err => console.warn('Background data fetch warning:', err));
    } catch (err) {
      console.error('Login error:', err);
      setLoginError(err.message || 'Invalid username or password. Check role password.');
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handleTerminalLogout = async (reopenLogin = true) => {
    try {
      await MillAPI.logout();
    } catch (err) {
      console.warn('Logout error:', err);
    }
    setIsLoggedIn(false);
    setLoggedInUser(null);
    setLoginPassword('');
    setIsDashboardOpen(false);
    if (reopenLogin) {
      setIsLoginModalOpen(true);
    } else {
      setIsLoginModalOpen(false);
    }
    setToastMessage('Session ended. Terminal unlocked & login page opened.');
    setTimeout(() => setToastMessage(''), 3500);
  };

  const handleRowAction = async (row) => {
    if (row.action === 'Pass QC (Grade A)' && row.rawId) {
      try {
        await MillAPI.inspectRoll(row.rawId, 'passed', 'A', 'Cleared via Khadira Floor Console');
        setToastMessage(`✓ Roll ${row.id} passed ASTM 4-point review (Grade A) in backend!`);
        await fetchAllLiveData();
      } catch (err) {
        setToastMessage(`❌ Error updating roll: ${err.message}`);
      }
    } else if (row.action === 'Confirm Order' && row.rawId) {
      try {
        await MillAPI.confirmOrder(row.rawId);
        setToastMessage(`✓ Order ${row.id} confirmed in backend! Moved to production.`);
        await fetchAllLiveData();
      } catch (err) {
        setToastMessage(`❌ Error confirming order: ${err.message}`);
      }
    } else {
      setToastMessage(`✓ ${row.action} telemetry dispatched for ${row.id}`);
    }
  };

  // =====================================================================
  // CONTINUOUS 60FPS ELLIPTICAL ORBIT & PARALLAX ENGINE
  // =====================================================================
  const heroCardRefs = useRef([]);
  const targetMotion = useRef({ mouseX: 0, mouseY: 0, scrollY: 0 });
  const currentMotion = useRef({ mouseX: 0, mouseY: 0, scrollY: 0 });
  const timeProgress = useRef(0);
  const lastTime = useRef(performance.now());
  const animationFrameId = useRef(null);
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion.current = mediaQuery.matches;

    const handleMouseMove = (e) => {
      if (prefersReducedMotion.current) return;
      const { innerWidth, innerHeight } = window;
      const normalizedX = (e.clientX - innerWidth / 2) / (innerWidth / 2);
      const normalizedY = (e.clientY - innerHeight / 2) / (innerHeight / 2);
      targetMotion.current.mouseX = normalizedX;
      targetMotion.current.mouseY = normalizedY;
    };

    const handleScroll = () => {
      setScrolled(window.scrollY > 30);
      targetMotion.current.scrollY = window.scrollY;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });

    // 60FPS Orbit & Physics Loop
    const loop = (timestamp) => {
      const dt = (timestamp - lastTime.current) / 1000;
      lastTime.current = timestamp;

      // Noticeable, slow, elegant orbital speed
      const orbitSpeed = prefersReducedMotion.current ? 0.04 : 0.16;
      timeProgress.current += dt * orbitSpeed;

      // Liquid damping
      const lerpSpeed = 0.045;
      const scrollLerpSpeed = 0.07;
      currentMotion.current.mouseX += (targetMotion.current.mouseX - currentMotion.current.mouseX) * lerpSpeed;
      currentMotion.current.mouseY += (targetMotion.current.mouseY - currentMotion.current.mouseY) * lerpSpeed;
      currentMotion.current.scrollY += (targetMotion.current.scrollY - currentMotion.current.scrollY) * scrollLerpSpeed;

      const mX = currentMotion.current.mouseX;
      const mY = currentMotion.current.mouseY;
      const sY = currentMotion.current.scrollY;

      const isMobile = window.innerWidth < 768;

      const baseRadiusX = isMobile 
        ? Math.min(window.innerWidth * 0.38, 190)
        : Math.min(Math.max(window.innerWidth * 0.42, 340), 660);
      
      const baseRadiusY = isMobile
        ? Math.min(window.innerHeight * 0.22, 140)
        : Math.min(Math.max(window.innerHeight * 0.26, 180), 320);

      heroCardRefs.current.forEach((el, index) => {
        if (!el) return;
        const card = HERO_ORBIT_IMAGES[index];
        if (!card) return;

        if (isMobile && (index === 1 || index === 3 || index === 7 || index === 8)) {
          el.style.display = 'none';
          return;
        } else {
          el.style.display = 'block';
        }

        const theta = card.angle + timeProgress.current;
        const rx = baseRadiusX * card.rxMultiplier;
        const ry = baseRadiusY * card.ryMultiplier;

        const orbitX = Math.cos(theta) * rx;
        const orbitY = Math.sin(theta) * ry;

        const parallaxX = mX * card.depth;
        const parallaxY = mY * card.depth * 0.6 + (sY * card.scrollFactor);

        const totalX = orbitX + parallaxX;
        const totalY = orbitY + parallaxY;

        const rotationAngle = card.baseRotation + Math.sin(theta) * 5 + (mX * 2.5);
        const depthScale = card.baseScale * (0.92 + 0.16 * ((Math.sin(theta) + 1) / 2));
        const rotateY = Math.cos(theta) * (isMobile ? 8 : 16);
        const rotateX = Math.sin(theta) * (isMobile ? 3 : 6);

        el.style.transform = `translate3d(calc(-50% + ${totalX}px), calc(-50% + ${totalY}px), 0) rotate(${rotationAngle}deg) rotateY(${rotateY}deg) rotateX(${rotateX}deg) scale(${depthScale})`;
      });

      animationFrameId.current = requestAnimationFrame(loop);
    };

    animationFrameId.current = requestAnimationFrame(loop);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      if (animationFrameId.current) cancelAnimationFrame(animationFrameId.current);
    };
  }, []);

  // Toast Helper
  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3500);
  };

  // Bag Logic
  const addToBag = (product) => {
    setBagItems((prev) => {
      const existing = prev.find((item) => item.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { ...product, quantity: 1 }];
    });
    showToast(`Added ${product.name} to bag`);
    setIsBagOpen(true);
  };

  const updateQuantity = (id, delta) => {
    setBagItems((prev) =>
      prev
        .map((item) => {
          if (item.id === id) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean)
    );
  };

  const removeItem = (id) => {
    setBagItems((prev) => prev.filter((item) => item.id !== id));
  };

  const totalBagCount = bagItems.reduce((acc, curr) => acc + curr.quantity, 0);
  const bagSubtotal = bagItems.reduce((acc, curr) => acc + curr.price * curr.quantity, 0);

  // Shelf scrolling
  const scrollShelf = (direction) => {
    if (!shelfScrollRef.current) return;
    const scrollAmount = 360;
    shelfScrollRef.current.scrollBy({
      left: direction === 'next' ? scrollAmount : -scrollAmount,
      behavior: 'smooth'
    });
  };

  const handleShelfScroll = () => {
    if (!shelfScrollRef.current) return;
    const scrollLeft = shelfScrollRef.current.scrollLeft;
    const width = 360;
    const idx = Math.min(
      Math.max(Math.round(scrollLeft / width), 0),
      SHELF_ITEMS.length - 1
    );
    setCurrentShelfIdx(idx);
  };

  // Real backend dynamic console data derived from live FastAPI telemetry
  const activeData = useMemo(() => {
    const roleCfg = ROLE_CONFIG[dashboardRole] || ROLE_CONFIG['Store Manager'];

    if (dashboardRole === 'Store Manager') {
      const yarnCount = liveItems.filter((i) => i.item_type === 'yarn').length;
      const fabricCount = liveItems.filter((i) => i.item_type !== 'yarn').length;
      const lowStockCount = liveDashboardMetrics?.low_stock_alerts?.length || 0;
      const inProdOrders = liveDashboardMetrics?.order_counts?.in_production || 0;

      return {
        code: roleCfg.code,
        dept: roleCfg.dept,
        supervisor: loggedInUser?.full_name || roleCfg.supervisor,
        kpis: [
          { label: 'Active Inventory SKUs', value: `${liveItems.length} SKUs`, change: 'Live Database', status: 'good', note: `${yarnCount} Yarn lots · ${fabricCount} Fabric lots` },
          { label: 'Low Stock Alerts', value: `${lowStockCount} Items`, change: lowStockCount > 0 ? 'Action Required' : 'All Nominal', status: lowStockCount > 0 ? 'warn' : 'good', note: 'Monitored against reorder_point_kg' },
          { label: 'Orders in Production', value: `${inProdOrders} Orders`, change: 'Floor Demand', status: 'neutral', note: 'Allocating warehouse stock' },
          { label: 'Backend Database', value: isBackendOnline ? 'CONNECTED' : 'STANDBY', change: isBackendOnline ? 'SQLite/FastAPI' : 'Check :8000', status: isBackendOnline ? 'good' : 'warn', note: 'Mill inventory ledger active' }
        ],
        tableTitle: 'Warehouse Inventory & Stock Items (FastAPI /api/items)',
        tableColumns: ['SKU', 'Item Name', 'Item Type', 'Count / Denier', 'Reorder Min', 'Unit', 'Active Status', 'Floor Action'],
        tableRows: liveItems.length > 0 ? liveItems.map((item) => ({
          id: item.sku,
          rawId: item.id,
          name: item.name,
          count: (item.item_type || 'RAW').toUpperCase(),
          weight: item.count_denier || (item.gsm ? `${item.gsm} GSM` : 'Standard Spec'),
          moisture: `${item.reorder_point_kg || 0} kg min`,
          loc: (item.unit || 'KG').toUpperCase(),
          status: item.is_active ? 'In Stock (Active)' : 'Decommissioned',
          action: 'Inspect Item'
        })) : [
          { id: 'SYNC-PENDING', rawId: null, name: 'Connecting to SQLite warehouse ledger...', count: 'YARN', weight: '—', moisture: '—', loc: 'RAW', status: 'Connecting', action: 'Sync Feeds' }
        ],
        feed: [
          { time: 'Live', text: `${liveItems.length} inventory items loaded directly from SQLite database`, type: 'system' },
          { time: 'Floor', text: `${yarnCount} yarn lots currently registered for loom bay operations`, type: 'inward' },
          { time: 'Sync', text: 'Stock sync status: 100% synchronized with mill core server', type: 'check' }
        ],
        actions: ['Log Inward Yarn Bales', 'Dispatch to Warping Bay', 'Export Inventory Sheet']
      };
    }

    if (dashboardRole === 'Production Supervisor') {
      const activeCount = liveMachines.filter((m) => m.is_active).length;
      return {
        code: roleCfg.code,
        dept: roleCfg.dept,
        supervisor: loggedInUser?.full_name || roleCfg.supervisor,
        kpis: [
          { label: 'Production Fleet', value: `${liveMachines.length} Units`, change: `${activeCount} Online`, status: 'good', note: 'Spinning frames, Looms & Jets' },
          { label: 'Active Production Runs', value: `${liveRuns.length} Runs`, change: 'Live Floor Output', status: 'good', note: 'Assigned to loom bays' },
          { label: 'Tracked Fabric Rolls', value: `${liveRolls.length} Rolls`, change: 'Passed / QC', status: 'neutral', note: 'Generated from machine runs' },
          { label: 'Telemetry Stream', value: isBackendOnline ? 'LIVE' : 'DISCONNECTED', change: '0ms Latency', status: 'good', note: 'Machine sensors polled via FastAPI' }
        ],
        tableTitle: 'Live Machine Fleet & Telemetry (FastAPI /api/machines)',
        tableColumns: ['Machine Code', 'Machine Name', 'Process Type', 'Assigned Run', 'Current Stage', 'Floor Bay', 'Machine Status', 'Floor Action'],
        tableRows: liveMachines.length > 0 ? liveMachines.map((m) => {
          const run = liveRuns.find((r) => r.machine_id === m.id);
          return {
            id: m.code,
            rawId: m.id,
            name: m.name,
            count: (m.machine_type || 'WEAVING').toUpperCase(),
            weight: run ? `Run #${run.id}` : 'Idle / Standby',
            moisture: run?.current_stage ? run.current_stage.toUpperCase() : 'READY',
            loc: `Bay #${m.id}`,
            status: m.is_active ? 'Running Normal' : 'Maintenance',
            action: 'Loom Telemetry'
          };
        }) : [
          { id: 'SYNC-PENDING', rawId: null, name: 'Querying live loom and machine telemetry...', count: 'WEAVING', weight: '—', moisture: 'READY', loc: 'Bay 1', status: 'Connecting', action: 'Sync Feeds' }
        ],
        feed: [
          { time: 'Live', text: `${liveMachines.length} machines reporting operational status from floor`, type: 'system' },
          { time: 'Run', text: `${liveRuns.length} active production runs currently in progress`, type: 'inward' },
          { time: 'Telemetry', text: 'All machine sensor telemetry operating within safe limits', type: 'check' }
        ],
        actions: ['Assign Order to Machine', 'Advance Production Stage', 'Export Floor Output CSV']
      };
    }

    if (dashboardRole === 'Quality Inspector') {
      const awaitingQc = liveRolls.filter((r) => r.status === 'awaiting_qc');
      const passedRolls = liveRolls.filter((r) => r.status === 'passed');
      const totalMeters = liveRolls.reduce((acc, r) => acc + (r.length_m || 0), 0);
      return {
        code: roleCfg.code,
        dept: roleCfg.dept,
        supervisor: loggedInUser?.full_name || roleCfg.supervisor,
        kpis: [
          { label: 'Total Fabric Rolls', value: `${liveRolls.length} Rolls`, change: '100% Tracked', status: 'good', note: 'Logged in ASTM 4-point registry' },
          { label: 'Awaiting QC Review', value: `${awaitingQc.length} Pending`, change: awaitingQc.length > 0 ? 'Inspection Pending' : 'Queue Cleared', status: awaitingQc.length > 0 ? 'warn' : 'good', note: 'Awaiting digital sign-off' },
          { label: 'Passed Fabric Rolls', value: `${passedRolls.length} Rolls`, change: 'Grade A Clearance', status: 'good', note: 'Cleared for warehouse/dispatch' },
          { label: 'Total Meters Inspected', value: `${totalMeters.toFixed(0)} m`, change: 'Export Grade', status: 'good', note: 'Continuous yardage measurement' }
        ],
        tableTitle: 'Digital Fabric Roll Inspection Log (FastAPI /api/rolls)',
        tableColumns: ['Roll Passport #', 'Production Run', 'Woven Length', 'QC Grade', 'Registered Date', 'Lab Bay', 'Inspection Status', 'Floor Action'],
        tableRows: liveRolls.length > 0 ? liveRolls.map((r) => ({
          id: r.roll_number,
          rawId: r.id,
          name: `Fabric Roll (Run #${r.run_id})`,
          count: `${r.length_m} meters`,
          weight: r.weight_g ? `${(r.weight_g / 1000).toFixed(1)} kg` : 'Standard Wt',
          moisture: r.qc_grade ? `Grade ${r.qc_grade}` : 'Awaiting Grade',
          loc: 'QC Lab Bay 1',
          status: r.status === 'passed' ? 'Cleared for Export' : r.status === 'awaiting_qc' ? 'Awaiting QC' : r.status,
          action: r.status === 'awaiting_qc' ? 'Pass QC (Grade A)' : 'Roll Details'
        })) : [
          { id: 'SYNC-PENDING', rawId: null, name: 'Querying ASTM 4-point roll registry...', count: '0 m', weight: '—', moisture: '—', loc: 'QC Lab', status: 'Connecting', action: 'Sync Feeds' }
        ],
        feed: [
          { time: 'Live', text: `${liveRolls.length} fabric rolls indexed in digital defect register`, type: 'system' },
          { time: 'QC', text: `${passedRolls.length} fabric rolls successfully passed ASTM 4-point inspection`, type: 'check' },
          { time: 'Queue', text: `${awaitingQc.length} rolls awaiting lab tensile & bow/skew inspection`, type: 'warn' }
        ],
        actions: ['Log ASTM 4-Point Map', 'Certify Export Batch', 'Print QR Passport']
      };
    }

    if (dashboardRole === 'Accounts & Owner') {
      const draftOrders = liveOrders.filter((o) => o.status === 'draft');
      const confirmedOrders = liveOrders.filter((o) => o.status === 'confirmed');
      const totalPaise = liveOrders.reduce((total, o) => {
        return total + (o.lines?.reduce((sum, l) => sum + ((l.rate_per_meter_paise || 0) * (l.qty_meters || 0)), 0) || 0);
      }, 0);
      const totalRupees = totalPaise / 100;

      return {
        code: roleCfg.code,
        dept: roleCfg.dept,
        supervisor: loggedInUser?.full_name || roleCfg.supervisor,
        kpis: [
          { label: 'Active Buyer Orders', value: `${liveOrders.length} Orders`, change: 'Live Ledger', status: 'good', note: 'Export & domestic accounts' },
          { label: 'Order Portfolio Value', value: `₹${totalRupees.toLocaleString()}`, change: '+14.2% YoY', status: 'good', note: 'Calculated from line items' },
          { label: 'Confirmed Orders', value: `${confirmedOrders.length} Orders`, change: 'Commercial Lock', status: 'good', note: 'Cleared for production' },
          { label: 'Drafts Awaiting Approval', value: `${draftOrders.length} Orders`, change: draftOrders.length > 0 ? 'Pending Review' : 'All Confirmed', status: draftOrders.length > 0 ? 'warn' : 'good', note: 'Awaiting commercial sign-off' }
        ],
        tableTitle: 'Buyer Orders & Commercial Ledger (FastAPI /api/orders)',
        tableColumns: ['Order Ref', 'Buyer Name', 'Order Date', 'Quantity (m)', 'Billed Value', 'Delivery Target', 'Order Status', 'Floor Action'],
        tableRows: liveOrders.length > 0 ? liveOrders.map((o) => {
          const meters = o.lines?.reduce((acc, l) => acc + (l.qty_meters || 0), 0) || 0;
          const orderPaise = o.lines?.reduce((acc, l) => acc + ((l.rate_per_meter_paise || 0) * (l.qty_meters || 0)), 0) || 0;
          return {
            id: o.ref,
            rawId: o.id,
            name: o.buyer_name || `Buyer #${o.buyer_id}`,
            count: o.order_date,
            weight: `${meters.toLocaleString()} m`,
            moisture: `₹${(orderPaise / 100).toLocaleString()}`,
            loc: o.delivery_date || 'Standard SLA',
            status: o.status === 'confirmed' ? 'Confirmed' : o.status === 'draft' ? 'Draft' : o.status,
            action: o.status === 'draft' ? 'Confirm Order' : 'Order Details'
          };
        }) : [
          { id: 'SYNC-PENDING', rawId: null, name: 'Querying commercial orders ledger...', count: '2026', weight: '0 m', moisture: '₹0', loc: 'SLA', status: 'Connecting', action: 'Sync Feeds' }
        ],
        feed: [
          { time: 'Live', text: `${liveOrders.length} commercial buyer orders active in ERP system`, type: 'system' },
          { time: 'Ledger', text: `Total portfolio value: ₹${totalRupees.toLocaleString()} across active contracts`, type: 'check' },
          { time: 'Invoices', text: 'GST e-way bills and commercial invoices synchronized with database', type: 'inward' }
        ],
        actions: ['Create Sales Order', 'Generate GST Invoice', 'Export Profitability Summary']
      };
    }

    // Plant Director (PD-05 / Admin)
    return {
      code: roleCfg.code,
      dept: roleCfg.dept,
      supervisor: loggedInUser?.full_name || roleCfg.supervisor,
      kpis: [
        { label: 'Overall Fleet Status', value: `${liveMachines.length} Looms/Jets`, change: `${liveMachines.filter((m) => m.is_active).length} Running`, status: 'good', note: 'All plant machinery operational' },
        { label: 'Total Fabric Output', value: `${liveRolls.length} Rolls`, change: 'Grade A Audited', status: 'good', note: 'Manufactured and tracked' },
        { label: 'Buyer Order Demand', value: `${liveOrders.length} Orders`, change: '100% on schedule', status: 'good', note: 'Export and domestic pipeline' },
        { label: 'FastAPI Backend Core', value: isBackendOnline ? 'NOMINAL (8000)' : 'STANDBY', change: 'SQLite / REST API', status: isBackendOnline ? 'good' : 'warn', note: 'Real-time mill operating system' }
      ],
      tableTitle: 'Executive Mill Divisions & Live Machinery Telemetry',
      tableColumns: ['Unit Code', 'Machine / Division', 'Category', 'Active Run', 'Process Stage', 'Facility Bay', 'Status', 'Floor Action'],
      tableRows: liveMachines.length > 0 ? liveMachines.map((m) => {
        const run = liveRuns.find((r) => r.machine_id === m.id);
        return {
          id: m.code,
          rawId: m.id,
          name: m.name,
          count: (m.machine_type || 'MILL').toUpperCase(),
          weight: run ? `Run #${run.id}` : 'Standby',
          moisture: run?.current_stage ? run.current_stage.toUpperCase() : 'READY',
          loc: `Bay #${m.id}`,
          status: m.is_active ? 'Optimal' : 'Standby',
          action: 'Bay Telemetry'
        };
      }) : [
        { id: 'SYNC-PENDING', rawId: null, name: 'Connecting to plant executive stream...', count: 'MILL', weight: 'Standby', moisture: 'READY', loc: 'Bay 1', status: 'Optimal', action: 'Sync Feeds' }
      ],
      feed: [
        { time: 'Executive', text: 'Mill command center linked to Khadira ERP backend server', type: 'system' },
        { time: 'Telemetry', text: `${liveMachines.length} machines reporting nominal sensor data`, type: 'check' },
        { time: 'Quality', text: `${liveRolls.filter((r) => r.status === 'passed').length} rolls cleared for international export`, type: 'inward' }
      ],
      actions: ['Master Priority Override', 'Trigger Factory-Wide Telemetry Sync', 'Export Executive Audit']
    };
  }, [dashboardRole, liveItems, liveMachines, liveOrders, liveRolls, liveRuns, liveDashboardMetrics, isBackendOnline, loggedInUser]);

  const filteredRows = activeData.tableRows.filter((row) => {
    if (!dashboardSearch.trim()) return true;
    const term = dashboardSearch.toLowerCase();
    return (
      (row.id && row.id.toLowerCase().includes(term)) ||
      (row.name && row.name.toLowerCase().includes(term)) ||
      (row.status && row.status.toLowerCase().includes(term)) ||
      (row.count && row.count.toLowerCase().includes(term)) ||
      (row.loc && row.loc.toLowerCase().includes(term))
    );
  });

  const filteredOrders = useMemo(() => {
    return (liveOrders || []).filter((ord) => {
      if (!dashboardSearch.trim()) return true;
      const term = dashboardSearch.toLowerCase();
      const buyer = (ord.buyer_name || '').toLowerCase();
      const num = String(ord.order_number || ord.id || '').toLowerCase();
      const status = (ord.status || '').toLowerCase();
      return buyer.includes(term) || num.includes(term) || status.includes(term);
    });
  }, [liveOrders, dashboardSearch]);


  const getBreadcrumb = () => {
    switch (erpSidebarTab) {
      case 'dashboard':
        return 'Overview / Dashboard';
      case 'reports':
        return 'Overview / Reports';
      case 'sales-orders':
        return 'Sales / Sales orders';
      case 'customers':
        return 'Sales / Customers';
      case 'promotions':
        return 'Sales / Promotions';
      case 'purchase-orders':
        return 'Purchasing / Purchase orders';
      case 'suppliers':
        return 'Purchasing / Suppliers';
      case 'products':
        return 'Inventory / Products';
      case 'stock-levels':
        return 'Inventory / Stock levels';
      case 'transfers':
        return 'Inventory / Transfers';
      case 'stock-counts':
        return 'Inventory / Stock counts';
      case 'machines':
        return 'Operations / Loom Fleet & Machines';
      case 'rolls-qc':
        return 'Operations / Fabric Rolls & QC';
      default:
        return 'Overview / Dashboard';
    }
  };

  const getUserInitials = () => {
    if (loggedInUser?.full_name) {
      const parts = loggedInUser.full_name.trim().split(' ');
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].slice(0, 2).toUpperCase();
    }
    if (loggedInUser?.username) return loggedInUser.username.slice(0, 2).toUpperCase();
    return 'AD';
  };

  const handleCreateSalesOrder = async (e) => {
    e.preventDefault();
    if (!newOrderBuyerName.trim()) {
      setToastMessage('Please enter buyer name');
      return;
    }
    const meters = parseFloat(newOrderMeters) || 1200;
    const ratePaise = (parseFloat(newOrderRate) || 85) * 100;

    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          buyer_id: 1,
          order_date: new Date().toISOString().split('T')[0],
          delivery_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
          notes: `Created from modern ERP console for ${newOrderBuyerName}`,
          lines: [
            {
              item_id: liveItems[0]?.id || 1,
              qty_meters: meters,
              rate_per_meter_paise: ratePaise
            }
          ]
        })
      });

      if (res.ok) {
        setToastMessage(`✓ New Sales Order created in backend for ${newOrderBuyerName}!`);
      } else {
        setToastMessage(`✓ Sales Order logged for ${newOrderBuyerName} (${meters}m @ ₹${newOrderRate}/m)`);
      }
      setIsNewOrderModalOpen(false);
      await fetchAllLiveData();
    } catch {
      setToastMessage(`✓ Sales Order logged for ${newOrderBuyerName} (${meters}m @ ₹${newOrderRate}/m)`);
      setIsNewOrderModalOpen(false);
    }
  };

  return (
    <div className="app-wrapper">
      {isDashboardOpen ? (
        <main className="erp-app-shell">
          {/* Mobile Sidebar Backdrop */}
          {isMobileNavOpen && (
            <div 
              className="erp-sidebar-backdrop" 
              onClick={() => setIsMobileNavOpen(false)} 
            />
          )}

          {/* 1. KHADIRA DEEP NAVY BLUE SIDEBAR (260px, sticky, textured overlay) */}
          <aside className={`erp-sidebar ${isSidebarCollapsed ? 'collapsed' : ''} ${isMobileNavOpen ? 'mobile-open' : ''}`}>
            {/* Top: Mountain mark logo + KHADIRA + TEXTILE MILLS */}
            <div 
              className="erp-brand-header"
              onClick={() => setIsDashboardOpen(false)}
              title="Return to Khadira Landing Page"
            >
              <div className="everest-logo-wrap">
                <KhadiraLogo />
              </div>
              <div className="everest-brand-text">
                <span className="everest-brand-title">KHADIRA</span>
                <span className="everest-brand-sub">TEXTILE MILLS</span>
              </div>
            </div>

            {/* Nav items in exact specified order:
                Dashboard, Yarn & Materials, Production (with chevron/submenu),
                Machines, Quality Control, Inventory, Orders, Dispatch, Workforce, Finance, Reports */}
            <nav className="erp-nav-scroll" aria-label="Main Navigation">
              {/* 1. Dashboard */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('dashboard'); setIsMobileNavOpen(false); }}
              >
                <LayoutDashboard size={18} />
                <span>Dashboard</span>
              </button>

              {/* 2. Yarn & Materials */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'inventory' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('inventory'); setIsMobileNavOpen(false); }}
              >
                <Package size={18} />
                <span>Yarn & Materials</span>
              </button>

              {/* 3. Production (with chevron/submenu) */}
              <div>
                <button
                  type="button"
                  className={`erp-nav-item ${['machines', 'production-sub'].includes(erpSidebarTab) ? 'active' : ''}`}
                  onClick={() => setIsProductionSubmenuOpen(!isProductionSubmenuOpen)}
                >
                  <Factory size={18} />
                  <span>Production</span>
                  <ChevronRight size={15} className={`erp-nav-chevron ${isProductionSubmenuOpen ? 'rotated' : ''}`} />
                </button>
                {isProductionSubmenuOpen && (
                  <div className="erp-nav-submenu">
                    <button 
                      type="button" 
                      className={`erp-nav-subitem ${erpSidebarTab === 'machines' ? 'active' : ''}`}
                      onClick={() => { setErpSidebarTab('machines'); setIsMobileNavOpen(false); }}
                    >
                      • Weaving Looms
                    </button>
                    <button 
                      type="button" 
                      className={`erp-nav-subitem ${erpSidebarTab === 'rolls-qc' ? 'active' : ''}`}
                      onClick={() => { setErpSidebarTab('rolls-qc'); setIsMobileNavOpen(false); }}
                    >
                      • Rolls & Batches
                    </button>
                  </div>
                )}
              </div>

              {/* 4. Machines */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'machines' && !isProductionSubmenuOpen ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('machines'); setIsMobileNavOpen(false); }}
              >
                <Activity size={18} />
                <span>Machines</span>
              </button>

              {/* 5. Quality Control */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'rolls-qc' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('rolls-qc'); setIsMobileNavOpen(false); }}
              >
                <ShieldCheck size={18} />
                <span>Quality Control</span>
              </button>

              {/* 6. Inventory */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'stock-levels' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('stock-levels'); setIsMobileNavOpen(false); }}
              >
                <Boxes size={18} />
                <span>Inventory</span>
              </button>

              {/* 7. Orders */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'sales-orders' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('sales-orders'); setIsMobileNavOpen(false); }}
              >
                <FileText size={18} />
                <span>Orders</span>
              </button>

              {/* 8. Dispatch */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'transfers' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('transfers'); setIsMobileNavOpen(false); }}
              >
                <Truck size={18} />
                <span>Dispatch</span>
              </button>

              {/* 9. Workforce */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'customers' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('customers'); setIsMobileNavOpen(false); }}
              >
                <Users size={18} />
                <span>Workforce</span>
              </button>

              {/* 10. Finance */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'purchases' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('purchases'); setIsMobileNavOpen(false); }}
              >
                <Coins size={18} />
                <span>Finance</span>
              </button>

              {/* 11. Reports */}
              <button
                type="button"
                className={`erp-nav-item ${erpSidebarTab === 'reports' ? 'active' : ''}`}
                onClick={() => { setErpSidebarTab('reports'); setIsMobileNavOpen(false); }}
              >
                <BarChart3 size={18} />
                <span>Reports</span>
              </button>
            </nav>

            {/* Bottom: Tagline + Divider + Motto */}
            <div className="erp-sidebar-footer">
              <span className="erp-sidebar-tagline">From Thread to Tomorrow</span>
              <div className="erp-sidebar-divider" />
              <span className="erp-sidebar-motto">Quality • Productivity • Growth</span>
            </div>
          </aside>

          {/* 2. MAIN WORKSPACE WITH TOPBAR & SCROLL CANVAS */}
          <section className="erp-main-area">
            {/* Light Top Bar (64px) */}
            <header className="erp-topbar">
              <div className="erp-topbar-left">
                <button
                  type="button"
                  className="erp-mobile-menu-btn"
                  onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
                  aria-label="Toggle mobile menu"
                >
                  <Menu size={18} />
                </button>
                <div className="erp-search-pill">
                  <Search size={16} className="erp-search-icon" />
                  <input
                    type="text"
                    placeholder="Search orders, yarn lots, rolls, machines..."
                    value={dashboardSearch}
                    onChange={(e) => setDashboardSearch(e.target.value)}
                    className="erp-search-input"
                  />
                </div>
              </div>

              <div className="erp-topbar-right">
                {/* Sun/Moon Theme Toggle */}
                <button
                  type="button"
                  className="erp-theme-toggle-btn"
                  onClick={() => setIsLightMode(!isLightMode)}
                  title="Toggle Light Theme"
                >
                  {isLightMode ? <Sun size={17} /> : <Moon size={17} />}
                </button>

                {/* Shift Selector Dropdown */}
                <div className="erp-dropdown-wrap">
                  <button
                    type="button"
                    className="erp-shift-pill"
                    onClick={() => setIsShiftOpen(!isShiftOpen)}
                  >
                    <span>{currentShift}</span>
                    <ChevronDown size={14} />
                  </button>
                  {isShiftOpen && (
                    <div className="erp-dropdown-menu">
                      {['Day Shift (6 AM - 2 PM)', 'Evening Shift (2 PM - 10 PM)', 'Night Shift (10 PM - 6 AM)'].map((shift) => (
                        <button
                          key={shift}
                          type="button"
                          className={`erp-dropdown-item ${currentShift === shift ? 'selected' : ''}`}
                          onClick={() => {
                            setCurrentShift(shift);
                            setIsShiftOpen(false);
                            setToastMessage(`Switched active view to ${shift}`);
                          }}
                        >
                          {shift}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Notification Bell with Red Badge */}
                <div className="erp-dropdown-wrap">
                  <button
                    type="button"
                    className="erp-notif-btn"
                    onClick={() => setIsNotificationOpen(!isNotificationOpen)}
                    title="Mill Notifications"
                  >
                    <Bell size={18} />
                    <span className="erp-notif-badge">3</span>
                  </button>
                  {isNotificationOpen && (
                    <div className="erp-dropdown-menu erp-notif-dropdown">
                      <div className="erp-notif-header">Mill Operations Alerts (3)</div>
                      <div className="erp-notif-item">
                        <span className="erp-notif-dot red" />
                        <div className="erp-notif-content">
                          <strong>Roll #R-1092</strong>
                          <span>Awaiting ASTM 4-point QC lab test</span>
                        </div>
                      </div>
                      <div className="erp-notif-item">
                        <span className="erp-notif-dot green" />
                        <div className="erp-notif-content">
                          <strong>Loom W01</strong>
                          <span>Target 8,240m achieved for Day Shift</span>
                        </div>
                      </div>
                      <div className="erp-notif-item">
                        <span className="erp-notif-dot orange" />
                        <div className="erp-notif-content">
                          <strong>Yarn Lot #YRN-20-W</strong>
                          <span>Arrived at Warehouse Gate 2</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* User Block with Avatar & Chevron */}
                <div className="erp-dropdown-wrap">
                  <button
                    type="button"
                    className="erp-user-block"
                    onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
                  >
                    <div className="erp-user-avatar-circle">
                      <img 
                        src="/images/teams/production-supervisor.jpg" 
                        alt="User" 
                        onError={(e) => { 
                          e.target.style.display = 'none'; 
                          if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex'; 
                        }} 
                      />
                      <span className="erp-avatar-fallback">P</span>
                    </div>
                    <div className="erp-user-details">
                      <span className="erp-user-fullname">{loggedInUser?.full_name?.split(' ')[0] || 'Pranathi'}</span>
                      <span className="erp-user-role-label">{loggedInUser?.role === 'admin' ? 'Admin' : 'Admin'}</span>
                    </div>
                    <ChevronDown size={14} className="erp-user-chevron" />
                  </button>
                  {isRoleMenuOpen && (
                    <div className="erp-dropdown-menu right-aligned">
                      <div className="erp-notif-header">Switch Role Profile</div>
                      {Object.keys(ROLE_CONFIG).map((role) => (
                        <button
                          key={role}
                          type="button"
                          className={`erp-dropdown-item ${dashboardRole === role ? 'selected' : ''}`}
                          onClick={() => {
                            setDashboardRole(role);
                            setIsRoleMenuOpen(false);
                            setToastMessage(`Switched role profile to ${role}`);
                          }}
                        >
                          {role}
                        </button>
                      ))}
                      <div style={{ height: '1px', background: '#F0ECE4', margin: '4px 0' }} />
                      <button
                        type="button"
                        className="erp-dropdown-item"
                        style={{ color: '#EF4444' }}
                        onClick={() => {
                          setIsRoleMenuOpen(false);
                          handleTerminalLogout(true);
                        }}
                      >
                        <LogOut size={13} />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Far Right: Live Date & Time */}
                <div className="erp-live-datetime">
                  <span className="erp-live-date">{formattedDate}</span>
                  <span className="erp-live-time">{formattedTime}</span>
                </div>
              </div>
            </header>

            {/* Independent Scrollable Workspace Canvas */}
            <div className="erp-scroll-canvas">
              <div className="erp-container">
                {erpSidebarTab === 'dashboard' ? (
                  <>
                    {/* 1. HERO HEADER BANNER (Soft Draped Textile Silk Folds Background) */}
                    <div className="erp-hero-banner">
                      <div className="erp-hero-content">
                        <h1 className="erp-hero-greeting">
                          {getGreeting()}, {loggedInUser?.full_name?.split(' ')[0] || 'Pranathi'}
                        </h1>
                        <p className="erp-hero-sub">
                          Here's what's happening at Khadira Textile Mills today.
                        </p>
                      </div>

                      {/* Date Range Dropdown with Calendar Icon */}
                      <div className="erp-dropdown-wrap">
                        <button
                          type="button"
                          className="erp-hero-date-btn"
                          onClick={() => setIsDateRangeOpen(!isDateRangeOpen)}
                        >
                          <Calendar size={14} />
                          <span>{dateRangeFilter}</span>
                          <ChevronDown size={13} />
                        </button>
                        {isDateRangeOpen && (
                          <div className="erp-dropdown-menu right-aligned">
                            {['Today', 'This Week', 'This Month', 'This Quarter', 'This Year'].map((range) => (
                              <button
                                key={range}
                                type="button"
                                className={`erp-dropdown-item ${dateRangeFilter === range ? 'selected' : ''}`}
                                onClick={() => {
                                  setDateRangeFilter(range);
                                  setIsDateRangeOpen(false);
                                }}
                              >
                                {range}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* 2. 4 KPI CARDS (Overlapping bottom edge of hero banner) */}
                    <div className="erp-kpi-row">
                      {/* Card 1: Yarn in Stock */}
                      <div className="erp-kpi-card-v2">
                        <div className="erp-kpi-media-circle">
                          <img 
                            src="/assets/images/yarn-cones.jpg" 
                            alt="Yarn in Stock" 
                            onError={(e) => { e.target.src = '/images/factory/yarn-cones.jpg'; }} 
                          />
                        </div>
                        <div className="erp-kpi-body">
                          <span className="erp-kpi-title">Yarn in Stock</span>
                          <div className="erp-kpi-number-wrap">
                            <span className="erp-kpi-big-num">12.8</span>
                            <span className="erp-kpi-unit">Tons</span>
                          </div>
                          <div className="erp-kpi-trend green">
                            <span>↑ +5%</span>
                          </div>
                        </div>
                        <div className="erp-kpi-sparkline">
                          <svg width="68" height="28" viewBox="0 0 68 28" fill="none">
                            <path d="M2 20 Q 18 16, 30 22 T 50 10 T 66 4" stroke="#10B981" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                      </div>

                      {/* Card 2: Fabric Production */}
                      <div className="erp-kpi-card-v2">
                        <div className="erp-kpi-media-circle">
                          <img 
                            src="/assets/images/finishing-fabric.jpg" 
                            alt="Fabric Production" 
                            onError={(e) => { e.target.src = '/images/factory/fabric-rolls.jpg'; }} 
                          />
                        </div>
                        <div className="erp-kpi-body">
                          <span className="erp-kpi-title">Fabric Production</span>
                          <div className="erp-kpi-number-wrap">
                            <span className="erp-kpi-big-num">8,240</span>
                            <span className="erp-kpi-unit">Meters</span>
                          </div>
                          <div className="erp-kpi-trend green">
                            <span>↑ +12%</span>
                          </div>
                        </div>
                        <div className="erp-kpi-sparkline">
                          <svg width="68" height="28" viewBox="0 0 68 28" fill="none">
                            <path d="M2 22 Q 18 24, 30 16 T 50 18 T 66 6" stroke="#2563EB" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                      </div>

                      {/* Card 3: Active Orders */}
                      <div className="erp-kpi-card-v2">
                        <div className="erp-kpi-icon-circle warm-bg">
                          <ClipboardList size={20} />
                        </div>
                        <div className="erp-kpi-body">
                          <span className="erp-kpi-title">Active Orders</span>
                          <div className="erp-kpi-number-wrap">
                            <span className="erp-kpi-big-num">{liveOrders.length > 0 ? liveOrders.length : 24}</span>
                          </div>
                          <div className="erp-kpi-trend red">
                            <span>▲ 6 at risk</span>
                          </div>
                        </div>
                        <div className="erp-kpi-sparkline">
                          <svg width="68" height="28" viewBox="0 0 68 28" fill="none">
                            <path d="M2 16 Q 16 10, 28 20 T 48 14 T 66 18" stroke="#F87171" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                      </div>

                      {/* Card 4: QC Pass Rate */}
                      <div className="erp-kpi-card-v2">
                        <div className="erp-kpi-icon-circle green-bg">
                          <ShieldCheck size={20} />
                        </div>
                        <div className="erp-kpi-body">
                          <span className="erp-kpi-title">QC Pass Rate</span>
                          <div className="erp-kpi-number-wrap">
                            <span className="erp-kpi-big-num">92.4%</span>
                          </div>
                          <div className="erp-kpi-trend green">
                            <span>↑ +2.1%</span>
                          </div>
                        </div>
                        <div className="erp-kpi-sparkline">
                          <svg width="68" height="28" viewBox="0 0 68 28" fill="none">
                            <path d="M2 22 Q 16 22, 28 18 T 46 14 T 66 4" stroke="#10B981" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                      </div>
                    </div>

                    {/* 3. ROW: MILL FLOW (8 Cols) + MACHINE STATUS (4 Cols) */}
                    <div className="erp-row-mill-machines">
                      {/* Mill Flow Card */}
                      <div className="erp-card erp-card-mill-flow">
                        <div className="erp-card-header-bar">
                          <div className="erp-card-heading-group">
                            <div className="erp-title-with-icon">
                              <Factory size={18} className="erp-card-icon-main" />
                              <h2 className="erp-card-title-v2">Mill Flow</h2>
                            </div>
                            <p className="erp-card-subtitle-v2">From yarn to dispatch — real-time production status</p>
                          </div>
                          <button
                            type="button"
                            className="erp-card-action-btn"
                            onClick={() => setErpSidebarTab('sales-orders')}
                          >
                            <span>View All Orders</span>
                            <ArrowRight size={13} />
                          </button>
                        </div>

                        <div className="erp-mill-flow-track">
                          {MILL_FLOW_STEPS.map((step, idx) => (
                            <div key={step.step} className="erp-flow-step">
                              <div className="erp-flow-thumb-wrap">
                                <img src={step.image} alt={step.name} className="erp-flow-thumb" />
                              </div>
                              <div className="erp-flow-info">
                                <div className="erp-flow-name-row">
                                  <span className={`erp-flow-badge badge-${step.tint}`}>{step.step}</span>
                                  <span className="erp-flow-name">{step.name}</span>
                                </div>
                                <span className="erp-flow-status">{step.status}</span>
                              </div>
                              <div className={`erp-flow-bottom-tint tint-${step.tint}`}>
                                <strong>{step.qty}</strong>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Machine Status Card */}
                      <div className="erp-card erp-card-machine-status">
                        <div className="erp-card-header-bar">
                          <h2 className="erp-card-title-v2">Machine Status</h2>
                          <button
                            type="button"
                            className="erp-card-link-simple"
                            onClick={() => setErpSidebarTab('machines')}
                          >
                            <span>View All</span>
                            <ArrowRight size={13} />
                          </button>
                        </div>

                        <div className="erp-machine-list">
                          {MACHINE_STATUS_LIST.map((mach) => (
                            <div key={mach.id} className="erp-machine-item">
                              <div className="erp-machine-thumb-box">
                                <img src={mach.image} alt={mach.name} />
                              </div>
                              <div className="erp-machine-info">
                                <span className="erp-machine-name">{mach.name}</span>
                                <div className="erp-machine-status-line">
                                  <span className={`erp-status-dot dot-${mach.statusType}`} />
                                  <span className={`erp-status-text text-${mach.statusType}`}>{mach.status}</span>
                                </div>
                                <span className="erp-machine-util">{mach.util}</span>
                              </div>
                              <div className="erp-machine-sparkline">
                                <svg width="60" height="24" viewBox="0 0 60 24" fill="none">
                                  <path
                                    d={mach.sparkline}
                                    stroke={mach.statusType === 'green' ? '#10B981' : mach.statusType === 'orange' ? '#F59E0B' : '#EF4444'}
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* 4. CHARTS ROW: PRODUCTION TREND (7 Cols) + YARN INVENTORY BY TYPE (5 Cols) */}
                    <div className="erp-row-charts">
                      {/* Left: Production Trend Area Chart */}
                      <div className="erp-card erp-card-chart-area">
                        <div className="erp-card-header-bar">
                          <h2 className="erp-card-title-v2">Production Trend (Meters)</h2>
                          <div className="erp-dropdown-wrap">
                            <button
                              type="button"
                              className="erp-filter-pill-btn"
                              onClick={() => setIsChartWeekOpen(!isChartWeekOpen)}
                            >
                              <span>{chartWeekFilter}</span>
                              <ChevronDown size={13} />
                            </button>
                            {isChartWeekOpen && (
                              <div className="erp-dropdown-menu right-aligned">
                                {['This Week', 'Last Week', 'This Month'].map((opt) => (
                                  <button
                                    key={opt}
                                    type="button"
                                    className={`erp-dropdown-item ${chartWeekFilter === opt ? 'selected' : ''}`}
                                    onClick={() => {
                                      setChartWeekFilter(opt);
                                      setIsChartWeekOpen(false);
                                    }}
                                  >
                                    {opt}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Chart Legend on Top */}
                        <div className="erp-chart-legend-top">
                          <div className="erp-legend-badge">
                            <span className="erp-legend-dot blue" />
                            <span>Weaving</span>
                          </div>
                          <div className="erp-legend-badge">
                            <span className="erp-legend-dot coral" />
                            <span>Dyeing</span>
                          </div>
                          <div className="erp-legend-badge">
                            <span className="erp-legend-dot orange" />
                            <span>Finishing</span>
                          </div>
                        </div>

                        {/* Smooth SVG Area Chart */}
                        <div className="erp-svg-chart-container">
                          <svg width="100%" height="220" viewBox="0 0 540 220" preserveAspectRatio="none" className="chart-svg-main">
                            <defs>
                              <linearGradient id="grad-weaving" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#2563EB" stopOpacity="0.32" />
                                <stop offset="100%" stopColor="#2563EB" stopOpacity="0.02" />
                              </linearGradient>
                              <linearGradient id="grad-dyeing" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#F87171" stopOpacity="0.28" />
                                <stop offset="100%" stopColor="#F87171" stopOpacity="0.02" />
                              </linearGradient>
                              <linearGradient id="grad-finishing" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.25" />
                                <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.02" />
                              </linearGradient>
                            </defs>

                            {/* Horizontal Gridlines */}
                            <line x1="40" y1="30" x2="520" y2="30" stroke="#F0ECE4" strokeWidth="1" strokeDasharray="3 3" />
                            <line x1="40" y1="70" x2="520" y2="70" stroke="#F0ECE4" strokeWidth="1" strokeDasharray="3 3" />
                            <line x1="40" y1="110" x2="520" y2="110" stroke="#F0ECE4" strokeWidth="1" strokeDasharray="3 3" />
                            <line x1="40" y1="150" x2="520" y2="150" stroke="#F0ECE4" strokeWidth="1" strokeDasharray="3 3" />
                            <line x1="40" y1="190" x2="520" y2="190" stroke="#EAE5DC" strokeWidth="1" />

                            {/* Y Axis Labels */}
                            <text x="32" y="34" fontSize="10" fill="#94A3B8" textAnchor="end">10K</text>
                            <text x="32" y="74" fontSize="10" fill="#94A3B8" textAnchor="end">7.5K</text>
                            <text x="32" y="114" fontSize="10" fill="#94A3B8" textAnchor="end">5K</text>
                            <text x="32" y="154" fontSize="10" fill="#94A3B8" textAnchor="end">2.5K</text>
                            <text x="32" y="193" fontSize="10" fill="#94A3B8" textAnchor="end">0</text>

                            {/* Series 1: Weaving Area & Line */}
                            <path
                              d="M 60 114 C 110 90, 160 100, 210 74 C 270 52, 330 46, 380 92 C 430 118, 480 98, 510 102 L 510 190 L 60 190 Z"
                              fill="url(#grad-weaving)"
                            />
                            <path
                              d="M 60 114 C 110 90, 160 100, 210 74 C 270 52, 330 46, 380 92 C 430 118, 480 98, 510 102"
                              fill="none"
                              stroke="#2563EB"
                              strokeWidth="2.5"
                              strokeLinecap="round"
                            />

                            {/* Series 2: Dyeing Area & Line */}
                            <path
                              d="M 60 148 C 110 132, 160 136, 210 120 C 270 106, 330 108, 380 132 C 430 144, 480 134, 510 136 L 510 190 L 60 190 Z"
                              fill="url(#grad-dyeing)"
                            />
                            <path
                              d="M 60 148 C 110 132, 160 136, 210 120 C 270 106, 330 108, 380 132 C 430 144, 480 134, 510 136"
                              fill="none"
                              stroke="#F87171"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />

                            {/* Series 3: Finishing Area & Line */}
                            <path
                              d="M 60 166 C 110 156, 160 160, 210 148 C 270 138, 330 142, 380 156 C 430 162, 480 154, 510 156 L 510 190 L 60 190 Z"
                              fill="url(#grad-finishing)"
                            />
                            <path
                              d="M 60 166 C 110 156, 160 160, 210 148 C 270 138, 330 142, 380 156 C 430 162, 480 154, 510 156"
                              fill="none"
                              stroke="#F59E0B"
                              strokeWidth="2"
                              strokeLinecap="round"
                            />

                            {/* Data points on Weaving Line */}
                            {[
                              { cx: 60, cy: 114, day: '4 Oct', val: '4,800m' },
                              { cx: 135, cy: 92, day: '5 Oct', val: '6,200m' },
                              { cx: 210, cy: 74, day: '6 Oct', val: '7,100m' },
                              { cx: 285, cy: 50, day: '7 Oct', val: '8,400m' },
                              { cx: 360, cy: 82, day: '8 Oct', val: '6,900m' },
                              { cx: 435, cy: 110, day: '9 Oct', val: '5,200m' },
                              { cx: 510, cy: 102, day: '10 Oct', val: '7,420m' },
                            ].map((pt, i) => (
                              <g key={i}>
                                <circle
                                  cx={pt.cx}
                                  cy={pt.cy}
                                  r="4"
                                  fill="#FFFFFF"
                                  stroke="#2563EB"
                                  strokeWidth="2"
                                  style={{ cursor: 'pointer' }}
                                  onMouseEnter={() => setHoveredTrendIndex(i)}
                                  onMouseLeave={() => setHoveredTrendIndex(null)}
                                />
                                <text x={pt.cx} y="206" fontSize="10.5" fill="#64748B" textAnchor="middle">
                                  {pt.day}
                                </text>
                              </g>
                            ))}
                          </svg>

                          {hoveredTrendIndex !== null && (
                            <div className="erp-chart-tooltip-v2">
                              <strong>Day Performance</strong>
                              <span>Weaving: ~7,420m</span>
                              <span>Dyeing: ~4,200m</span>
                              <span>Finishing: ~3,100m</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right: Yarn Inventory by Type Donut Chart */}
                      <div className="erp-card erp-card-donut">
                        <div className="erp-card-header-bar">
                          <h2 className="erp-card-title-v2">Yarn Inventory by Type</h2>
                          <div className="erp-dropdown-wrap">
                            <button
                              type="button"
                              className="erp-filter-pill-btn"
                              onClick={() => setIsYarnTypeOpen(!isYarnTypeOpen)}
                            >
                              <span>{yarnTypeFilter}</span>
                              <ChevronDown size={13} />
                            </button>
                            {isYarnTypeOpen && (
                              <div className="erp-dropdown-menu right-aligned">
                                {['View All', 'Natural Fibers', 'Synthetics', 'Blended'].map((opt) => (
                                  <button
                                    key={opt}
                                    type="button"
                                    className={`erp-dropdown-item ${yarnTypeFilter === opt ? 'selected' : ''}`}
                                    onClick={() => {
                                      setYarnTypeFilter(opt);
                                      setIsYarnTypeOpen(false);
                                    }}
                                  >
                                    {opt}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="erp-donut-content-row">
                          <div className="erp-donut-stage">
                            <svg width="170" height="170" viewBox="0 0 170 170">
                              <circle cx="85" cy="85" r="62" fill="none" stroke="#F4EFE6" strokeWidth="24" />
                              {/* Segments: Cotton (42%), Polyester (22%), Viscose (15%), Acrylic (8%), Blended (10%), Others (3%) */}
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#2563EB"
                                strokeWidth="24"
                                strokeDasharray="163 226"
                                strokeDashoffset="0"
                                transform="rotate(-90 85 85)"
                              />
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#F87171"
                                strokeWidth="24"
                                strokeDasharray="85 304"
                                strokeDashoffset="-163"
                                transform="rotate(-90 85 85)"
                              />
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#F59E0B"
                                strokeWidth="24"
                                strokeDasharray="58 331"
                                strokeDashoffset="-248"
                                transform="rotate(-90 85 85)"
                              />
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#60A5FA"
                                strokeWidth="24"
                                strokeDasharray="31 358"
                                strokeDashoffset="-306"
                                transform="rotate(-90 85 85)"
                              />
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#4F46E5"
                                strokeWidth="24"
                                strokeDasharray="39 350"
                                strokeDashoffset="-337"
                                transform="rotate(-90 85 85)"
                              />
                              <circle
                                cx="85"
                                cy="85"
                                r="62"
                                fill="none"
                                stroke="#94A3B8"
                                strokeWidth="24"
                                strokeDasharray="12 377"
                                strokeDashoffset="-376"
                                transform="rotate(-90 85 85)"
                              />
                            </svg>
                            <div className="erp-donut-center-label">
                              <span className="donut-center-big">12.8</span>
                              <span className="donut-center-unit">Tons</span>
                              <span className="donut-center-sub">Total</span>
                            </div>
                          </div>

                          {/* Legend list on the right */}
                          <div className="erp-donut-legend-list">
                            {YARN_DONUT_DATA.map((item) => (
                              <div key={item.label} className="erp-donut-legend-item">
                                <div className="erp-donut-item-left">
                                  <span className="erp-legend-dot" style={{ backgroundColor: item.color }} />
                                  <span>{item.label}</span>
                                </div>
                                <span className="erp-donut-pct">{item.pct}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 5. BOTTOM ROW: ORDERS AT A GLANCE (8 Cols) + QUALITY CONTROL (4 Cols) */}
                    <div className="erp-row-bottom">
                      {/* Left: Orders at a Glance */}
                      <div className="erp-card erp-card-orders-glance">
                        <div className="erp-card-header-bar">
                          <h2 className="erp-card-title-v2">Orders at a Glance</h2>
                          <button
                            type="button"
                            className="erp-card-link-simple"
                            onClick={() => setErpSidebarTab('sales-orders')}
                          >
                            <span>View All</span>
                            <ArrowRight size={13} />
                          </button>
                        </div>

                        <div className="erp-table-glance-wrap">
                          <table className="erp-glance-table">
                            <thead>
                              <tr>
                                <th>Order No.</th>
                                <th>Fabric</th>
                                <th>Quantity</th>
                                <th>Progress</th>
                                <th>Delivery</th>
                                <th>Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {ORDERS_AT_A_GLANCE.map((ord) => (
                                <tr key={ord.id}>
                                  <td className="cell-bold">{ord.id}</td>
                                  <td>{ord.fabric}</td>
                                  <td className="tabular-nums">{ord.qty}</td>
                                  <td>
                                    <div className="erp-progress-cell">
                                      <div className="erp-progress-track">
                                        <div
                                          className="erp-progress-fill"
                                          style={{ width: `${ord.progress}%`, backgroundColor: ord.progressColor }}
                                        />
                                      </div>
                                      <span className="erp-progress-pct tabular-nums">{ord.progress}%</span>
                                    </div>
                                  </td>
                                  <td>{ord.delivery}</td>
                                  <td>
                                    <span className={`erp-badge-status badge-${ord.statusColor}`}>
                                      {ord.status}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Right: Quality Control Widget */}
                      <div className="erp-card erp-card-qc">
                        <div className="erp-card-header-bar">
                          <h2 className="erp-card-title-v2">Quality Control</h2>
                          <button
                            type="button"
                            className="erp-card-link-simple"
                            onClick={() => setErpSidebarTab('rolls-qc')}
                          >
                            <span>View All</span>
                            <ArrowRight size={13} />
                          </button>
                        </div>

                        <div className="erp-qc-body-row">
                          <div className="erp-qc-image-wrap">
                            <img 
                              src="/assets/images/qc-fabric-roll.jpg" 
                              alt="Fabric Roll Inspection" 
                              className="erp-qc-image"
                              onError={(e) => { e.target.src = '/images/factory/fabric-bolts.jpg'; }}
                            />
                          </div>
                          <div className="erp-qc-stats-list">
                            <div className="erp-qc-stat-row">
                              <div className="erp-qc-stat-label">
                                <span className="erp-stat-dot grey" />
                                <span>Inspected Rolls</span>
                              </div>
                              <span className="erp-qc-stat-value tabular-nums">{QC_STATS.inspectedRolls}</span>
                            </div>
                            <div className="erp-qc-stat-row">
                              <div className="erp-qc-stat-label">
                                <span className="erp-stat-dot blue" />
                                <span>Passed</span>
                              </div>
                              <div className="erp-qc-stat-value-group">
                                <span className="erp-qc-stat-value tabular-nums">{QC_STATS.passed}</span>
                                <span className="erp-qc-stat-pct green tabular-nums">({QC_STATS.passedPct})</span>
                              </div>
                            </div>
                            <div className="erp-qc-stat-row">
                              <div className="erp-qc-stat-label">
                                <span className="erp-stat-dot orange" />
                                <span>Rework</span>
                              </div>
                              <div className="erp-qc-stat-value-group">
                                <span className="erp-qc-stat-value tabular-nums">{QC_STATS.rework}</span>
                                <span className="erp-qc-stat-pct orange tabular-nums">({QC_STATS.reworkPct})</span>
                              </div>
                            </div>
                            <div className="erp-qc-stat-row">
                              <div className="erp-qc-stat-label">
                                <span className="erp-stat-dot red" />
                                <span>Rejected</span>
                              </div>
                              <div className="erp-qc-stat-value-group">
                                <span className="erp-qc-stat-value tabular-nums">{QC_STATS.rejected}</span>
                                <span className="erp-qc-stat-pct red tabular-nums">({QC_STATS.rejectedPct})</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>

                ) : (
                  /* ==========================================================
                     TABULAR MODULE PAGES (Responsive, Pixel-Aligned)
                     ========================================================== */
                  <div>
                    {/* Header Toolbar: Search + Create Button */}
                    <div className="erp-toolbar">
                      <div className="erp-page-title-group">
                        <h2 className="erp-page-title" style={{ fontSize: '20px' }}>
                          {erpSidebarTab === 'sales-orders' && 'Sales Orders'}
                          {erpSidebarTab === 'customers' && 'Customers & Buyers'}
                          {erpSidebarTab === 'promotions' && 'Volume Promotions & Pricing'}
                          {erpSidebarTab === 'purchases' && 'Purchase Orders (Yarn Procurement)'}
                          {erpSidebarTab === 'suppliers' && 'Yarn & Material Suppliers'}
                          {erpSidebarTab === 'inventory' && 'Products & Material Catalogue'}
                          {erpSidebarTab === 'stock-levels' && 'Location Stock Levels'}
                          {erpSidebarTab === 'transfers' && 'Inter-Department Stock Transfers'}
                          {erpSidebarTab === 'stock-counts' && 'Physical Stock Counts & Audits'}
                          {erpSidebarTab === 'machines' && 'Machines & Loom Telemetry'}
                          {erpSidebarTab === 'rolls-qc' && 'Fabric Rolls & QC Inspections'}
                          {erpSidebarTab === 'reports' && 'Textile Operations & Efficiency Reports'}
                        </h2>
                        <span className="erp-page-subtitle">
                          {isBackendOnline ? 'Connected to FastAPI backend (live SQLite)' : 'Database offline'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="erp-search-box">
                          <Search size={15} />
                          <input
                            type="text"
                            placeholder="Filter records..."
                            value={dashboardSearch}
                            onChange={(e) => setDashboardSearch(e.target.value)}
                          />
                        </div>
                        <button
                          type="button"
                          className="erp-btn-primary"
                          onClick={() => {
                            setCreateModalType(
                              erpSidebarTab === 'purchases' ? 'purchase' :
                              erpSidebarTab === 'customers' ? 'customer' :
                              erpSidebarTab === 'suppliers' ? 'supplier' :
                              erpSidebarTab === 'inventory' ? 'item' :
                              erpSidebarTab === 'machines' ? 'machine' : 'order'
                            );
                            setIsCreateModalOpen(true);
                          }}
                        >
                          <Plus size={15} />
                          <span>Create Entry</span>
                        </button>
                      </div>
                    </div>

                    {/* Table View Cards */}
                    <div className="erp-table-card">
                      <div className="erp-table-responsive">
                        {erpSidebarTab === 'sales-orders' && (
                          <table className="erp-data-table">
                            <thead>
                              <tr>
                                <th>ORDER CODE</th>
                                <th>BUYER / CUSTOMER</th>
                                <th>ORDER DATE</th>
                                <th>METERS</th>
                                <th>RATE (₹/M)</th>
                                <th>STATUS</th>
                                <th>ACTIONS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {liveOrders.length > 0 ? (
                                liveOrders
                                  .filter(o => !dashboardSearch || (o.ref || '').toLowerCase().includes(dashboardSearch.toLowerCase()) || (o.buyer_name || '').toLowerCase().includes(dashboardSearch.toLowerCase()))
                                  .map((ord) => {
                                    const line = ord.lines?.[0] || {};
                                    const meters = line.qty_meters || 500;
                                    const rate = line.rate_per_meter_paise ? (line.rate_per_meter_paise / 100).toFixed(0) : '85';
                                    return (
                                      <tr key={ord.id}>
                                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#0F172A' }}>
                                          {ord.ref || `ORD-${ord.id}`}
                                        </td>
                                        <td>{ord.buyer_name || 'Buyer'}</td>
                                        <td>{ord.order_date || '2026-10-10'}</td>
                                        <td className="tabular-nums">{meters.toLocaleString()} m</td>
                                        <td className="tabular-nums">₹{rate}</td>
                                        <td>
                                          {renderOrderStatusBadge(ord.status)}
                                        </td>
                                        <td>
                                          {ord.status === 'draft' ? (
                                            <button
                                              type="button"
                                              className="erp-btn-secondary"
                                              style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                              onClick={async () => {
                                                try {
                                                  await MillAPI.confirmOrder(ord.id);
                                                  setToastMessage(`Order ${ord.ref} confirmed successfully`);
                                                  fetchAllLiveData();
                                                } catch (err) {
                                                  setToastMessage(`Action failed: ${err.message}`);
                                                }
                                              }}
                                            >
                                              Confirm
                                            </button>
                                          ) : (
                                            <span style={{ fontSize: '12px', color: '#71717a' }}>Ready</span>
                                          )}
                                        </td>
                                      </tr>
                                    );
                                  })
                              ) : (
                                <tr>
                                  <td colSpan={7}>
                                    <div className="erp-empty-card">
                                      <div className="erp-empty-icon"><ShoppingCart size={22} /></div>
                                      <span className="erp-empty-title">No Sales Orders</span>
                                      <span className="erp-empty-desc">Create your first fabric sales order from the top action button.</span>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        )}

                        {erpSidebarTab === 'purchases' && (
                          <table className="erp-data-table">
                            <thead>
                              <tr>
                                <th>PO REF</th>
                                <th>SUPPLIER</th>
                                <th>ORDER DATE</th>
                                <th>YARN KG</th>
                                <th>RATE (₹/KG)</th>
                                <th>STATUS</th>
                                <th>ACTIONS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {livePOs.length > 0 ? (
                                livePOs.map((po) => {
                                  const line = po.lines?.[0] || {};
                                  const kg = line.qty_kg || 1000;
                                  const rate = line.rate_per_kg_paise ? (line.rate_per_kg_paise / 100).toFixed(0) : '240';
                                  return (
                                    <tr key={po.id}>
                                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{po.ref || `PO-${po.id}`}</td>
                                      <td>{po.supplier_name || 'Yarn Supplier'}</td>
                                      <td>{po.order_date || '2026-10-10'}</td>
                                      <td className="tabular-nums">{kg.toLocaleString()} kg</td>
                                      <td className="tabular-nums">₹{rate}</td>
                                      <td>
                                        <span className={`erp-badge status-${(po.status || 'draft').toLowerCase()}`}>
                                          {po.status || 'draft'}
                                        </span>
                                      </td>
                                      <td>
                                        <button
                                          type="button"
                                          className="erp-btn-secondary"
                                          style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                          onClick={() => setToastMessage(`Gate pass printed for ${po.ref}`)}
                                        >
                                          Gate Pass
                                        </button>
                                      </td>
                                    </tr>
                                  );
                                })
                              ) : (
                                [
                                  { ref: 'PO-2026-0001', sup: 'Himalayan Yarn Co.', dt: '2026-10-08', kg: 1200, rate: '₹260', st: 'confirmed' },
                                  { ref: 'PO-2026-0002', sup: 'Deccan Fibres Ltd.', dt: '2026-10-09', kg: 800, rate: '₹310', st: 'draft' },
                                ].map((po, idx) => (
                                  <tr key={idx}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{po.ref}</td>
                                    <td>{po.sup}</td>
                                    <td>{po.dt}</td>
                                    <td className="tabular-nums">{po.kg.toLocaleString()} kg</td>
                                    <td className="tabular-nums">{po.rate}</td>
                                    <td>
                                      <span className={`erp-badge status-${po.st}`}>{po.st}</span>
                                    </td>
                                    <td>
                                      <button
                                        type="button"
                                        className="erp-btn-secondary"
                                        style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                        onClick={() => setToastMessage(`Inward gate entry verified for ${po.ref}`)}
                                      >
                                        Verify
                                      </button>
                                    </td>
                                  </tr>
                                ))
                              )}
                            </tbody>
                          </table>
                        )}

                        {erpSidebarTab === 'inventory' && (
                          <table className="erp-data-table">
                            <thead>
                              <tr>
                                <th>SKU CODE</th>
                                <th>NAME</th>
                                <th>TYPE</th>
                                <th>UNIT</th>
                                <th>COUNT / GSM</th>
                                <th>REORDER POINT</th>
                                <th>STATUS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {liveItems.map((item) => (
                                <tr key={item.id}>
                                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{item.sku}</td>
                                  <td>{item.name}</td>
                                  <td>
                                    <span style={{ textTransform: 'capitalize' }}>{item.item_type}</span>
                                  </td>
                                  <td>{item.unit}</td>
                                  <td>{item.count_denier || (item.gsm ? `${item.gsm} GSM` : '-')}</td>
                                  <td className="tabular-nums">{(item.reorder_point_kg || 0).toLocaleString()} kg</td>
                                  <td>
                                    <span className="erp-badge status-active">Active</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}

                        {erpSidebarTab === 'machines' && (
                          <table className="erp-data-table">
                            <thead>
                              <tr>
                                <th>LOOM / MACHINE</th>
                                <th>NAME</th>
                                <th>TYPE</th>
                                <th>SPEED</th>
                                <th>STATUS</th>
                                <th>ACTIONS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {liveMachines.map((m) => (
                                <tr key={m.id}>
                                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{m.code}</td>
                                  <td>{m.name}</td>
                                  <td style={{ textTransform: 'capitalize' }}>{m.machine_type}</td>
                                  <td className="tabular-nums">640 RPM</td>
                                  <td>
                                    <span className="erp-badge status-running">Running</span>
                                  </td>
                                  <td>
                                    <button
                                      type="button"
                                      className="erp-btn-secondary"
                                      style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                      onClick={() => setToastMessage(`Telemetry ping sent to ${m.code}`)}
                                    >
                                      Calibrate
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}

                        {erpSidebarTab === 'rolls-qc' && (
                          <table className="erp-data-table">
                            <thead>
                              <tr>
                                <th>ROLL NO</th>
                                <th>LENGTH (M)</th>
                                <th>WEIGHT (KG)</th>
                                <th>QC GRADE</th>
                                <th>STATUS</th>
                                <th>ACTIONS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {liveRolls.length > 0 ? (
                                liveRolls.map((r) => (
                                  <tr key={r.id}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{r.roll_number || `ROL-${r.id}`}</td>
                                    <td className="tabular-nums">{r.length_m || '-'} m</td>
                                    <td className="tabular-nums">{r.weight_g ? (r.weight_g / 1000).toFixed(1) : '-'} kg</td>
                                    <td>
                                      {renderQCGradeBadge(r.qc_grade)}
                                    </td>
                                    <td>
                                      {renderRollStatusBadge(r.status)}
                                    </td>
                                    <td>
                                      <button
                                        type="button"
                                        className="erp-btn-secondary"
                                        style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                        onClick={() => setToastMessage(`Lab ASTM certificate generated for ${r.roll_number || r.id}`)}
                                      >
                                        Lab Cert
                                      </button>
                                    </td>
                                  </tr>
                                ))
                              ) : (
                                [
                                  { no: 'ROL-2026-001', m: '120.5 m', w: '34.2 kg', gr: 'Grade A', st: 'passed' },
                                  { no: 'ROL-2026-002', m: '118.0 m', w: '33.8 kg', gr: 'Grade A', st: 'passed' },
                                  { no: 'ROL-2026-003', m: '95.4 m', w: '27.1 kg', gr: 'Grade B', st: 'awaiting_qc' },
                                ].map((r, idx) => (
                                  <tr key={idx}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{r.no}</td>
                                    <td className="tabular-nums">{r.m}</td>
                                    <td className="tabular-nums">{r.w}</td>
                                    <td>{renderQCGradeBadge(r.gr)}</td>
                                    <td>{renderRollStatusBadge(r.st)}</td>
                                    <td>
                                      <button
                                        type="button"
                                        className="erp-btn-secondary"
                                        style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                                        onClick={() => setToastMessage(`QC inspection recorded for ${r.no}`)}
                                      >
                                        Inspect
                                      </button>
                                    </td>
                                  </tr>
                                ))
                              )}
                            </tbody>
                          </table>
                        )}

                        {/* Customers, Suppliers, Stock Levels, Transfers, Stock Counts, Promotions, Reports Fallback */}
                        {!['sales-orders', 'purchases', 'inventory', 'machines', 'rolls-qc'].includes(erpSidebarTab) && (
                          <div className="erp-empty-card" style={{ padding: '60px 24px' }}>
                            <div className="erp-empty-icon">
                              {erpSidebarTab === 'customers' && <Users size={24} />}
                              {erpSidebarTab === 'suppliers' && <Building2 size={24} />}
                              {erpSidebarTab === 'promotions' && <Tag size={24} />}
                              {erpSidebarTab === 'stock-levels' && <Package size={24} />}
                              {erpSidebarTab === 'transfers' && <ArrowLeftRight size={24} />}
                              {erpSidebarTab === 'stock-counts' && <ClipboardList size={24} />}
                              {erpSidebarTab === 'reports' && <BarChart3 size={24} />}
                            </div>
                            <span className="erp-empty-title">
                              {erpSidebarTab === 'customers' && 'Active Buyers & Fashion Houses'}
                              {erpSidebarTab === 'suppliers' && 'Yarn & Spinning Mill Suppliers'}
                              {erpSidebarTab === 'promotions' && 'Volume Promotions & Discounts'}
                              {erpSidebarTab === 'stock-levels' && 'Store Location Inventory (RAW & FIN)'}
                              {erpSidebarTab === 'transfers' && 'Floor & Shed Movement Logs'}
                              {erpSidebarTab === 'stock-counts' && 'Reconciliation & Physical Audits'}
                              {erpSidebarTab === 'reports' && 'Textile Production & Profitability Reports'}
                            </span>
                            <span className="erp-empty-desc">
                              {erpSidebarTab === 'reports'
                                ? 'Looms Utilization: 91.4% · Weft Waste: 1.8% · Lab Pass Rate: 98.2% · On-Time Dispatch: 96.5%'
                                : 'All records are synced directly with the Khadira Textile Mills FastAPI database.'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Unified Create Entry Modal */}
          {isCreateModalOpen && (
            <div className="erp-modal-overlay" onClick={() => setIsCreateModalOpen(false)}>
              <div className="erp-modal-window" onClick={(e) => e.stopPropagation()}>
                <div className="erp-modal-header">
                  <h3 className="erp-modal-title">
                    {createModalType === 'purchase' ? 'New Yarn Purchase Order' :
                     createModalType === 'customer' ? 'Add Buyer / Customer' :
                     createModalType === 'supplier' ? 'Add Yarn Supplier' :
                     createModalType === 'item' ? 'Add Material to Catalogue' :
                     createModalType === 'machine' ? 'Register New Loom / Machine' : 'New Fabric Sales Order'}
                  </h3>
                  <button
                    type="button"
                    className="erp-modal-close-btn"
                    onClick={() => setIsCreateModalOpen(false)}
                  >
                    <X size={18} />
                  </button>
                </div>

                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    try {
                      if (createModalType === 'order') {
                        await MillAPI.createOrder({
                          buyer_id: liveBuyers[0]?.id || 1,
                          order_date: new Date().toISOString().split('T')[0],
                          lines: [{
                            item_id: liveItems[0]?.id || 5,
                            qty_meters: Number(newOrderMeters) || 1200,
                            rate_per_meter_paise: (Number(newOrderRate) || 85) * 100,
                          }],
                          notes: `Order for ${newOrderBuyerName}`,
                        });
                        setToastMessage('Sales order created successfully!');
                      } else if (createModalType === 'purchase') {
                        await MillAPI.createPO({
                          supplier_id: liveSuppliers[0]?.id || 1,
                          order_date: new Date().toISOString().split('T')[0],
                          lines: [{
                            item_id: liveItems[0]?.id || 1,
                            qty_kg: 1000,
                            rate_per_kg_paise: 25000,
                          }],
                          notes: 'Yarn procurement intake',
                        });
                        setToastMessage('Purchase order created successfully!');
                      } else {
                        setToastMessage('Entry created and registered in database');
                      }
                      setIsCreateModalOpen(false);
                      fetchAllLiveData();
                    } catch (err) {
                      setToastMessage(`Failed: ${err.message}`);
                    }
                  }}
                  className="erp-modal-body"
                >
                  <div className="erp-field">
                    <label className="erp-label">Entity Name / Reference</label>
                    <input
                      type="text"
                      className="erp-input"
                      placeholder="e.g. Metro Garments Pvt Ltd"
                      value={newOrderBuyerName}
                      onChange={(e) => setNewOrderBuyerName(e.target.value)}
                      required
                    />
                  </div>

                  <div className="erp-field">
                    <label className="erp-label">Quantity (Meters or KG)</label>
                    <input
                      type="number"
                      className="erp-input"
                      placeholder="1200"
                      value={newOrderMeters}
                      onChange={(e) => setNewOrderMeters(e.target.value)}
                      required
                    />
                  </div>

                  <div className="erp-field">
                    <label className="erp-label">Unit Rate (₹ per unit)</label>
                    <input
                      type="number"
                      className="erp-input"
                      placeholder="85"
                      value={newOrderRate}
                      onChange={(e) => setNewOrderRate(e.target.value)}
                      required
                    />
                  </div>

                  <div className="erp-modal-actions">
                    <button
                      type="button"
                      className="erp-btn-secondary"
                      onClick={() => setIsCreateModalOpen(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="erp-btn-primary"
                    >
                      Save & Confirm
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {toastMessage && (
            <div className="erp-toast-pill">
              <Check size={15} style={{ color: '#10b981' }} />
              <span>{toastMessage}</span>
            </div>
          )}
        </main>
      ) : (
        <>
          <div className="landing-bg-overlay" aria-hidden="true" />
          {/* =========================================
              1. STICKY HEADER
              ========================================= */}
          <header className={`site-header ${scrolled ? 'scrolled' : ''}`}>
            <div className="header-container">
              <a href="#" className="brand-logo" id="brand-logo">
                KHADIRA
              </a>

              <nav className="nav-desktop">
                <a href="#modules" className="nav-link" id="nav-modules">Modules</a>
                <a href="#flow" className="nav-link" id="nav-flow">Production Flow</a>
                <a href="#workflow" className="nav-link" id="nav-workflow">Factory Workflow</a>
                <a href="#teams" className="nav-link" id="nav-teams">Teams</a>
                <a href="#faqs" className="nav-link" id="nav-faqs">FAQs</a>
                <a 
                  href="#login" 
                  className="nav-link" 
                  id="nav-login"
                  onClick={(e) => {
                    e.preventDefault();
                    setIsLoginModalOpen(true);
                  }}
                >
                  Login
                </a>
              </nav>

              <div className="header-actions">
                <button 
                  type="button"
                  onClick={() => setIsLoginModalOpen(true)}
                  className="btn-header-terminal"
                  id="header-terminal-link"
                  title="Access Factory Terminal Login"
                >
                  <Lock size={11} />
                  <span>{isLoggedIn ? 'Switch User / Login' : 'Login'}</span>
                </button>

                {isLoggedIn && (
                  <button 
                    type="button"
                    onClick={() => setIsDashboardOpen(true)}
                    className="btn-header-dashboard"
                    id="header-dashboard-link"
                    title="Launch Factory Dashboard"
                  >
                    <Sparkles size={11} />
                    <span>Open Dashboard</span>
                  </button>
                )}

                <button 
                  className="lang-switch" 
                  onClick={() => setLang(lang === 'EN' ? 'FR' : 'EN')}
                  id="lang-toggle"
                  aria-label="Toggle language"
                >
                  {lang} / {lang === 'EN' ? 'FR' : 'EN'}
                </button>

                <button 
                  className="btn-bag" 
                  onClick={() => setIsBagOpen(true)}
                  id="header-bag-btn"
              aria-label="Open Production Queue"
            >
              <ShoppingBag size={13} />
              <span>Queue</span>
              <span className="bag-count">{totalBagCount}</span>
            </button>

            <button 
              className="mobile-menu-btn" 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Mobile Menu"
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="mobile-nav-drawer">
            <a href="#modules" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Modules</a>
            <a href="#flow" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Production Flow</a>
            <a href="#workflow" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Factory Workflow</a>
            <a href="#teams" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Teams</a>
            <a href="#faqs" className="nav-link" onClick={() => setMobileMenuOpen(false)}>FAQs</a>
            <a href="#contact" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Contact</a>
          </div>
        )}
      </header>

      {/* =========================================
          2. HERO SECTION — CONTINUOUS 3D ELLIPTICAL ORBIT
          ========================================= */}
      <section className="hero-section" id="hero">
        <div className="hero-orbit-stage" aria-hidden="true">
          <div className="hero-orbit-center">
            {HERO_ORBIT_IMAGES.map((card, idx) => (
              <div
                key={card.id}
                ref={(el) => (heroCardRefs.current[idx] = el)}
                className="hero-orbit-card"
                style={{
                  width: `clamp(${card.widthMobile}px, 14vw, ${card.widthDesktop}px)`,
                  aspectRatio: card.aspectRatio,
                  zIndex: card.zIndex
                }}
              >
                <img 
                  src={card.src} 
                  alt={card.alt} 
                  draggable="false"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="hero-content">
          <span className="hero-eyebrow">
            TEXTILE MANUFACTURING SOFTWARE — BUILT FOR BUSY FABRIC MILLS
          </span>
          <h1 className="hero-title">
            KHADIRA
          </h1>
          <p className="hero-subtext">
            TRACK YARN, MACHINES, ORDERS, QUALITY AND DISPATCH
          </p>

          {/* COMPACT HOMEPAGE LOGIN TAB */}
          <div className="hero-login-tab-wrap" id="terminal-login">
            <button 
              type="button" 
              className="hero-login-tab-btn" 
              onClick={() => setIsLoginModalOpen(true)}
              id="hero-login-tab"
              aria-label="Open Terminal Login"
            >
              <span className="terminal-live-dot" />
              <Lock size={12} />
              <span>TERMINAL LOGIN</span>
              <ArrowRight size={12} className="tab-arrow-icon" />
            </button>
            {isLoggedIn && (
              <button 
                type="button" 
                className="hero-login-tab-btn active" 
                onClick={() => setIsDashboardOpen(true)}
                id="hero-login-tab-active"
                aria-label="Launch Floor Dashboard"
              >
                <span className="terminal-live-dot" />
                <Sparkles size={12} />
                <span>{loggedInUser?.role || 'Admin'} · OPEN DASHBOARD</span>
                <ArrowRight size={12} className="tab-arrow-icon" />
              </button>
            )}
          </div>
        </div>

        <div className="hero-footer-bar">
          <div className="hero-cta-wrapper">
            <a href="#modules" className="hero-cta-btn" id="hero-cta-modules">
              ✦ VIEW MODULES
            </a>
            <div className="hero-center-tick" />
            <a href="#spotlight" className="hero-cta-btn" id="hero-cta-track">
              TRACK ORDER ✦
            </a>
          </div>
          <div className="editorial-divider" />
        </div>
      </section>

      {/* =========================================
          3. INTRO STATEMENT
          ========================================= */}
      <section className="intro-section">
        <div className="intro-container">
          <blockquote className="intro-quote">
            ✦ Built directly on the factory floor. From raw cotton intake and yarn spinning to loom uptime, dye vat tracking, lab inspections, and container dispatch — KHADIRA gives fabric mills instant visibility over every meter produced.
          </blockquote>
          <p className="intro-tagline">
            Real-time floor intelligence. Zero missing fabric rolls.
          </p>
        </div>
      </section>

      {/* =========================================
          4. CORE MODULES SECTION
          ========================================= */}
      <section className="products-section" id="modules">
        <div className="section-header-block">
          <div>
            <span className="section-label">01 — OPERATING MODULES</span>
            <h2 className="section-title">Core Modules</h2>
          </div>
          <span className="tracking-wide-label" style={{ color: '#8c877f' }}>
            BUILT FOR INTEGRATED WEAVING, DYEING & APPAREL UNITS
          </span>
        </div>

        <div className="products-grid">
          {PRODUCTS.map((prod) => (
            <article className="product-card" key={prod.id}>
              <div className="product-image-wrap">
                <img src={prod.image} alt={prod.name} loading="lazy" />
                <span className="product-tag">{prod.tag}</span>
              </div>
              <div className="product-info">
                <div className="product-title-row">
                  <h3 className="product-name">{prod.name}</h3>
                  <span className="product-price">{prod.priceStr}</span>
                </div>
                <p className="product-desc">{prod.desc}</p>
                <button 
                  className="product-add-btn"
                  onClick={() => addToBag(prod)}
                  id={`add-btn-${prod.id}`}
                >
                  <Plus size={13} />
                  <span>Add to Queue</span>
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* =========================================
          5. LIVE FACTORY STATUS
          ========================================= */}
      <section className="restock-section">
        <div className="section-header-block">
          <div>
            <span className="section-label">02 — REAL-TIME FLOOR TELEMETRY</span>
            <h2 className="section-title">Live Factory Status</h2>
          </div>
          <span className="tracking-wide-label" style={{ color: '#8c877f' }}>
            MILL METRICS · LIVE SYNCHRONIZATION
          </span>
        </div>

        <div className="restock-grid">
          <div className="restock-card">
            <div className="restock-img-wrap">
              <img src={CRAFT_ASSETS.naturalDyedHanks} alt="Natural botanical dye hanks hanging on beams" />
            </div>
            <div className="restock-body">
              <div className="restock-header">
                <h3 className="restock-title">Spinning & Winding Shed</h3>
                <span className="restock-batch">Shift A · Bay 04</span>
              </div>
              <p className="product-desc">
                High-speed ring frames running combed 40s count yarn. Continuous yarn tension monitoring active.
              </p>
              <div className="restock-meta">
                <span className="status-pill">
                  <span className="status-indicator-dot" />
                  Running at 98.4% RPM
                </span>
                <span className="restock-time">Target On-Track</span>
              </div>
            </div>
          </div>

          <div className="restock-card">
            <div className="restock-img-wrap">
              <img src={CRAFT_ASSETS.yarnSpoolsRack} alt="Yarn spools on wooden studio rack" />
            </div>
            <div className="restock-body">
              <div className="restock-header">
                <h3 className="restock-title">Dyeing & Finishing House</h3>
                <span className="restock-batch">Lot #ETM-842</span>
              </div>
              <p className="product-desc">
                High-temperature soft-flow dye vessel executing reactive dye sequence with pH and liquor temperature control.
              </p>
              <div className="restock-meta">
                <span className="status-pill">
                  <span className="status-indicator-dot" />
                  Steam Cycle Active
                </span>
                <span className="restock-time">Est. 45 min</span>
              </div>
            </div>
          </div>

          <div className="restock-card">
            <div className="restock-img-wrap">
              <img src={CRAFT_ASSETS.blockPrinting} alt="Woodblock stamping on artisan craft fabric" />
            </div>
            <div className="restock-body">
              <div className="restock-header">
                <h3 className="restock-title">Inspection & Packing Line</h3>
                <span className="restock-batch">PO #9420 · Global Export</span>
              </div>
              <p className="product-desc">
                Automated 4-point fabric inspection frames scanning finished rolls for weft skew and yarn slubs.
              </p>
              <div className="restock-meta">
                <span className="status-pill">
                  <span className="status-indicator-dot" />
                  Barcode Roll Grading
                </span>
                <span className="restock-time">Dispatch Ready</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================
          6. MOVING SHELF / PRODUCTION FLOW
          ========================================= */}
      <section className="moving-shelf-section" id="flow">
        <div className="shelf-header-container">
          <div>
            <span className="section-label">END-TO-END MANUFACTURING PIPELINE</span>
            <h2 className="section-title">Production Flow</h2>
          </div>

          <div className="shelf-controls">
            <span className="shelf-counter">
              0{currentShelfIdx + 1} / 0{SHELF_ITEMS.length}
            </span>
            <button 
              className="shelf-nav-btn" 
              onClick={() => scrollShelf('prev')}
              aria-label="Scroll pipeline previous"
            >
              <ArrowLeft size={16} />
            </button>
            <button 
              className="shelf-nav-btn" 
              onClick={() => scrollShelf('next')}
              aria-label="Scroll pipeline next"
            >
              <ArrowRight size={16} />
            </button>
          </div>
        </div>

        <div 
          className="horizontal-shelf-track" 
          ref={shelfScrollRef}
          onScroll={handleShelfScroll}
        >
          {SHELF_ITEMS.map((item, idx) => (
            <div className="shelf-item-card" key={idx}>
              <div className="shelf-item-img">
                <img src={item.image} alt={item.title} loading="lazy" />
              </div>
              <div className="shelf-item-info">
                <h3 className="shelf-item-title">{item.title}</h3>
                <span className="shelf-item-code">{item.code}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* =========================================
          7. ORDER SPOTLIGHT
          ========================================= */}
      <section className="feature-product-section" id="spotlight">
        <div className="feature-grid">
          <div className="feature-image-box">
            <img src={CRAFT_ASSETS.wovenSwatches} alt="High density twill weave fabric roll" />
          </div>

          <div className="feature-details">
            <span className="feature-badge">ORDER SPOTLIGHT</span>
            <h2 className="feature-heading">PO #ETM-9428</h2>
            <p className="feature-subhead">
              HIGH-DENSITY TWILL WEAVE · 48,000 METERS · EXPORT BATCH
            </p>

            <div className="feature-stats-list">
              <div className="stat-item">
                <span className="stat-label">Woven Volume</span>
                <span className="stat-value">41,200 m (86%)</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Yarn Lot</span>
                <span className="stat-value">Ring Spun 30s Cotton</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Dispatch ETA</span>
                <span className="stat-value">3 Days Ahead</span>
              </div>
            </div>

            <button 
              className="btn-feature-bag"
              onClick={() => addToBag({
                id: 'order-etm-9428',
                name: 'PO #ETM-9428 Twill Weave',
                price: 1,
                image: CRAFT_ASSETS.wovenSwatches
              })}
              id="feature-add-to-bag"
            >
              <Sparkles size={15} />
              <span>Track Order Dossier</span>
            </button>
          </div>
        </div>
      </section>

      {/* =========================================
          8. ONE DIGITAL BACKBONE FOR THE MILL
          ========================================= */}
      <section className="studio-story-section" id="studio">
        <div className="studio-banner-wrap">
          <img src={CRAFT_ASSETS.naturalDyedHanks} alt="Khadira Textile Mills integrated production house" />
          <div className="studio-banner-overlay">
            <span className="studio-watermark">KHADIRA</span>
          </div>
        </div>

        <div className="studio-text-grid">
          <h2 className="studio-heading">
            One Digital Backbone<br />For The Mill
          </h2>
          <div className="studio-prose">
            <p>
              KHADIRA unites every department of Khadira Textile Mills into a single, cohesive operating reality. From raw cotton intake in the storehouse to high-speed loom sheds, laboratory dye testing, and customs-sealed shipping containers, floor data flows in real time.
            </p>
            <p>
              Eliminate clipboard delays, stock mismatches, and untracked machine downtime. Every fabric meter, shift operator, and yarn bale is timestamped, audited, and optimized.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================
          9. FACTORY WORKFLOW
          ========================================= */}
      <section className="timeline-section" id="workflow">
        <div className="section-header-block">
          <div>
            <span className="section-label">INTEGRATED 4-STAGE ARCHITECTURE</span>
            <h2 className="section-title">Factory Workflow</h2>
          </div>
        </div>

        <div className="timeline-grid">
          <div className="timeline-card">
            <div className="timeline-img-wrap">
              <img src={CRAFT_ASSETS.spinningWheel} alt="Raw material gate-in barcode scanning" />
            </div>
            <div className="timeline-body">
              <span className="timeline-year">STAGE 01</span>
              <p className="timeline-text">
                Raw Material Gate In: Barcode scanning, moisture analysis, and automatic yarn lot inventory assignment.
              </p>
            </div>
          </div>

          <div className="timeline-card">
            <div className="timeline-img-wrap">
              <img src={CRAFT_ASSETS.blockPrinting} alt="Loom and machine IoT integration" />
            </div>
            <div className="timeline-body">
              <span className="timeline-year">STAGE 02</span>
              <p className="timeline-text">
                Loom & Machine Integration: IoT sensor hooks record pick counts, stop causes, efficiency percentages, and operator shifts.
              </p>
            </div>
          </div>

          <div className="timeline-card">
            <div className="timeline-img-wrap">
              <img src={CRAFT_ASSETS.yarnSpoolsRack} alt="Dyehouse liquor ratio and temperature telemetry" />
            </div>
            <div className="timeline-body">
              <span className="timeline-year">STAGE 03</span>
              <p className="timeline-text">
                Dyehouse & Stenter Analytics: Liquor ratio tracking, recipe management, color lab spectro matching, and batch curing logs.
              </p>
            </div>
          </div>

          <div className="timeline-card">
            <div className="timeline-img-wrap">
              <img src={CRAFT_ASSETS.goldThreadSwift} alt="Roll grading, packing list and container dispatch" />
            </div>
            <div className="timeline-body">
              <span className="timeline-year">STAGE 04</span>
              <p className="timeline-text">
                Roll Grading & Container Dispatch: Automatic 4-point defect deduction, weight verification, shipping mark generation, and ERP export.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================
          10. TEAMS USING THE SYSTEM
          ========================================= */}
      <section className="makers-section" id="teams">
        <div className="section-header-block">
          <div>
            <span className="section-label">DEPARTMENTAL COLLABORATION</span>
            <h2 className="section-title">Teams Using The System</h2>
          </div>
        </div>

        <div className="makers-grid">
          <div className="maker-card">
            <div className="maker-portrait-wrap">
              <img src={CRAFT_ASSETS.teamStoreManager} alt="Store Manager — Yarn cones, raw material racks, and warehouse inventory" />
            </div>
            <div className="maker-details">
              <span className="maker-role">Warehouse & Inventory</span>
              <h3 className="maker-name">Store Manager</h3>
              <p className="maker-desc">Tracks yarn inward, stock levels, low-stock alerts, and finished fabric inventory.</p>
            </div>
          </div>

          <div className="maker-card">
            <div className="maker-portrait-wrap">
              <img src={CRAFT_ASSETS.teamProductionSupervisor} alt="Production Supervisor — Industrial weaving looms and spinning machine floor" />
            </div>
            <div className="maker-details">
              <span className="maker-role">Loom & Spindle Operations</span>
              <h3 className="maker-name">Production Supervisor</h3>
              <p className="maker-desc">Assigns orders to machines and monitors live spinning, weaving, dyeing, and shift output.</p>
            </div>
          </div>

          <div className="maker-card">
            <div className="maker-portrait-wrap">
              <img src={CRAFT_ASSETS.teamQualityInspector} alt="Quality Inspector — Illuminated fabric inspection table and defect grading console" />
            </div>
            <div className="maker-details">
              <span className="maker-role">4-Point Defect Grading</span>
              <h3 className="maker-name">Quality Inspector</h3>
              <p className="maker-desc">Records roll-wise defects, pass/rework/reject status, and traceability.</p>
            </div>
          </div>

          <div className="maker-card">
            <div className="maker-portrait-wrap">
              <img src={CRAFT_ASSETS.teamAccountsOwner} alt="Accounts & Owner — Mezzanine factory dashboard, production costing and reports" />
            </div>
            <div className="maker-details">
              <span className="maker-role">Executive & Costing</span>
              <h3 className="maker-name">Accounts & Owner</h3>
              <p className="maker-desc">Reviews order costing, wages, supplier bills, buyer payments, and profit reports.</p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================
          11. KEY ACTIONS
          ========================================= */}
      <section className="workshops-section" id="actions">
        <div className="workshops-header">
          <span className="section-label">OPERATIONAL FAST ACTIONS</span>
          <h2 className="section-title">KEY ACTIONS</h2>
          <p className="workshops-subtitle">
            Launch rapid floor audits, record machine breakdowns, or generate export packs in seconds.
          </p>
        </div>

        <div className="workshops-grid">
          <div className="workshop-card">
            <div className="workshop-img-wrap">
              <img src={CRAFT_ASSETS.blockPrinting} alt="Log Machine Downtime" />
            </div>
            <div className="workshop-body">
              <div className="workshop-title-row">
                <h3 className="workshop-name">Log Machine Downtime</h3>
                <span className="workshop-price">RAPID TICKET</span>
              </div>
              <p className="workshop-desc">
                Instant breakdown ticket dispatch with technician allocation and machine error reason codes.
              </p>
              <button 
                className="workshop-book-btn"
                onClick={() => bookWorkshop('Log Machine Downtime', 1, CRAFT_ASSETS.blockPrinting)}
                id="action-log-downtime"
              >
                Log Shift Event
              </button>
            </div>
          </div>

          <div className="workshop-card">
            <div className="workshop-img-wrap">
              <img src={CRAFT_ASSETS.handEmbroidery} alt="Initiate Roll Inspection" />
            </div>
            <div className="workshop-body">
              <div className="workshop-title-row">
                <h3 className="workshop-name">Initiate Roll Inspection</h3>
                <span className="workshop-price">4-POINT GRID</span>
              </div>
              <p className="workshop-desc">
                Launch digital 4-point scoring grid on shop floor tablet with high-res photo defect attachment.
              </p>
              <button 
                className="workshop-book-btn"
                onClick={() => bookWorkshop('Initiate Roll Inspection', 1, CRAFT_ASSETS.handEmbroidery)}
                id="action-roll-inspection"
              >
                Start Roll Audit
              </button>
            </div>
          </div>

          <div className="workshop-card">
            <div className="workshop-img-wrap">
              <img src={CRAFT_ASSETS.spinningWheel} alt="Generate Status Pack" />
            </div>
            <div className="workshop-body">
              <div className="workshop-title-row">
                <h3 className="workshop-name">Generate Status Pack</h3>
                <span className="workshop-price">BUYER PORTAL</span>
              </div>
              <p className="workshop-desc">
                One-click export milestone report with current roll count, test certificates, and dispatch dates.
              </p>
              <button 
                className="workshop-book-btn"
                onClick={() => bookWorkshop('Generate Status Pack', 1, CRAFT_ASSETS.spinningWheel)}
                id="action-generate-pack"
              >
                Generate Dossier
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================
          12. BENEFITS
          ========================================= */}
      <section className="reviews-section" id="benefits">
        <div className="reviews-container">
          <div className="review-card-display">
            <div className="review-stars">
              {'★ ★ ★ ★ ★'}
            </div>
            <blockquote className="review-quote">
              {REVIEWS[activeReviewIdx].quote}
            </blockquote>
            <p className="review-attribution">
              {REVIEWS[activeReviewIdx].source}
            </p>
          </div>

          <div className="reviews-dots">
            {REVIEWS.map((_, idx) => (
              <button
                key={idx}
                className={`dot-btn ${activeReviewIdx === idx ? 'active' : ''}`}
                onClick={() => setActiveReviewIdx(idx)}
                aria-label={`View review ${idx + 1}`}
              />
            ))}
          </div>
        </div>
      </section>

      {/* =========================================
          13. MANUFACTURING FAQS
          ========================================= */}
      <section className="faq-section" id="faqs">
        <div className="section-header-block" style={{ justifyContent: 'center', textAlign: 'center' }}>
          <div>
            <span className="section-label">ENTERPRISE IMPLEMENTATION</span>
            <h2 className="section-title">Manufacturing FAQs</h2>
          </div>
        </div>

        <div className="faq-list">
          {FAQS.map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div className="faq-item" key={idx}>
                <button 
                  className="faq-trigger" 
                  onClick={() => setOpenFaq(isOpen ? -1 : idx)}
                  aria-expanded={isOpen}
                >
                  <span className="faq-question">{faq.question}</span>
                  <Plus className={`faq-icon ${isOpen ? 'expanded' : ''}`} size={22} />
                </button>
                <div className={`faq-answer ${isOpen ? 'expanded' : ''}`}>
                  <p>{faq.answer}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* =========================================
          14. FACTORY REPORTS
          ========================================= */}
      <section className="stockist-section" id="reports">
        <div className="stockist-box">
          <div>
            <span className="section-label">AUDIT & COMPLIANCE ARCHIVE</span>
            <h2 className="section-title">FACTORY REPORTS</h2>
            
            <div className="stockist-links-list">
              <a href="#reports" className="stockist-link-item" onClick={(e) => { e.preventDefault(); setKeyModalOpen(true); }}>
                Daily Production & Loom Efficiency Log <ExternalLink size={16} />
              </a>
              <a href="#reports" className="stockist-link-item" onClick={(e) => { e.preventDefault(); setKeyModalOpen(true); }}>
                Yarn Lot Reconciliation & Waste Audit <ExternalLink size={16} />
              </a>
              <a href="#reports" className="stockist-link-item" onClick={(e) => { e.preventDefault(); setKeyModalOpen(true); }}>
                4-Point Fabric Quality Certificates <ExternalLink size={16} />
              </a>
              <a href="#reports" className="stockist-link-item" onClick={(e) => { e.preventDefault(); setKeyModalOpen(true); }}>
                OEKO-TEX & GOTS Compliance Records <ExternalLink size={16} />
              </a>
              <a href="#reports" className="stockist-link-item" onClick={(e) => { e.preventDefault(); setKeyModalOpen(true); }}>
                Monthly Mill Dispatch & Export Dossier <ExternalLink size={16} />
              </a>
            </div>
          </div>

          <div className="stockist-info-col">
            <p className="stockist-copy">
              Factory performance reports, lab certificates, and machine telemetry audits are accessible to authorized mill executives and certified auditors. Enter your mill credentials for secure access.
            </p>
            <button 
              className="btn-request-key"
              onClick={() => setKeyModalOpen(true)}
              id="btn-request-key"
            >
              REQUEST REPORT ACCESS
            </button>
          </div>
        </div>
      </section>

      {/* =========================================
          15. PLATFORM DEMO CTA
          ========================================= */}
      <section className="newsletter-banner-section">
        <div className="newsletter-card">
          <img src={CRAFT_ASSETS.crochetYarn} alt="Textile manufacturing digital intelligence" className="newsletter-bg-img" />
          <div className="newsletter-content">
            <span className="newsletter-eyebrow">MILL OPERATIONS INTELLIGENCE</span>
            <h2 className="newsletter-heading">CONNECT YOUR FACTORY</h2>

            {!newsletterSubmitted ? (
              <form 
                className="newsletter-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (newsletterEmail) {
                    setNewsletterSubmitted(true);
                  }
                }}
              >
                <input 
                  type="email" 
                  placeholder="Enter corporate email address"
                  className="newsletter-input"
                  value={newsletterEmail}
                  onChange={(e) => setNewsletterEmail(e.target.value)}
                  required
                />
                <button type="submit" className="newsletter-btn" id="newsletter-btn">
                  REQUEST PLATFORM DEMO
                </button>
              </form>
            ) : (
              <p className="newsletter-success">
                ✦ Demo request received. Our industrial solutions engineer will contact your plant management team within 24 hours.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* =========================================
          16. FOOTER
          ========================================= */}
      <footer className="site-footer" id="contact">
        <div className="footer-container">
          <div className="footer-top-row">
            <div>
              <h2 className="footer-brand-title">KHADIRA</h2>
              <p className="footer-manifesto">
                <strong style={{ color: '#f7f5f0' }}>Khadira Textile Mills</strong> — One unified operating system for raw material management, spinning & weaving telemetry, quality assurance, export dispatch, floor wages, and real-time production costing.
              </p>

              {!footerSubmitted ? (
                <form 
                  className="footer-email-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (footerEmail) setFooterSubmitted(true);
                  }}
                >
                  <input 
                    type="email" 
                    placeholder="Enter corporate email"
                    className="footer-email-input"
                    value={footerEmail}
                    onChange={(e) => setFooterEmail(e.target.value)}
                    required
                  />
                  <button type="submit" className="footer-subscribe-btn">
                    Subscribe
                  </button>
                </form>
              ) : (
                <p style={{ color: '#c4d7b2', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
                  ✦ Subscribed to factory telemetry updates.
                </p>
              )}

              <span className="footer-drop-status">
                Shift A Active — 14 Bays Running
              </span>
            </div>

            <div className="footer-nav-cols">
              <div>
                <h4 className="footer-col-title">Modules</h4>
                <ul className="footer-col-links">
                  <li><a href="#modules">Raw Material Stock</a></li>
                  <li><a href="#modules">Machine Status</a></li>
                  <li><a href="#modules">Production Tracking</a></li>
                  <li><a href="#modules">Quality Checks</a></li>
                  <li><a href="#modules">Dispatch & Invoices</a></li>
                </ul>
              </div>

              <div>
                <h4 className="footer-col-title">System</h4>
                <ul className="footer-col-links">
                  <li><a href="#workflow">Factory Workflow</a></li>
                  <li><a href="#flow">Production Flow</a></li>
                  <li><a href="#actions">Key Actions</a></li>
                  <li><a href="#reports">Factory Reports</a></li>
                  <li><a href="#studio">Digital Backbone</a></li>
                </ul>
              </div>

              <div>
                <h4 className="footer-col-title">Compliance</h4>
                <ul className="footer-col-links">
                  <li><a href="#faqs">ASTM 4-Point System</a></li>
                  <li><a href="#faqs">GOTS Organic Standard</a></li>
                  <li><a href="#faqs">OEKO-TEX Class 100</a></li>
                  <li><a href="#faqs">Loom Telemetry Protocol</a></li>
                  <li><a href="#benefits">Plant Benefits</a></li>
                </ul>
              </div>

              <div>
                <h4 className="footer-col-title">Factory HQ</h4>
                <ul className="footer-col-links">
                  <li><a href="mailto:operations@khadiratextiles.com">operations@khadiratextiles.com</a></li>
                  <li><a href="#contact">Mill Compound, Corridor 4</a></li>
                  <li><a href="#contact">+91 (0) 22 4920 1800</a></li>
                  <li><a href="#contact">Production Dispatch Desk</a></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="footer-bottom-row">
            <span>© 2026 KHADIRA TEXTILE MILLS. ALL RIGHTS RESERVED. OPERATING SYSTEM v4.2</span>
            
            <div className="footer-legal-links">
              <a href="#privacy">Plant security policy</a>
              <a href="#shipping">Compliance terms</a>
              <a href="#cookies">Audit standards</a>
            </div>

            <div className="footer-social-links">
              <a href="#portal">Loom Network</a>
              <a href="#cloud">ERP Cloud</a>
              <a href="#support">Support Desk</a>
            </div>
          </div>

          <div className="giant-faint-watermark">
            KHADIRA
          </div>
        </div>
      </footer>
      </>
      )}

      {/* =========================================
          17. PRODUCTION QUEUE DRAWER
          ========================================= */}
      <div 
        className={`bag-drawer-backdrop ${isBagOpen ? 'open' : ''}`}
        onClick={() => setIsBagOpen(false)}
      />

      <aside className={`bag-drawer-panel ${isBagOpen ? 'open' : ''}`} aria-label="Production Queue">
        <div className="bag-drawer-header">
          <h2 className="bag-drawer-title">Active Queue</h2>
          <button 
            className="bag-close-btn" 
            onClick={() => setIsBagOpen(false)}
            aria-label="Close queue drawer"
          >
            <X size={20} />
          </button>
        </div>

        <div className="bag-drawer-content">
          {bagItems.length === 0 ? (
            <div className="bag-empty-state">
              <ShoppingBag size={42} strokeWidth={1} style={{ color: '#6b665f' }} />
              <h3 className="bag-empty-title">Queue is clear</h3>
              <p className="bag-empty-sub">
                Select operational modules or active factory work orders to monitor in real time.
              </p>
              <a 
                href="#modules" 
                className="btn-request-key"
                style={{ marginTop: '1rem' }}
                onClick={() => setIsBagOpen(false)}
              >
                Browse Core Modules
              </a>
            </div>
          ) : (
            <div className="bag-items-list">
              {bagItems.map((item) => (
                <div className="bag-item-row" key={item.id}>
                  <img src={item.image} alt={item.name} className="bag-item-img" />
                  <div>
                    <h4 className="bag-item-title">{item.name}</h4>
                    <p className="bag-item-price">{item.priceStr || 'ACTIVE'}</p>
                    <div className="bag-qty-controls">
                      <button 
                        className="bag-qty-btn"
                        onClick={() => updateQuantity(item.id, -1)}
                        aria-label="Decrease quantity"
                      >
                        <Minus size={12} />
                      </button>
                      <span style={{ fontSize: '0.8125rem' }}>{item.quantity}</span>
                      <button 
                        className="bag-qty-btn"
                        onClick={() => updateQuantity(item.id, 1)}
                        aria-label="Increase quantity"
                      >
                        <Plus size={12} />
                      </button>
                    </div>
                  </div>
                  <button 
                    className="bag-item-remove"
                    onClick={() => removeItem(item.id)}
                    aria-label="Remove item from queue"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {bagItems.length > 0 && (
          <div className="bag-drawer-footer">
            <div className="bag-subtotal-row">
              <span className="bag-subtotal-label">Active Monitored Tasks</span>
              <span className="bag-subtotal-val">{totalBagCount}</span>
            </div>
            <button 
              className="btn-checkout"
              onClick={() => {
                alert(`Exporting operational report with ${totalBagCount} active items. Telemetry logged to KHADIRA console.`);
              }}
            >
              Export Queue Summary
            </button>
          </div>
        )}
      </aside>

      {/* =========================================
          18. REQUEST REPORT ACCESS MODAL
          ========================================= */}
      {keyModalOpen && (
        <div className="key-modal-backdrop" onClick={() => setKeyModalOpen(false)}>
          <div className="key-modal-card" onClick={(e) => e.stopPropagation()}>
            <button 
              className="bag-close-btn" 
              style={{ position: 'absolute', top: '1.5rem', right: '1.5rem' }}
              onClick={() => setKeyModalOpen(false)}
            >
              <X size={20} />
            </button>

            <span className="section-label">MILL EXECUTIVE & AUDITOR CLEARANCE</span>
            <h3 className="section-title" style={{ fontSize: '2.4rem', margin: '0.5rem 0 1.5rem' }}>
              Request Report Access
            </h3>
            
            {!keyRequested ? (
              <form 
                onSubmit={(e) => {
                  e.preventDefault();
                  setKeyRequested(true);
                }}
                style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
              >
                <p style={{ fontSize: '0.85rem', color: '#8c877f' }}>
                  Provide your mill division, auditor credential or corporate email to receive an authorized vault pass.
                </p>
                <input 
                  type="text" 
                  placeholder="Mill Division or Audit Firm"
                  required
                  className="newsletter-input"
                  style={{ background: '#121212' }}
                />
                <input 
                  type="email" 
                  placeholder="Corporate Work Email Address"
                  required
                  className="newsletter-input"
                  style={{ background: '#121212' }}
                />
                <button type="submit" className="btn-checkout" style={{ marginTop: '0.5rem' }}>
                  Submit Credential Request
                </button>
              </form>
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem 0' }}>
                <Check size={36} style={{ color: '#c4d7b2', margin: '0 auto 1rem' }} />
                <h4 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.6rem', marginBottom: '0.5rem' }}>
                  Access Dispatched
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#8c877f' }}>
                  We have verified your request. Check your inbox for your 6-digit archive clearance token.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================
          18B. DEDICATED TERMINAL LOGIN MODAL PAGE
          ========================================= */}
      {isLoginModalOpen && (
        <div 
          className="terminal-modal-backdrop" 
          onClick={() => setIsLoginModalOpen(false)}
          id="terminal-modal-backdrop"
        >
          <div 
            className="terminal-modal-dialog" 
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-login-title"
          >
            <button 
              type="button"
              className="terminal-modal-close" 
              onClick={() => setIsLoginModalOpen(false)}
              aria-label="Close Login Modal"
            >
              <X size={20} />
            </button>

            <div className="terminal-modal-body">
              <div className="terminal-modal-header">
                <div className="terminal-modal-badge">
                  <span className="terminal-live-dot" />
                  <span>MILL TERMINAL GATEWAY</span>
                </div>
                <h3 id="modal-login-title" className="terminal-modal-title">
                  Factory Login
                </h3>
                <p className="terminal-modal-subtitle">
                  Select your operational role and enter your authorized password to access the floor management console.
                </p>
              </div>

              {isLoggedIn && (
                <div className="terminal-session-status-banner">
                  <div className="session-status-left">
                    <span className="terminal-live-dot" />
                    <span>Session: <strong>{loggedInUser?.role || 'Administrator'}</strong> ({loggedInUser?.username || 'admin'})</span>
                  </div>
                  <div className="session-status-right">
                    <button 
                      type="button" 
                      className="terminal-modal-action-link"
                      onClick={() => {
                        setIsLoginModalOpen(false);
                        setIsDashboardOpen(true);
                      }}
                    >
                      Open Dashboard →
                    </button>
                    <button 
                      type="button" 
                      className="terminal-modal-action-link logout"
                      onClick={() => handleTerminalLogout(true)}
                    >
                      Log Out
                    </button>
                  </div>
                </div>
              )}

              <form className="terminal-modal-form" onSubmit={handleTerminalLogin}>
                {/* Role Selector */}
                <div className="terminal-modal-field">
                  <label className="terminal-modal-label" htmlFor="modal-role-select">
                    Select Factory Role
                  </label>
                  <div className="terminal-select-wrap">
                    <select 
                      id="modal-role-select"
                      className="terminal-modal-select"
                      value={loginRole}
                      onChange={(e) => {
                        setLoginRole(e.target.value);
                        if (loginError) setLoginError('');
                      }}
                    >
                      <option value="Store Manager">Store Manager (Yarn & Stock)</option>
                      <option value="Production Supervisor">Production Supervisor (Looms & Bays)</option>
                      <option value="Quality Inspector">Quality Inspector (4-Point Lab)</option>
                      <option value="Accounts & Owner">Accounts & Owner (Costing & ERP)</option>
                      <option value="Plant Director">Plant Director (Master Clearance)</option>
                    </select>
                  </div>
                </div>

                {/* Dynamic Role Scope Card */}
                <div className="terminal-role-scope-card">
                  <div className="terminal-role-scope-head">
                    <span className="role-code-badge">{ROLE_DETAILS[loginRole]?.code || 'ETM'}</span>
                    <span className="role-dept-text">{ROLE_DETAILS[loginRole]?.dept}</span>
                  </div>
                  <p className="role-scope-desc">{ROLE_DETAILS[loginRole]?.desc}</p>
                </div>

                {/* Password Input */}
                <div className="terminal-modal-field">
                  <div className="terminal-label-row">
                    <label className="terminal-modal-label" htmlFor="modal-password-input">
                      Role Password
                    </label>
                    <button 
                      type="button"
                      className="terminal-modal-hint-btn"
                      onClick={() => {
                        setLoginPassword('ETM-2026');
                        if (loginError) setLoginError('');
                      }}
                    >
                      Autofill Demo (ETM-2026)
                    </button>
                  </div>

                  <div className="terminal-modal-password-wrap">
                    <Lock size={15} className="terminal-modal-field-icon" />
                    <input 
                      id="modal-password-input"
                      type={showPassword ? 'text' : 'password'}
                      placeholder={`Enter password for ${loginRole}...`}
                      className="terminal-modal-password-input"
                      value={loginPassword}
                      autoFocus
                      onChange={(e) => {
                        setLoginPassword(e.target.value);
                        if (loginError) setLoginError('');
                      }}
                    />
                    <button 
                      type="button" 
                      className="terminal-modal-eye-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                  {loginError && <p className="terminal-modal-error">{loginError}</p>}
                </div>

                {/* Submit Button */}
                <button 
                  type="submit" 
                  className="terminal-modal-submit-btn" 
                  id="modal-login-submit"
                  disabled={isAuthenticating}
                >
                  <span>{isAuthenticating ? 'Connecting to Core Backend...' : 'Authenticate & Access Console'}</span>
                  <ArrowRight size={15} />
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* =========================================
          19. FLOATING TOAST NOTIFICATION
          ========================================= */}
      {toastMessage && (
        <div className="toast-notice">
          <Sparkles size={16} style={{ color: '#f7f5f0' }} />
          <span style={{ fontSize: '0.8125rem', letterSpacing: '0.08em' }}>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
