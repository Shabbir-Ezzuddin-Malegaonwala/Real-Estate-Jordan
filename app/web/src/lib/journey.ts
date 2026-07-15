import { useCallback, useState } from "react";

// The builder's decision journey — one product, seven ordered steps. The stepper
// is a re-labelling/re-ordering of capabilities the app already has, framed as
// the questions a builder asks in sequence.
export type StepKey =
  | "opportunity"
  | "economics"
  | "pricing"
  | "monitoring";

export interface JourneyStep {
  key: StepKey;
  n: number;
  label: string;
  question: string;
}

export const STEPS: JourneyStep[] = [
  { key: "opportunity", n: 1, label: "Where to build", question: "Which area is best to build in?" },
  { key: "economics", n: 2, label: "Land price", question: "What can I pay for the land?" },
  { key: "pricing", n: 3, label: "Sell price", question: "What price should I sell at?" },
  { key: "monitoring", n: 4, label: "Market news", question: "What's changed recently?" },
];

export const STEP_INDEX: Record<StepKey, number> = Object.fromEntries(
  STEPS.map((s, i) => [s.key, i]),
) as Record<StepKey, number>;

export type EntryMode = "explore" | "evaluate";

const KEY = "builder-entered";

// Landing gate. Once a builder enters, the choice persists so returning sessions
// skip straight into the workspace; the home affordance clears it.
export function useEntered(): { entered: boolean; enter: () => void; exit: () => void } {
  const [entered, setEntered] = useState<boolean>(() => localStorage.getItem(KEY) === "1");
  const enter = useCallback(() => {
    localStorage.setItem(KEY, "1");
    setEntered(true);
  }, []);
  const exit = useCallback(() => {
    localStorage.removeItem(KEY);
    setEntered(false);
  }, []);
  return { entered, enter, exit };
}
