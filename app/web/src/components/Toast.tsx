// Transient, honest notice — used when a map click lands outside the covered
// submarkets. Dismissible; App auto-clears it.
export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <div
      role="status"
      className="pointer-events-auto absolute left-1/2 top-4 z-40 flex max-w-[520px] -translate-x-1/2 items-start gap-3 rounded-[3px] border border-line bg-panel px-3 py-2 shadow-2xl"
    >
      <span className="mt-[1px] h-2 w-2 shrink-0 rounded-full bg-warn" aria-hidden />
      <span className="text-[12px] leading-relaxed text-ink-dim">{message}</span>
      <button
        type="button"
        onClick={onClose}
        aria-label="Dismiss notice"
        className="shrink-0 text-ink-mute hover:text-ink"
      >
        ✕
      </button>
    </div>
  );
}
