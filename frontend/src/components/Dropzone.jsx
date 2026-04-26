import { useRef, useState } from "react";

/**
 * Uniwersalna strefa drag-and-drop dla zdjec i video.
 */
export function Dropzone({ file, onFileSelect, disabled }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(fileList) {
    const selectedFile = Array.from(fileList || []).find(
      (item) => item.type.startsWith("image/") || item.type.startsWith("video/"),
    );
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          if (!disabled) handleFiles(event.dataTransfer.files);
        }}
        className={[
          "group relative w-full overflow-hidden rounded-[28px] border border-dashed px-5 py-8 text-left transition-all duration-300",
          "bg-gradient-to-br from-white via-orange-50 to-cyan-50 shadow-sm",
          isDragging ? "border-orange-400 shadow-glow ring-4 ring-orange-100" : "border-slate-300 hover:border-orange-300 hover:shadow-glow",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
        ].join(" ")}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_38%),radial-gradient(circle_at_bottom_left,rgba(8,145,178,0.12),transparent_32%)]" />
        <div className="relative flex items-center gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/90 text-2xl shadow-sm">
            {file?.type?.startsWith("video/") ? "🎬" : "📷"}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-ink">Przeciagnij zdjecie lub video tutaj</p>
            <p className="mt-1 text-sm text-slate-500">
              Obslugiwane video: do 15 sekund. Kliknij, aby wybrac plik.
            </p>
          </div>
        </div>
        {file ? (
          <div className="relative mt-4 rounded-2xl bg-white/80 px-4 py-3 text-sm text-slate-600 shadow-sm">
            Zalaczony plik: <span className="font-semibold text-ink">{file.name}</span>
          </div>
        ) : null}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,video/*"
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />
    </div>
  );
}
