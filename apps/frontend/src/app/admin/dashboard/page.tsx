"use client";

import { FormEvent, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { StatCard } from "@/components/dashboard/StatCard";
import { EventList } from "@/components/dashboard/EventList";
import {
  changeUserRole,
  getAdminAudit,
  getAdminHealth,
  getMe,
  inviteOrgUser,
  listOrgUsers,
} from "@/lib/api";

export default function AdminDashboardPage() {
  const queryClient = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("driver");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then((me) => setOrgId(me.org_id || null))
      .catch(() => setOrgId(null));
  }, []);

  const healthQuery = useQuery({
    queryKey: ["admin-health"],
    queryFn: getAdminHealth,
  });
  const auditQuery = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () => getAdminAudit(40),
  });
  const usersQuery = useQuery({
    queryKey: ["admin-users", orgId],
    enabled: Boolean(orgId),
    queryFn: () => listOrgUsers(orgId!),
  });

  const onInvite = async (event: FormEvent) => {
    event.preventDefault();
    if (!orgId) return;
    setMessage(null);
    try {
      await inviteOrgUser(orgId, { email, role });
      setEmail("");
      setMessage(`Invited ${email} as ${role}`);
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-audit"] });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Invite failed");
    }
  };

  const health = healthQuery.data;
  const auditEvents = (auditQuery.data?.items || []).map((item) => ({
    id: item.id,
    event_type: item.action,
    severity: "LOW",
    timestamp: item.created_at,
  }));

  return (
    <RoleShell subtitle="Invites, roles, audit trail, and system health">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Environment"
          value={health?.environment || "—"}
          accent="fuchsia"
        />
        <StatCard
          label="Database"
          value={health?.database || "—"}
          accent={health?.database === "ok" ? "emerald" : "rose"}
        />
        <StatCard
          label="Redis"
          value={health?.redis || "—"}
          accent={health?.redis === "ok" ? "emerald" : "amber"}
        />
        <StatCard
          label="Users in org"
          value={usersQuery.data?.length ?? "—"}
          accent="sky"
        />
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="mb-3 text-sm font-semibold">Invite user</h2>
          {!orgId ? (
            <p className="text-sm text-slate-500">
              Sign in as org_admin with an organization to invite users.
            </p>
          ) : (
            <form onSubmit={onInvite} className="space-y-3">
              <input
                type="email"
                required
                placeholder="email@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              >
                <option value="driver">driver</option>
                <option value="fleet_manager">fleet_manager</option>
                <option value="maintenance_tech">maintenance_tech</option>
                <option value="org_admin">org_admin</option>
              </select>
              <button
                type="submit"
                className="rounded-xl bg-fuchsia-600 px-4 py-2 text-sm font-semibold hover:bg-fuchsia-500"
              >
                Send invite
              </button>
              {message ? (
                <p className="text-xs text-slate-400">{message}</p>
              ) : null}
            </form>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="mb-3 text-sm font-semibold">Org users</h2>
          <ul className="max-h-64 space-y-2 overflow-auto text-sm">
            {(usersQuery.data || []).map((user) => (
              <li
                key={user.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 px-3 py-2"
              >
                <div>
                  <p className="font-medium">{user.email}</p>
                  <p className="text-xs text-slate-500">{user.role}</p>
                </div>
                <select
                  value={user.role}
                  onChange={async (e) => {
                    await changeUserRole(user.id, e.target.value);
                    await queryClient.invalidateQueries({
                      queryKey: ["admin-users"],
                    });
                    await queryClient.invalidateQueries({
                      queryKey: ["admin-audit"],
                    });
                  }}
                  className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
                >
                  <option value="driver">driver</option>
                  <option value="fleet_manager">fleet_manager</option>
                  <option value="maintenance_tech">maintenance_tech</option>
                  <option value="org_admin">org_admin</option>
                  <option value="super_admin">super_admin</option>
                </select>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-200">Audit log</h2>
        <EventList events={auditEvents} emptyLabel="No audit events yet" />
      </div>
    </RoleShell>
  );
}
