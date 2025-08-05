import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useHttpClient } from "../utils/http-client";
import { Logger } from "../utils/logger";

// Dashboard stats interface
interface DashboardStats {
  totalPatients: number;
  todayAppointments: number;
  pendingBilling: number;
  systemAlerts: number;
}

// Quick action interface
interface QuickAction {
  name: string;
  href: string;
  icon: string;
  description: string;
  requiredRoles: readonly string[];
}

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { api } = useHttpClient();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick actions based on user roles
  const quickActions: QuickAction[] = [
    {
      name: "New Patient",
      href: "/patients/new",
      icon: "UserPlusIcon",
      description: "Register a new patient",
      requiredRoles: ["clinician", "admin", "staff"],
    },
    {
      name: "Schedule Appointment",
      href: "/appointments/new",
      icon: "CalendarPlusIcon",
      description: "Book a new appointment",
      requiredRoles: ["clinician", "admin", "staff"],
    },
    {
      name: "Patient Search",
      href: "/patients",
      icon: "SearchIcon",
      description: "Find patient records",
      requiredRoles: ["clinician", "admin", "staff"],
    },
    {
      name: "Billing Review",
      href: "/billing",
      icon: "CreditCardIcon",
      description: "Review pending billing",
      requiredRoles: ["admin", "billing"],
    },
    {
      name: "Reports",
      href: "/reports",
      icon: "ChartBarIcon",
      description: "View analytics and reports",
      requiredRoles: ["admin"],
    },
    {
      name: "System Settings",
      href: "/settings",
      icon: "CogIcon",
      description: "Configure system settings",
      requiredRoles: ["admin"],
    },
  ];

  // Icons (using inline SVG)
  const Icons = {
    UserPlusIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
        />
      </svg>
    ),
    CalendarPlusIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
        />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11v6m3-3H9" />
      </svg>
    ),
    SearchIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    ),
    CreditCardIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
        />
      </svg>
    ),
    ChartBarIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    CogIcon: () => (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  };

  // Check if user has required roles for an action
  const hasRequiredRole = (requiredRoles: readonly string[]): boolean => {
    if (!user?.roles || requiredRoles.length === 0) return false;
    return requiredRoles.some((role) => user.roles.includes(role));
  };

  // Get icon component
  const getIconComponent = (iconName: string) => {
    const IconComponent = Icons[iconName as keyof typeof Icons];
    return IconComponent ? <IconComponent /> : <Icons.SearchIcon />;
  };

  // Fetch dashboard stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);

        // Mock data for now - replace with actual API call
        // const response = await api.get('/api/dashboard/stats');
        // setStats(response.data);

        // Simulate API delay
        await new Promise((resolve) => setTimeout(resolve, 1000));

        // Mock stats data
        const mockStats: DashboardStats = {
          totalPatients: 1247,
          todayAppointments: 23,
          pendingBilling: 156,
          systemAlerts: 2,
        };

        setStats(mockStats);

        Logger.info("Dashboard stats loaded", {
          component: "DashboardPage",
          action: "fetch_stats",
          userId: user?.id,
        });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load dashboard data";
        setError(errorMessage);

        Logger.error("Failed to fetch dashboard stats", err as Error, {
          component: "DashboardPage",
          action: "fetch_stats_failed",
          userId: user?.id,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [api, user?.id]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {getGreeting()}, {user?.name || "User"}!
        </h1>
        <p className="mt-1 text-sm text-gray-600">Welcome to your practice management dashboard</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {loading ? (
          // Loading skeleton
          Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="bg-white overflow-hidden shadow rounded-lg animate-pulse">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 bg-gray-300 rounded"></div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
                    <div className="h-6 bg-gray-300 rounded w-1/2"></div>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : error ? (
          <div className="col-span-full bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error loading dashboard data</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                </div>
              </div>
            </div>
          </div>
        ) : stats ? (
          [
            {
              name: "Total Patients",
              value: stats.totalPatients.toLocaleString(),
              icon: "👥",
              color: "text-blue-600",
              bgColor: "bg-blue-100",
            },
            {
              name: "Today's Appointments",
              value: stats.todayAppointments.toString(),
              icon: "📅",
              color: "text-green-600",
              bgColor: "bg-green-100",
            },
            {
              name: "Pending Billing",
              value: stats.pendingBilling.toLocaleString(),
              icon: "💳",
              color: "text-yellow-600",
              bgColor: "bg-yellow-100",
            },
            {
              name: "System Alerts",
              value: stats.systemAlerts.toString(),
              icon: "⚠️",
              color: stats.systemAlerts > 0 ? "text-red-600" : "text-gray-600",
              bgColor: stats.systemAlerts > 0 ? "bg-red-100" : "bg-gray-100",
            },
          ].map((stat) => (
            <div key={stat.name} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`${stat.bgColor} rounded-md p-3`}>
                      <span className="text-lg">{stat.icon}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">{stat.name}</dt>
                      <dd className={`text-lg font-medium ${stat.color}`}>{stat.value}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : null}
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {quickActions
            .filter((action) => hasRequiredRole(action.requiredRoles))
            .map((action) => (
              <Link
                key={action.name}
                to={action.href}
                className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200 hover:border-indigo-300 group"
              >
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-indigo-600 group-hover:text-indigo-700">
                      {getIconComponent(action.icon)}
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-900 group-hover:text-indigo-900">
                      {action.name}
                    </h3>
                    <p className="text-sm text-gray-500">{action.description}</p>
                  </div>
                </div>
              </Link>
            ))}
        </div>
      </div>

      {/* Recent Activity Placeholder */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Recent Activity</h3>
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No recent activity</h3>
            <p className="mt-1 text-sm text-gray-500">
              Recent patient interactions and system events will appear here.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
