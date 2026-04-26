/**
 * Karta wyniku z polską prezentacją wyceny.
 */
export function ResultCard({ estimate }) {
  const range = estimate?.price_range;
  const sourceLabel =
    estimate?.price_source === "google_search"
      ? "Porównanie z cenami rynkowymi"
      : "Cennik serwisu";

  return (
    <div className="space-y-4 rounded-[28px] bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-900 p-5 text-white shadow-glow">
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/80">Wynik wyceny</p>
        <h3 className="mt-2 text-lg font-semibold">
          {estimate.matched_device.brand} {estimate.matched_device.model_name}
        </h3>
        <p className="mt-2 text-sm leading-6 text-slate-200/85">
          {estimate.vision_result.technical_summary}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-3xl bg-white/10 p-4 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-orange-200">Kopia</p>
          <p className="mt-2 text-2xl font-bold">{range.min_price} {range.currency}</p>
        </div>
        <div className="rounded-3xl bg-white/10 p-4 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-cyan-200">Oryginał</p>
          <p className="mt-2 text-2xl font-bold">{range.max_price} {range.currency}</p>
        </div>
      </div>

      <div className="rounded-3xl bg-white/10 p-4 backdrop-blur">
        <p className="text-xs uppercase tracking-wide text-slate-300">Rekomendowana cena</p>
        <p className="mt-2 text-3xl font-bold text-white">{estimate.recommended_price} {range.currency}</p>
        <p className="mt-2 text-sm text-slate-300">
          Diagnoza: <span className="font-medium text-white">{estimate.vision_result.damage_category}</span>
        </p>
        <p className="mt-2 text-sm text-slate-300">
          Źródło ceny: <span className="font-medium text-white">{sourceLabel}</span>
        </p>
        <p className="mt-3 text-xs leading-5 text-slate-300/85">
          Podana cena ma charakter orientacyjny. Dokładna wycena może się zmienić po oględzinach urządzenia przez specjalistę.
        </p>
      </div>
    </div>
  );
}
