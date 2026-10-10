"use client";

import { useEffect, useState } from "react";
import { 
  Factory, 
  Package, 
  CircleDollarSign, 
  ClipboardCheck,
  TrendingUp,
  Activity,
  AlertTriangle,
  LogOut,
  Bell,
  Search,
  Menu
} from "lucide-react";
import axios from "axios";

// Formatting utils
const formatCurrency = (paise: number) => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);
};

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // For demo purposes, we will mock the backend call if it fails or simulate it
    const load = async () => {
      try {
        // Auto-login for demo purposes to establish the session cookie
        await axios.post("http://localhost:8000/api/auth/login", {
          username: "admin",
          password: "admin123"
        }, { withCredentials: true });

        // Now fetch dashboard data with the newly set cookie
        const res = await axios.get("http://localhost:8000/api/dashboard/", {
          withCredentials: true
        });
        setData(res.data);
      } catch (e) {
        console.error("Dashboard fetch failed. Using fallback data for demo.", e);
        setData({
          order_counts: { pending: 12, in_production: 5, qc: 3, ready: 8, dispatched: 24 },
          machine_summary: { running: 4, idle: 2, maintenance: 1 },
          low_stock_alerts: [
            { id: 1, sku: "YRN-CTN-BLU", name: "Cotton Yarn - Blue", stock_quantity: 150000, reorder_point: 300000, unit: "kg" }
          ],
          outstanding_receivables_paise: 12500000, // 1.25L
          qc_pending_rolls: 14,
          total_machines: 7
        });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const {
    order_counts,
    machine_summary,
    low_stock_alerts,
    outstanding_receivables_paise,
    qc_pending_rolls,
    total_machines
  } = data || {};

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* Sidebar Navigation */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-slate-200 hidden lg:block z-10 fade-in">
        <div className="flex h-16 shrink-0 items-center px-6 border-b border-slate-100">
          <Factory className="h-6 w-6 text-primary mr-2" />
          <span className="font-bold text-lg tracking-tight text-slate-900">Khadira</span>
        </div>
        <nav className="flex flex-1 flex-col px-4 py-6 space-y-1">
          <a href="#" className="bg-primary/10 text-primary group flex items-center px-3 py-2.5 text-sm font-medium rounded-md">
            <Activity className="text-primary mr-3 h-5 w-5" />
            Dashboard
          </a>
          <a href="#" className="text-slate-600 hover:bg-slate-50 hover:text-slate-900 group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors">
            <Package className="text-slate-400 group-hover:text-slate-500 mr-3 h-5 w-5" />
            Inventory & Stock
          </a>
          <a href="#" className="text-slate-600 hover:bg-slate-50 hover:text-slate-900 group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors">
            <ClipboardCheck className="text-slate-400 group-hover:text-slate-500 mr-3 h-5 w-5" />
            Production & QC
          </a>
          <a href="#" className="text-slate-600 hover:bg-slate-50 hover:text-slate-900 group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors">
            <TrendingUp className="text-slate-400 group-hover:text-slate-500 mr-3 h-5 w-5" />
            Orders & Dispatch
          </a>
          <a href="#" className="text-slate-600 hover:bg-slate-50 hover:text-slate-900 group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors">
            <CircleDollarSign className="text-slate-400 group-hover:text-slate-500 mr-3 h-5 w-5" />
            Finance & Wages
          </a>
        </nav>
      </aside>

      {/* Main Content */}
      <div className="lg:pl-64 flex flex-col flex-1">
        {/* Top Header */}
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-x-4 border-b border-slate-200 bg-white/80 backdrop-blur-md px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <button type="button" className="-m-2.5 p-2.5 text-slate-700 lg:hidden">
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <form className="relative flex flex-1" action="#" method="GET">
              <Search className="absolute inset-y-0 left-0 h-full w-5 text-slate-400 pointer-events-none ml-2" aria-hidden="true" />
              <input
                id="search-field"
                className="block h-full w-full border-0 py-0 pl-10 pr-0 text-slate-900 placeholder:text-slate-400 focus:ring-0 sm:text-sm bg-transparent"
                placeholder="Search orders, rolls, or invoices..."
                type="search"
                name="search"
              />
            </form>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              <button type="button" className="-m-2.5 p-2.5 text-slate-400 hover:text-slate-500">
                <span className="sr-only">View notifications</span>
                <Bell className="h-6 w-6" aria-hidden="true" />
              </button>
              <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-slate-200" aria-hidden="true" />
              <button className="flex items-center p-1.5 hover:bg-slate-50 rounded-full transition-colors">
                <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                  A
                </div>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 pb-10">
          <div className="px-4 sm:px-6 lg:px-8 py-8 fade-in">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
              <div>
                <h1 className="text-2xl font-bold leading-7 text-slate-900 sm:truncate sm:text-3xl sm:tracking-tight">
                  Mill Overview
                </h1>
                <p className="mt-1 text-sm text-slate-500">Real-time metrics for production, inventory, and finance.</p>
              </div>
              <div className="mt-4 flex md:ml-4 md:mt-0">
                <button type="button" className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
                  Generate Report
                </button>
                <button type="button" className="ml-3 inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                  New Order
                </button>
              </div>
            </div>

            {/* Stats Grid */}
            <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
              <div className="relative overflow-hidden rounded-xl bg-white px-4 pb-12 pt-5 shadow-sm ring-1 ring-slate-200 sm:px-6 sm:pt-6 group hover:shadow-md transition-shadow">
                <dt>
                  <div className="absolute rounded-md bg-blue-500/10 p-3">
                    <Activity className="h-6 w-6 text-blue-600" aria-hidden="true" />
                  </div>
                  <p className="ml-16 truncate text-sm font-medium text-slate-500">Active Machines</p>
                </dt>
                <dd className="ml-16 flex items-baseline pb-6 sm:pb-7">
                  <p className="text-2xl font-semibold text-slate-900">
                    {machine_summary?.running || 0} <span className="text-sm text-slate-400 font-normal">/ {total_machines}</span>
                  </p>
                </dd>
                <div className="absolute inset-x-0 bottom-0 bg-slate-50 px-4 py-4 sm:px-6 border-t border-slate-100">
                  <div className="text-sm"><a href="#" className="font-medium text-blue-600 hover:text-blue-500">View machines<span className="sr-only"> Active Machines</span></a></div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-xl bg-white px-4 pb-12 pt-5 shadow-sm ring-1 ring-slate-200 sm:px-6 sm:pt-6 group hover:shadow-md transition-shadow">
                <dt>
                  <div className="absolute rounded-md bg-emerald-500/10 p-3">
                    <TrendingUp className="h-6 w-6 text-emerald-600" aria-hidden="true" />
                  </div>
                  <p className="ml-16 truncate text-sm font-medium text-slate-500">Production Orders</p>
                </dt>
                <dd className="ml-16 flex items-baseline pb-6 sm:pb-7">
                  <p className="text-2xl font-semibold text-slate-900">{order_counts?.in_production || 0}</p>
                </dd>
                <div className="absolute inset-x-0 bottom-0 bg-slate-50 px-4 py-4 sm:px-6 border-t border-slate-100">
                  <div className="text-sm"><a href="#" className="font-medium text-emerald-600 hover:text-emerald-500">Track progress<span className="sr-only"> Production Orders</span></a></div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-xl bg-white px-4 pb-12 pt-5 shadow-sm ring-1 ring-slate-200 sm:px-6 sm:pt-6 group hover:shadow-md transition-shadow">
                <dt>
                  <div className="absolute rounded-md bg-amber-500/10 p-3">
                    <ClipboardCheck className="h-6 w-6 text-amber-600" aria-hidden="true" />
                  </div>
                  <p className="ml-16 truncate text-sm font-medium text-slate-500">Rolls Awaiting QC</p>
                </dt>
                <dd className="ml-16 flex items-baseline pb-6 sm:pb-7">
                  <p className="text-2xl font-semibold text-slate-900">{qc_pending_rolls || 0}</p>
                </dd>
                <div className="absolute inset-x-0 bottom-0 bg-slate-50 px-4 py-4 sm:px-6 border-t border-slate-100">
                  <div className="text-sm"><a href="#" className="font-medium text-amber-600 hover:text-amber-500">Start inspection<span className="sr-only"> QC Rolls</span></a></div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-xl bg-white px-4 pb-12 pt-5 shadow-sm ring-1 ring-slate-200 sm:px-6 sm:pt-6 group hover:shadow-md transition-shadow">
                <dt>
                  <div className="absolute rounded-md bg-purple-500/10 p-3">
                    <CircleDollarSign className="h-6 w-6 text-purple-600" aria-hidden="true" />
                  </div>
                  <p className="ml-16 truncate text-sm font-medium text-slate-500">Outstanding Receivables</p>
                </dt>
                <dd className="ml-16 flex items-baseline pb-6 sm:pb-7">
                  <p className="text-2xl font-semibold text-slate-900">
                    {formatCurrency(outstanding_receivables_paise || 0)}
                  </p>
                </dd>
                <div className="absolute inset-x-0 bottom-0 bg-slate-50 px-4 py-4 sm:px-6 border-t border-slate-100">
                  <div className="text-sm"><a href="#" className="font-medium text-purple-600 hover:text-purple-500">View invoices<span className="sr-only"> Receivables</span></a></div>
                </div>
              </div>
            </dl>

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
              {/* Active Orders Table */}
              <div className="rounded-xl bg-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
                <div className="px-4 py-5 sm:px-6 border-b border-slate-200 flex justify-between items-center">
                  <h3 className="text-base font-semibold leading-6 text-slate-900">Order Pipeline</h3>
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800">
                    Active overview
                  </span>
                </div>
                <div className="px-4 py-5 sm:p-6">
                  <div className="space-y-4">
                    {[
                      { status: "Pending", count: order_counts?.pending, color: "bg-slate-400" },
                      { status: "In Production", count: order_counts?.in_production, color: "bg-blue-500" },
                      { status: "In QC", count: order_counts?.qc, color: "bg-amber-500" },
                      { status: "Ready to Dispatch", count: order_counts?.ready, color: "bg-emerald-500" },
                    ].map((item) => (
                      <div key={item.status} className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div className={`h-2.5 w-2.5 rounded-full ${item.color} mr-3`}></div>
                          <span className="text-sm font-medium text-slate-700">{item.status}</span>
                        </div>
                        <span className="text-sm font-semibold text-slate-900">{item.count || 0}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6 pt-6 border-t border-slate-100">
                    <a href="#" className="text-sm font-medium text-primary hover:text-primary/80">View all orders &rarr;</a>
                  </div>
                </div>
              </div>

              {/* Alerts Panel */}
              <div className="rounded-xl bg-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
                <div className="px-4 py-5 sm:px-6 border-b border-slate-200">
                  <h3 className="text-base font-semibold leading-6 text-slate-900 flex items-center">
                    <AlertTriangle className="h-5 w-5 text-amber-500 mr-2" />
                    Attention Required
                  </h3>
                </div>
                <div className="px-4 py-5 sm:p-6">
                  {low_stock_alerts && low_stock_alerts.length > 0 ? (
                    <ul className="divide-y divide-slate-100">
                      {low_stock_alerts.map((alert: any, idx: number) => (
                        <li key={idx} className="py-3 flex justify-between items-center">
                          <div>
                            <p className="text-sm font-medium text-slate-900">{alert.name}</p>
                            <p className="text-xs text-slate-500">SKU: {alert.sku}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-red-600">{(alert.stock_quantity / 1000).toFixed(1)} {alert.unit}</p>
                            <p className="text-xs text-slate-500">Reorder at {(alert.reorder_point / 1000).toFixed(1)}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center py-6 text-slate-500 text-sm">
                      No urgent alerts right now.
                    </div>
                  )}
                  <div className="mt-6 pt-4 border-t border-slate-100">
                    <button className="w-full text-center text-sm font-medium text-primary hover:text-primary/80">
                      Generate Purchase Order
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
