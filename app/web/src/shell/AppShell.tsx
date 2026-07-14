import { useApp } from "../lib/store";
import { ViewRouter } from "../views";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { MapRegion } from "./MapRegion";

// Responsive CSS-flex shell (Demo-G target): TopBar spans full width; below
// it, Sidebar and the InfoPanel collapse INDEPENDENTLY via navOpen/infoOpen.
// Under 900px both overlay the map instead of pushing it.
export function AppShell() {
  const { state, toggleNav, toggleInfo } = useApp();
  const { navOpen, infoOpen } = state;

  function closeOverlays() {
    if (navOpen) toggleNav();
    if (infoOpen) toggleInfo();
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-stitch-bg text-stitch-ink">
      <TopBar />
      <div className="relative flex flex-1 overflow-hidden">
        {(navOpen || infoOpen) && (
          <div onClick={closeOverlays} className="fixed inset-0 z-20 hidden bg-black/30 max-[899px]:block" />
        )}

        <aside
          className={
            navOpen
              ? "z-30 flex-none overflow-y-auto overflow-x-hidden border-r border-stitch-line bg-stitch-card transition-all duration-200 w-[236px] max-[1200px]:w-[210px] max-[899px]:fixed max-[899px]:inset-y-0 max-[899px]:left-0 max-[899px]:top-[54px] max-[899px]:w-[min(300px,86vw)] max-[899px]:translate-x-0 max-[899px]:shadow-2xl"
              : "z-30 flex-none overflow-y-auto overflow-x-hidden border-r border-stitch-line bg-stitch-card transition-all duration-200 w-0 max-[899px]:fixed max-[899px]:inset-y-0 max-[899px]:left-0 max-[899px]:top-[54px] max-[899px]:w-[min(300px,86vw)] max-[899px]:-translate-x-full max-[899px]:shadow-2xl"
          }
        >
          <Sidebar />
        </aside>

        <section
          className={
            infoOpen
              ? "z-10 flex-none overflow-y-auto border-r border-stitch-line bg-stitch-bg transition-all duration-200 w-[380px] max-[1200px]:w-[330px] max-[899px]:fixed max-[899px]:inset-y-0 max-[899px]:left-0 max-[899px]:top-[54px] max-[899px]:z-30 max-[899px]:w-[min(360px,90vw)] max-[899px]:translate-x-0 max-[899px]:shadow-2xl"
              : "z-10 flex-none overflow-y-auto border-r border-stitch-line bg-stitch-bg transition-all duration-200 w-0 max-[899px]:fixed max-[899px]:inset-y-0 max-[899px]:left-0 max-[899px]:top-[54px] max-[899px]:z-30 max-[899px]:w-[min(360px,90vw)] max-[899px]:-translate-x-full max-[899px]:shadow-2xl"
          }
        >
          {infoOpen && (
            <div className="p-4">
              <ViewRouter />
            </div>
          )}
        </section>

        <MapRegion />
      </div>
    </div>
  );
}
