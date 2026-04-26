import { useEffect, useMemo, useRef, useState } from "react";

import { estimateLeadMedia, fetchPublicConfig, sendChatMessage, startChat, uploadLeadMedia } from "./api";
import { LoadingState } from "./components/LoadingState";
import { ResultCard } from "./components/ResultCard";

const QUICK_CHIPS = [
  "Pęknięty ekran",
  "Bateria",
  "Zalany telefon",
  "Tablet",
  "Laptop",
];

async function getVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration || 0);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Nie udało się odczytać długości wideo."));
    };
    video.src = url;
  });
}

function extractModel(text) {
  const source = (text || "").toLowerCase();
  const patterns = [
    /(iphone\s?[a-z0-9+\- ]{1,20})/i,
    /(ipad\s?[a-z0-9+\- ]{1,20})/i,
    /(samsung\s+galaxy\s?[a-z0-9+\- ]{1,20})/i,
    /(galaxy\s?[a-z0-9+\- ]{1,20})/i,
    /(tablet\s?[a-z0-9+\- ]{0,20})/i,
    /(macbook\s?[a-z0-9+\- ]{0,20})/i,
  ];
  for (const pattern of patterns) {
    const match = source.match(pattern);
    if (match?.[1]) {
      return match[1].trim();
    }
  }
  return null;
}

function buildPreview(file) {
  if (!file) return null;
  return {
    url: URL.createObjectURL(file),
    isImage: file.type.startsWith("image/"),
    isVideo: file.type.startsWith("video/"),
  };
}

function LeadCompleteCard({ name, phone, model }) {
  return (
    <div className="rounded-[26px] border border-emerald-200 bg-[linear-gradient(135deg,#ecfdf5_0%,#f0fdfa_100%)] p-4 text-left shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Zgłoszenie przyjęte</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-900">Dane kontaktowe zostały zapisane</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Serwis ma już komplet podstawowych danych i może wrócić do klienta z potwierdzeniem kontaktu lub terminu.
      </p>
      <div className="mt-4 grid gap-2 text-sm text-slate-700 sm:grid-cols-3">
        <div className="rounded-2xl bg-white/80 px-3 py-2">
          <span className="block text-[11px] uppercase tracking-[0.16em] text-slate-400">Klient</span>
          <span className="font-medium">{name || "Uzupełniony"}</span>
        </div>
        <div className="rounded-2xl bg-white/80 px-3 py-2">
          <span className="block text-[11px] uppercase tracking-[0.16em] text-slate-400">Telefon</span>
          <span className="font-medium">{phone || "Zapisany"}</span>
        </div>
        <div className="rounded-2xl bg-white/80 px-3 py-2">
          <span className="block text-[11px] uppercase tracking-[0.16em] text-slate-400">Urządzenie</span>
          <span className="font-medium">{model || "W trakcie doprecyzowania"}</span>
        </div>
      </div>
    </div>
  );
}

export function WidgetApp({ apiBaseUrl, title, accentLabel }) {
  const [isOpen, setIsOpen] = useState(false);
  const [leadId, setLeadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedMedia, setUploadedMedia] = useState(null);
  const [lastDetectedModel, setLastDetectedModel] = useState("");
  const [leadSnapshot, setLeadSnapshot] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [publicConfig, setPublicConfig] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const preview = useMemo(() => buildPreview(selectedFile), [selectedFile]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const setViewportHeight = () => {
      const visualHeight = window.visualViewport?.height || window.innerHeight;
      document.documentElement.style.setProperty("--ai-widget-vh", `${visualHeight}px`);
    };

    setViewportHeight();
    window.addEventListener("resize", setViewportHeight);
    window.visualViewport?.addEventListener("resize", setViewportHeight);

    return () => {
      window.removeEventListener("resize", setViewportHeight);
      window.visualViewport?.removeEventListener("resize", setViewportHeight);
    };
  }, []);

  useEffect(() => {
    if (typeof document === "undefined" || !isOpen) return undefined;

    const { body } = document;
    const previousOverflow = body.style.overflow;
    const previousTouchAction = body.style.touchAction;

    body.style.overflow = "hidden";
    body.style.touchAction = "none";

    return () => {
      body.style.overflow = previousOverflow;
      body.style.touchAction = previousTouchAction;
    };
  }, [isOpen]);

  useEffect(() => {
    return () => {
      if (preview?.url) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [preview]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, estimate, errorMessage, isSubmitting, isUploading, leadSnapshot]);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      try {
        const config = await fetchPublicConfig(apiBaseUrl);
        if (!cancelled) {
          setPublicConfig(config);
        }
      } catch (_error) {
        // Widżet może działać na ustawieniach domyślnych.
      }
    }

    loadConfig();
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!isOpen || leadId) return;
    let cancelled = false;

    async function bootstrap() {
      try {
        const chat = await startChat(apiBaseUrl);
        if (!cancelled) {
          setLeadId(chat.lead_id);
          setMessages([{ role: "assistant", text: chat.message }]);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error.message);
        }
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl, isOpen, leadId]);

  async function maybeEstimate(activeLeadId, mediaAsset, explicitModel) {
    if (!activeLeadId || !mediaAsset) return;
    try {
      const result = await estimateLeadMedia(apiBaseUrl, {
        lead_id: activeLeadId,
        media_asset_id: mediaAsset.id,
        device_model: explicitModel || lastDetectedModel || null,
      });
      setEstimate(result);
      if (result?.matched_device) {
        setLastDetectedModel(`${result.matched_device.brand} ${result.matched_device.model_name}`);
      } else if (explicitModel) {
        setLastDetectedModel(explicitModel);
      }
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: result.customer_message || "Przygotowałem orientacyjną wycenę." },
      ]);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleSendMessage(prefilledText) {
    if (!leadId) {
      setErrorMessage("Czat jeszcze się uruchamia. Spróbuj ponownie za chwilę.");
      return;
    }

    const candidateText = typeof prefilledText === "string" ? prefilledText : draft;
    const hasText = Boolean(candidateText.trim());
    const fallbackText = selectedFile ? "Dodaję plik do konsultacji." : "";
    const text = hasText ? candidateText.trim() : fallbackText;
    if (!text) {
      setErrorMessage("Napisz wiadomość albo dodaj plik, aby kontynuować rozmowę.");
      return;
    }

    const extractedModel = extractModel(text);
    const resolvedModel = extractedModel || lastDetectedModel || null;
    if (extractedModel) {
      setLastDetectedModel(extractedModel);
    }

    setIsSubmitting(true);
    setErrorMessage("");
    setEstimate(null);

    try {
      let mediaForEstimate = uploadedMedia;
      let shouldEstimate = false;

      if (selectedFile) {
        setIsUploading(true);
        const uploaded = await uploadLeadMedia(apiBaseUrl, leadId, selectedFile);
        mediaForEstimate = uploaded.media_asset;
        setUploadedMedia(uploaded.media_asset);
        shouldEstimate = true;
        setMessages((prev) => [
          ...prev,
          { role: "user", text: `Dodałem plik: ${selectedFile.name}` },
          { role: "assistant", text: uploaded.assistant_message },
        ]);
        setSelectedFile(null);
        setIsUploading(false);
      }

      const reply = await sendChatMessage(apiBaseUrl, {
        lead_id: leadId,
        text,
        device_model: resolvedModel,
      });

      setLeadSnapshot({
        status: reply.lead_status,
        customerName: reply.customer_name,
        phone: reply.phone,
        deviceModel: reply.device_model || resolvedModel,
      });

      if (reply.device_model) {
        setLastDetectedModel(reply.device_model);
      }

      setMessages((prev) => [
        ...prev,
        { role: "user", text },
        { role: "assistant", text: reply.message },
      ]);
      setDraft("");

      if (mediaForEstimate && (shouldEstimate || !estimate)) {
        await maybeEstimate(leadId, mediaForEstimate, resolvedModel);
      }
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsUploading(false);
      setIsSubmitting(false);
    }
  }

  async function handleFileChange(file) {
    try {
      setErrorMessage("");
      if (file.type.startsWith("video/")) {
        const duration = await getVideoDuration(file);
        if (duration > 15) {
          setErrorMessage("Wideo może mieć maksymalnie 15 sekund.");
          return;
        }
      }
      setSelectedFile(file);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  const resolvedTitle = publicConfig?.widget_title || title;
  const resolvedAccent = publicConfig?.accent_label || accentLabel;
  const launcherLabel = publicConfig?.widget_button_label || title;
  const isLeadReady = leadSnapshot?.status === "gotowy_do_kontaktu";

  return (
    <div className="ai-widget-root relative z-[2147483000]">
      <div className="hidden max-w-[720px] items-stretch gap-4 md:flex">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="group inline-flex items-center gap-4 rounded-[28px] border border-white/50 bg-[linear-gradient(135deg,#f97316_0%,#0891b2_100%)] px-7 py-5 text-white shadow-glow transition duration-300 hover:translate-y-[-1px]"
          aria-label="Otwórz czat wyceny"
        >
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] bg-white/15 text-3xl">+</span>
          <span className="text-left">
            <span className="block text-[11px] font-semibold uppercase tracking-[0.24em] text-white/75">{resolvedAccent}</span>
            <span className="mt-1 block text-xl font-semibold">{launcherLabel}</span>
            <span className="mt-1 block text-sm text-white/80">Szybka konsultacja, orientacyjna wycena i zapis kontaktu.</span>
          </span>
        </button>
      </div>

      <div className="inline-flex max-w-full flex-col items-start gap-2 md:hidden">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="group inline-flex max-w-full items-center gap-3 rounded-[20px] border border-white/50 bg-[linear-gradient(135deg,#f97316_0%,#0891b2_100%)] px-4 py-3 text-white shadow-glow transition duration-300 hover:translate-y-[-1px]"
          aria-label="Otwórz czat wyceny"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-2xl">+</span>
          <span className="min-w-0 text-left">
            <span className="block text-[10px] font-semibold uppercase tracking-[0.22em] text-white/75">{resolvedAccent}</span>
            <span className="mt-1 block truncate text-base font-semibold">{launcherLabel}</span>
          </span>
        </button>
      </div>

      <p className="mt-3 max-w-md text-xs leading-5 text-slate-500">
        Szybka konsultacja AI i orientacyjna wycena. Dokładna cena może się zmienić po oględzinach urządzenia przez specjalistę.
      </p>

      {isOpen ? (
        <div className="ai-widget-overlay fixed inset-0 z-[2147483001] flex items-end justify-center overflow-hidden bg-slate-950/40 p-0 backdrop-blur-sm sm:p-4 md:items-center">
          <div className="ai-widget-sheet h-[var(--ai-widget-vh,100dvh)] w-full rounded-none border-0 bg-[linear-gradient(180deg,#f8fafc_0%,#fff7ed_45%,#f0fdfa_100%)] p-1 shadow-glow sm:h-auto sm:w-[min(96vw,620px)] sm:rounded-[34px] sm:border sm:border-white/70 sm:p-4">
            <div className="flex h-full flex-col rounded-t-[26px] rounded-b-none bg-white/95 shadow-sm sm:max-h-[88vh] sm:rounded-[24px]">
              <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-3 py-3 sm:px-5 sm:py-4">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-orange-500">{resolvedAccent}</p>
                  <h2 className="mt-2 text-[22px] font-bold leading-tight text-ink sm:text-2xl">{resolvedTitle}</h2>
                  <p className="mt-2 text-[13px] leading-6 text-slate-500 sm:text-sm">
                    Opisz problem, dodaj zdjęcie lub wideo, a AI poprowadzi rozmowę i przygotuje orientacyjną wycenę.
                  </p>
                  {lastDetectedModel ? (
                    <div className="mt-3 inline-flex max-w-full rounded-full bg-cyan-50 px-3 py-1 text-[11px] font-semibold text-cyan-700 sm:text-xs">
                      <span className="truncate">Model: {lastDetectedModel}</span>
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-xl text-slate-600 transition hover:bg-slate-200 sm:h-11 sm:w-11"
                  aria-label="Zamknij czat"
                >
                  ×
                </button>
              </div>

              <div className="border-b border-slate-100 px-3 py-3 sm:px-5">
                <div className="flex flex-wrap gap-2 pb-1 sm:flex-nowrap sm:overflow-x-auto">
                  {QUICK_CHIPS.map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => handleSendMessage(chip)}
                      disabled={isSubmitting || isUploading}
                      className="shrink-0 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-orange-200 hover:bg-orange-50 disabled:opacity-50"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>

              <div className="ai-widget-messages ai-scrollbar min-h-0 flex-1 overflow-y-auto px-3 py-3 sm:px-5 sm:py-4">
                <div className="space-y-3">
                  {messages.map((item, index) => (
                    <div key={`${item.role}-${index}`} className={item.role === "user" ? "flex justify-end" : "flex justify-start"}>
                      <div
                        className={[
                          "max-w-[96%] rounded-[20px] px-4 py-3 text-[13px] leading-6 sm:max-w-[86%] sm:rounded-[22px] sm:text-sm",
                          item.role === "user"
                            ? "bg-gradient-to-r from-orange-500 to-cyan-600 text-white"
                            : "bg-slate-100 text-slate-700",
                        ].join(" ")}
                      >
                        {item.text}
                      </div>
                    </div>
                  ))}

                  {selectedFile && preview ? (
                    <div className="rounded-[24px] border border-slate-200 bg-white p-3 shadow-sm">
                      <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Podgląd pliku</div>
                      {preview.isImage ? (
                        <img src={preview.url} alt="Podgląd pliku" className="h-36 w-full rounded-[20px] object-cover" />
                      ) : preview.isVideo ? (
                        <video src={preview.url} controls className="h-36 w-full rounded-[20px] object-cover" />
                      ) : null}
                      <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-600">
                        <span className="truncate">{selectedFile.name}</span>
                        <button
                          type="button"
                          onClick={() => setSelectedFile(null)}
                          className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600"
                        >
                          Usuń
                        </button>
                      </div>
                    </div>
                  ) : null}

                  {uploadedMedia ? (
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                      Załączony plik: {uploadedMedia.file_name}
                    </div>
                  ) : null}

                  {(isSubmitting || isUploading) ? <LoadingState /> : null}
                  {!isSubmitting && estimate ? <ResultCard estimate={estimate} /> : null}
                  {isLeadReady ? (
                    <LeadCompleteCard
                      name={leadSnapshot?.customerName}
                      phone={leadSnapshot?.phone}
                      model={leadSnapshot?.deviceModel || lastDetectedModel}
                    />
                  ) : null}
                  {errorMessage ? (
                    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                      {errorMessage}
                    </div>
                  ) : null}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="ai-widget-composer border-t border-slate-100 px-3 pb-[max(14px,env(safe-area-inset-bottom))] pt-3 sm:px-5 sm:pt-4">
                <div className="flex items-end gap-2 sm:gap-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-xl text-slate-600 transition hover:bg-slate-50 sm:h-12 sm:w-12"
                    aria-label="Dodaj załącznik"
                  >
                    +
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,video/*"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) {
                        handleFileChange(file);
                      }
                    }}
                  />

                  <div className="min-w-0 flex-1 rounded-[20px] border border-slate-200 bg-white px-3 py-2 shadow-sm sm:rounded-[24px] sm:px-4 sm:py-3">
                    <textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      rows={1}
                      className="max-h-24 min-h-[26px] w-full resize-none border-0 bg-transparent text-base leading-6 text-ink outline-none md:max-h-32 md:text-sm"
                      placeholder="Np. iPhone X po upadku, dotyk działa, ale pękło szkło. Możesz też od razu podać imię i numer telefonu."
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => handleSendMessage()}
                    disabled={isSubmitting || isUploading}
                    className="shrink-0 rounded-2xl bg-gradient-to-r from-orange-500 to-cyan-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60 sm:px-5"
                  >
                    Wyślij
                  </button>
                </div>

                <p className="mt-2 text-[11px] leading-5 text-slate-500 sm:mt-3 sm:text-xs">
                  Obsługujemy telefony, tablety i inne urządzenia mobilne. AI może poprosić o model, opis objawów, imię i numer telefonu.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
