// Global app store (Context + useReducer — no external state lib). Holds the
// shell-level UI state (selected area/unit/view, independent sidebar toggles)
// and chat history. Chats + settings persist to localStorage, keyed by a
// placeholder userId so the same shape carries over once real accounts land
// (Phase 6 in docs/DEVELOPMENT-PLAN.md).
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import { dataSource } from "./dataSource";

export type ViewKey =
  | "opportunity"
  | "ranking"
  | "price"
  | "comps"
  | "trend"
  | "land"
  | "margin"
  | "build"
  | "scenarios"
  | "buildability"
  | "competitors"
  | "news"
  | "nearby"
  | "infra"
  | "chatnew"
  | "chathist"
  | "chatopen"
  | "settings";

export interface ChatMessage {
  role: "user" | "bot";
  text: string;
}

export interface ChatSession {
  id: string;
  title: string;
  when: string; // ISO timestamp
  messages: ChatMessage[];
}

export interface AppState {
  selectedArea: string | null;
  unitType: string;
  view: ViewKey;
  navOpen: boolean;
  infoOpen: boolean;
  chats: ChatSession[];
  openChatId: string | null;
  // Bumped when a background dataSource.prefetch(area) resolves. Consumers don't
  // read this directly — it exists purely to give the context value a new
  // identity so components re-render and pick up the now-cached real bundle
  // (getBundle() itself is a plain, un-memoized read; see MapRegion/views/index).
  dataTick: number;
}

// No auth yet (Phase 6) — chats/settings are scoped under this placeholder so
// the storage key shape doesn't need to change once accounts exist.
export const PLACEHOLDER_USER_ID = "local-user";

const DEFAULT_UNIT = "m2";
const DEFAULT_VIEW: ViewKey = "price";

function genId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

function storageKey(userId: string): string {
  return `jre:${userId}:appstate`;
}

interface Persisted {
  chats: ChatSession[];
  unitType: string;
}

function loadPersisted(userId: string): Persisted | null {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Persisted>;
    if (!Array.isArray(parsed.chats)) return null;
    return { chats: parsed.chats, unitType: parsed.unitType ?? DEFAULT_UNIT };
  } catch {
    return null;
  }
}

function savePersisted(userId: string, data: Persisted): void {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(data));
  } catch {
    // localStorage unavailable (private mode / quota) — chats stay session-only.
  }
}

function initState(userId: string): AppState {
  const persisted = loadPersisted(userId);
  return {
    selectedArea: null,
    unitType: persisted?.unitType ?? DEFAULT_UNIT,
    view: DEFAULT_VIEW,
    navOpen: true,
    infoOpen: true,
    chats: persisted?.chats ?? [],
    openChatId: null,
    dataTick: 0,
  };
}

type Action =
  | { type: "SET_AREA"; area: string | null }
  | { type: "SET_UNIT"; unit: string }
  | { type: "SET_VIEW"; view: ViewKey }
  | { type: "TOGGLE_NAV" }
  | { type: "TOGGLE_INFO" }
  | { type: "NEW_CHAT" }
  | { type: "OPEN_CHAT"; id: string }
  | { type: "ADD_MESSAGE"; message: ChatMessage }
  | { type: "DATA_TICK" };

function newSession(): ChatSession {
  return { id: genId(), title: "New chat", when: new Date().toISOString(), messages: [] };
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_AREA":
      return { ...state, selectedArea: action.area };
    case "SET_UNIT":
      return { ...state, unitType: action.unit };
    case "SET_VIEW":
      return { ...state, view: action.view };
    case "TOGGLE_NAV":
      return { ...state, navOpen: !state.navOpen };
    case "TOGGLE_INFO":
      return { ...state, infoOpen: !state.infoOpen };
    case "NEW_CHAT": {
      const session = newSession();
      return { ...state, chats: [session, ...state.chats], openChatId: session.id, view: "chatopen" };
    }
    case "OPEN_CHAT":
      return { ...state, openChatId: action.id, view: "chatopen" };
    case "ADD_MESSAGE": {
      let chats = state.chats;
      let openChatId = state.openChatId;
      // No open session yet (e.g. message sent before "New chat" was pressed) —
      // create one lazily so a message is never silently dropped.
      if (!openChatId || !chats.some((c) => c.id === openChatId)) {
        const session = newSession();
        chats = [session, ...chats];
        openChatId = session.id;
      }
      chats = chats.map((c) => {
        if (c.id !== openChatId) return c;
        const messages = [...c.messages, action.message];
        const title =
          c.title === "New chat" && action.message.role === "user"
            ? action.message.text.slice(0, 48)
            : c.title;
        return { ...c, messages, title };
      });
      return { ...state, chats, openChatId };
    }
    case "DATA_TICK":
      return { ...state, dataTick: state.dataTick + 1 };
    default:
      return state;
  }
}

export interface AppStateContextValue {
  state: AppState;
  setArea: (area: string | null) => void;
  setUnit: (unit: string) => void;
  setView: (view: ViewKey) => void;
  toggleNav: () => void;
  toggleInfo: () => void;
  newChat: () => void;
  openChat: (id: string) => void;
  addMessage: (message: ChatMessage) => void;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({
  children,
  userId = PLACEHOLDER_USER_ID,
}: {
  children: ReactNode;
  userId?: string;
}) {
  const [state, dispatch] = useReducer(reducer, userId, initState);

  useEffect(() => {
    savePersisted(userId, { chats: state.chats, unitType: state.unitType });
  }, [userId, state.chats, state.unitType]);

  const value = useMemo<AppStateContextValue>(
    () => ({
      state,
      setArea: (area) => {
        dispatch({ type: "SET_AREA", area });
        // Real source only: kicks off the background fetch+cache for this area
        // and forces one re-render when it lands, so the mock-placeholder
        // bundle shown meanwhile upgrades to the live one without a poll.
        if (area) {
          dataSource.prefetch?.(area).then(() => dispatch({ type: "DATA_TICK" })).catch(() => {});
        }
      },
      setUnit: (unit) => dispatch({ type: "SET_UNIT", unit }),
      setView: (view) => dispatch({ type: "SET_VIEW", view }),
      toggleNav: () => dispatch({ type: "TOGGLE_NAV" }),
      toggleInfo: () => dispatch({ type: "TOGGLE_INFO" }),
      newChat: () => dispatch({ type: "NEW_CHAT" }),
      openChat: (id) => dispatch({ type: "OPEN_CHAT", id }),
      addMessage: (message) => dispatch({ type: "ADD_MESSAGE", message }),
    }),
    [state],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useApp(): AppStateContextValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useApp must be used within an AppStateProvider");
  return ctx;
}
