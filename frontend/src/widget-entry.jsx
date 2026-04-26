import React from "react";
import { createRoot } from "react-dom/client";

import styles from "./index.css?inline";
import { WidgetApp } from "./WidgetApp";

const DEFAULT_OPTIONS = {
  apiBaseUrl: "",
  title: "Wycena naprawy",
  accentLabel: "AI Diagnostyka",
};

/**
 * Встраивает виджет в страницу, создавая отдельный Shadow DOM для изоляции стилей.
 */
function init(userOptions = {}) {
  const options = {
    ...DEFAULT_OPTIONS,
    ...userOptions,
    apiBaseUrl: userOptions.apiBaseUrl || DEFAULT_OPTIONS.apiBaseUrl,
  };

  const host = document.createElement("div");
  host.setAttribute("data-ai-repair-estimator", "true");
  const scriptParent = document.currentScript?.parentElement;
  const mountTarget =
    userOptions.mountTarget ||
    (scriptParent && scriptParent.tagName !== "HEAD" ? scriptParent : document.body);
  mountTarget.appendChild(host);

  const shadowRoot = host.attachShadow({ mode: "open" });
  const styleTag = document.createElement("style");
  styleTag.textContent = styles;
  shadowRoot.appendChild(styleTag);

  const mountNode = document.createElement("div");
  shadowRoot.appendChild(mountNode);

  const root = createRoot(mountNode);
  root.render(
    <React.StrictMode>
      <WidgetApp
        apiBaseUrl={options.apiBaseUrl}
        title={options.title}
        accentLabel={options.accentLabel}
      />
    </React.StrictMode>,
  );

  return {
    /**
     * Аккуратно размонтирует виджет и удалит его контейнер со страницы.
     */
    destroy() {
      root.unmount();
      host.remove();
    },
  };
}

/**
 * Пытается автоматически инициализировать виджет по data-атрибутам script-тега.
 */
function autoInitFromScriptTag() {
  const currentScript = document.currentScript;
  if (!(currentScript instanceof HTMLScriptElement)) {
    return;
  }

  const apiBaseUrl = currentScript.dataset.apiBaseUrl;
  if (!apiBaseUrl) {
    return;
  }

  init({
    apiBaseUrl,
    title: currentScript.dataset.title || DEFAULT_OPTIONS.title,
    accentLabel: currentScript.dataset.accentLabel || DEFAULT_OPTIONS.accentLabel,
  });
}

window.AIRepairEstimatorWidget = { init };
autoInitFromScriptTag();
