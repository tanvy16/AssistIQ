import { describe, expect, it } from "vitest";

import { getNavigationForRole, navigationByRole } from "./navigation";
import { getRoleHomePath } from "./routes";

describe("getRoleHomePath", () => {
  it("maps each role to its dashboard route", () => {
    expect(getRoleHomePath("employee")).toBe("/app/employee");
    expect(getRoleHomePath("agent")).toBe("/app/agent");
    expect(getRoleHomePath("admin")).toBe("/app/admin");
  });
});

describe("navigationByRole", () => {
  it("defines employee navigation items", () => {
    const items = getNavigationForRole("employee");
    expect(items.map((item) => item.path)).toEqual([
      "/app/employee",
      "/app/employee/chat",
      "/app/employee/tickets",
      "/app/employee/knowledge",
      "/app/employee/it-requests",
      "/app/employee/password-reset",
      "/app/employee/security",
    ]);
  });

  it("gives every role its own Security settings page", () => {
    for (const role of ["employee", "agent", "admin"] as const) {
      expect(getNavigationForRole(role).some((item) => item.path === `/app/${role}/security`)).toBe(true);
    }
  });

  it("has no duplicate destinations in any role's navigation", () => {
    for (const role of ["employee", "agent", "admin"] as const) {
      const paths = getNavigationForRole(role).map((item) => item.path);
      expect(new Set(paths).size).toBe(paths.length);
    }
  });

  it("defines agent navigation items including queue and knowledge", () => {
    const items = getNavigationForRole("agent");
    expect(items.some((item) => item.path === "/app/agent/queue")).toBe(true);
    expect(items.some((item) => item.path === "/app/agent/knowledge")).toBe(true);
    expect(items.some((item) => item.path === "/app/agent/it-requests")).toBe(true);
    expect(items.some((item) => item.path === "/app/agent/password-resets")).toBe(true);
  });

  it("defines admin knowledge and AI model routes", () => {
    const items = getNavigationForRole("admin");
    expect(items.some((item) => item.path === "/app/admin/knowledge")).toBe(true);
    expect(items.some((item) => item.path === "/app/admin/it-requests")).toBe(true);
    expect(items.some((item) => item.path === "/app/admin/password-resets")).toBe(true);
    expect(items.some((item) => item.path === "/app/admin/observability")).toBe(true);
  });

  it("defines admin navigation items", () => {
    const items = getNavigationForRole("admin");
    expect(items.map((item) => item.label)).toContain("Tickets");
    expect(items.map((item) => item.label)).toContain("Audit Log");
  });

  it("covers all three roles", () => {
    expect(Object.keys(navigationByRole).sort()).toEqual([
      "admin",
      "agent",
      "employee",
    ]);
  });
});
