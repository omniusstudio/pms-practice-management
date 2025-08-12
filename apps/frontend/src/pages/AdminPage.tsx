import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../utils/http-client";
import { Logger } from "../utils/logger";
import { RoleGuard } from "../components/ProtectedRoute";
import { useFeatureFlag } from "../hooks/useFeatureFlags";

// Types for admin data
interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  roles: string[];
  permissions: string[];
  is_active: boolean;
  is_admin: boolean;
}

interface UserResponse {
  data: User[];
  message?: string;
  success: boolean;
  correlation_id?: string;
}

interface RolePermission {
  name: string;
  description: string;
  permissions: string[];
}

interface RolesResponse {
  data: Record<string, RolePermission>;
  message?: string;
  success: boolean;
  correlation_id?: string;
}

interface UserRoleUpdateRequest {
  user_id: string;
  roles: string[];
}

const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [rolesInfo, setRolesInfo] = useState<Record<string, RolePermission>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [updating, setUpdating] = useState(false);
  const [activeTab, setActiveTab] = useState<"users" | "roles">("users");

  // Feature flag for enhanced admin UI
  const { isEnabled: advancedAdminEnabled } = useFeatureFlag("advanced_admin_ui", false);

  useEffect(() => {
    fetchData();
  }, [roleFilter]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch users and roles info in parallel
      const [usersResponse, rolesResponse] = await Promise.all([
        api.get<UserResponse>(`/admin/users${roleFilter ? `?role_filter=${roleFilter}` : ""}`),
        api.get<RolesResponse>("/admin/roles"),
      ]);

      setUsers(usersResponse.data || []);
      setRolesInfo(rolesResponse.data || {});

      Logger.info("Admin data loaded successfully", {
        component: "AdminPage",
        usersCount: usersResponse.data?.length || 0,
        rolesCount: Object.keys(rolesResponse.data || {}).length,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load admin data";
      setError(errorMessage);
      Logger.error("Failed to fetch admin data", err as Error, {
        component: "AdminPage",
        roleFilter,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUserRoles = async (userId: string, newRoles: string[]) => {
    try {
      setUpdating(true);

      const updateRequest: UserRoleUpdateRequest = {
        user_id: userId,
        roles: newRoles,
      };

      await api.put(`/admin/users/${userId}/roles`, updateRequest);

      // Refresh the users list
      await fetchData();

      setShowRoleModal(false);
      setSelectedUser(null);

      Logger.auditAction("role_update_success", "admin_ui", user?.id || "unknown", {
        component: "AdminPage",
        targetUserId: userId,
        newRoles,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update user roles";
      setError(errorMessage);
      Logger.error("Failed to update user roles", err as Error, {
        component: "AdminPage",
        targetUserId: userId,
        newRoles,
      });
    } finally {
      setUpdating(false);
    }
  };

  const openRoleModal = (selectedUser: User) => {
    setSelectedUser(selectedUser);
    setShowRoleModal(true);
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-red-100 text-red-800";
      case "clinician":
        return "bg-blue-100 text-blue-800";
      case "biller":
        return "bg-green-100 text-green-800";
      case "front_desk":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
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
              <h3 className="text-sm font-medium text-red-800">Error Loading Admin Dashboard</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-4">
                <button
                  onClick={fetchData}
                  className="bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <RoleGuard requiredRoles={["admin"]}>
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="mt-2 text-gray-600">
                HIPAA-compliant user and role management for Practice Management System
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {advancedAdminEnabled && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Advanced UI Enabled
                </span>
              )}
              <button
                onClick={fetchData}
                disabled={loading}
                className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab("users")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "users"
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              User Management ({users.length})
            </button>
            <button
              onClick={() => setActiveTab("roles")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "roles"
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Role Information ({Object.keys(rolesInfo).length})
            </button>
          </nav>
        </div>

        {/* Users Tab */}
        {activeTab === "users" && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-4">
                  <div>
                    <label
                      htmlFor="role-filter"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Filter by Role
                    </label>
                    <select
                      id="role-filter"
                      value={roleFilter}
                      onChange={(e) => setRoleFilter(e.target.value)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                    >
                      <option value="">All Roles</option>
                      {Object.keys(rolesInfo).map((role) => (
                        <option key={role} value={role}>
                          {rolesInfo[role].name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="mt-4 md:mt-0">
                  <span className="text-sm text-gray-500">Total Users: {users.length}</span>
                </div>
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white shadow overflow-hidden sm:rounded-lg">
              <div className="px-4 py-5 sm:px-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900">System Users</h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-500">
                  Manage user roles and permissions for the Practice Management System.
                </p>
              </div>
              <div className="border-t border-gray-200">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          User
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Roles
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Permissions
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {users.map((userData) => (
                        <tr key={userData.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="flex-shrink-0 h-10 w-10">
                                <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                                  <span className="text-sm font-medium text-gray-700">
                                    {(userData.display_name || userData.email)
                                      .charAt(0)
                                      .toUpperCase()}
                                  </span>
                                </div>
                              </div>
                              <div className="ml-4">
                                <div className="text-sm font-medium text-gray-900">
                                  {userData.display_name ||
                                    `${userData.first_name} ${userData.last_name}`.trim() ||
                                    "Unknown"}
                                </div>
                                <div className="text-sm text-gray-500">{userData.email}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex flex-wrap gap-1">
                              {userData.roles.map((role) => (
                                <span
                                  key={role}
                                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(
                                    role,
                                  )}`}
                                >
                                  {role}
                                </span>
                              ))}
                              {userData.roles.length === 0 && (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                                  No roles
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                userData.is_active
                                  ? "bg-green-100 text-green-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {userData.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {userData.permissions.length} permissions
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => openRoleModal(userData)}
                              className="text-indigo-600 hover:text-indigo-900 mr-4"
                            >
                              Manage Roles
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Roles Tab */}
        {activeTab === "roles" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.entries(rolesInfo).map(([roleKey, roleInfo]) => (
                <div key={roleKey} className="bg-white overflow-hidden shadow rounded-lg">
                  <div className="px-4 py-5 sm:p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRoleBadgeColor(
                            roleKey,
                          )}`}
                        >
                          {roleKey}
                        </span>
                      </div>
                    </div>
                    <div className="mt-3">
                      <h3 className="text-lg font-medium text-gray-900">{roleInfo.name}</h3>
                      <p className="mt-2 text-sm text-gray-500">{roleInfo.description}</p>
                    </div>
                    <div className="mt-4">
                      <h4 className="text-sm font-medium text-gray-900">Permissions:</h4>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {roleInfo.permissions.map((permission) => (
                          <span
                            key={permission}
                            className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800"
                          >
                            {permission}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 text-xs text-gray-500">
                      {users.filter((u) => u.roles.includes(roleKey)).length} users with this role
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Role Assignment Modal */}
        {showRoleModal && selectedUser && (
          <RoleAssignmentModal
            user={selectedUser}
            availableRoles={rolesInfo}
            onUpdate={handleUpdateUserRoles}
            onClose={() => {
              setShowRoleModal(false);
              setSelectedUser(null);
            }}
            updating={updating}
          />
        )}
      </div>
    </RoleGuard>
  );
};

// Role Assignment Modal Component
interface RoleAssignmentModalProps {
  user: User;
  availableRoles: Record<string, RolePermission>;
  onUpdate: (userId: string, roles: string[]) => Promise<void>;
  onClose: () => void;
  updating: boolean;
}

const RoleAssignmentModal: React.FC<RoleAssignmentModalProps> = ({
  user,
  availableRoles,
  onUpdate,
  onClose,
  updating,
}) => {
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user.roles);

  const handleRoleToggle = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role],
    );
  };

  const handleSubmit = async () => {
    await onUpdate(user.id, selectedRoles);
  };

  const hasChanges = JSON.stringify(selectedRoles.sort()) !== JSON.stringify(user.roles.sort());

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Manage User Roles</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              disabled={updating}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <div className="mb-4">
            <div className="text-sm text-gray-600">
              <strong>User:</strong> {user.display_name || user.email}
            </div>
            <div className="text-sm text-gray-500">{user.email}</div>
          </div>

          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-700">Select Roles:</label>
            {Object.entries(availableRoles).map(([roleKey, roleInfo]) => (
              <div key={roleKey} className="flex items-start">
                <div className="flex items-center h-5">
                  <input
                    id={`role-${roleKey}`}
                    type="checkbox"
                    checked={selectedRoles.includes(roleKey)}
                    onChange={() => handleRoleToggle(roleKey)}
                    disabled={updating}
                    className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                  />
                </div>
                <div className="ml-3 text-sm">
                  <label htmlFor={`role-${roleKey}`} className="font-medium text-gray-700">
                    {roleInfo.name}
                  </label>
                  <p className="text-gray-500">{roleInfo.description}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={onClose}
              disabled={updating}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={updating || !hasChanges}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
            >
              {updating ? "Updating..." : "Update Roles"}
            </button>
          </div>

          {hasChanges && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <div className="text-sm text-blue-800">
                <p className="font-medium">Changes will be applied:</p>
                <ul className="mt-1 list-disc list-inside">
                  {selectedRoles
                    .filter((role) => !user.roles.includes(role))
                    .map((role) => (
                      <li key={role}>Add: {availableRoles[role]?.name || role}</li>
                    ))}
                  {user.roles
                    .filter((role) => !selectedRoles.includes(role))
                    .map((role) => (
                      <li key={role}>Remove: {availableRoles[role]?.name || role}</li>
                    ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
