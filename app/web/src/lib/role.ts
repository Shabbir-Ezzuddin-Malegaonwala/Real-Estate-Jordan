import { useCallback, useEffect, useState } from "react";
import type { Role } from "../types";

const KEY = "workspace-role";

function storedRole(): Role | null {
  const v = localStorage.getItem(KEY);
  return v === "builder" || v === "agent" || v === "buyer" ? v : null;
}

// The chosen role reshapes the workspace (which primary panel is dominant) over
// the SAME map + evidence base. The choice persists so returning users land
// straight in their workspace; the header switcher can change it any time.
export function useRole(): {
  role: Role | null;
  setRole: (r: Role) => void;
  clearRole: () => void;
} {
  const [role, setRoleState] = useState<Role | null>(() => storedRole());

  useEffect(() => {
    if (role) document.documentElement.dataset.role = role;
    else delete document.documentElement.dataset.role;
  }, [role]);

  const setRole = useCallback((r: Role) => {
    localStorage.setItem(KEY, r);
    setRoleState(r);
  }, []);

  const clearRole = useCallback(() => {
    localStorage.removeItem(KEY);
    setRoleState(null);
  }, []);

  return { role, setRole, clearRole };
}

export const ROLE_META: Record<Role, { label: string; question: string; blurb: string }> = {
  builder: {
    label: "Builder",
    question: "Where should I build, and what can I launch at?",
    blurb: "Opportunity map, residual land value, launch-price defence, what-if scenarios.",
  },
  agent: {
    label: "Agent",
    question: "What is this unit worth — with evidence I can show a client?",
    blurb: "Evidence-backed valuation band, comparables, a ready-to-send sales narrative.",
  },
  buyer: {
    label: "Buyer",
    question: "Is this fair, is the area good, what's the catch?",
    blurb: "Plain-language read on price fairness, area quality, and honest red flags.",
  },
};
