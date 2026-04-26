/**
 * Spokojny stan ładowania podczas generowania odpowiedzi AI.
 */
export function LoadingState() {
  return (
    <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] px-5 py-6 shadow-sm">
      <div className="mx-auto flex w-full max-w-[280px] flex-col items-center text-center">
        <div className="relative mb-5 flex h-24 w-24 items-center justify-center rounded-[30px] bg-slate-950 shadow-[0_20px_45px_rgba(15,23,42,0.18)]">
          <div className="absolute inset-0 rounded-[30px] border border-white/10" />
          <div className="absolute inset-[14px] rounded-[22px] bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.45),transparent_50%),linear-gradient(135deg,rgba(249,115,22,0.22),rgba(8,145,178,0.2))]" />
          <div className="relative h-9 w-9 rounded-full border-[3px] border-white/80 border-t-transparent animate-spin" />
          <div className="absolute h-16 w-16 rounded-full border border-orange-300/35 animate-pulse" />
        </div>
        <h3 className="text-base font-semibold text-ink">Przygotowujemy odpowiedź</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          AI analizuje zgłoszenie, porównuje możliwe warianty naprawy i za chwilę odpisze.
        </p>
      </div>
    </div>
  );
}
