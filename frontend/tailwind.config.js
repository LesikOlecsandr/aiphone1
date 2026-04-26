/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      boxShadow: {
        glow: "0 18px 48px rgba(6, 24, 44, 0.18)",
      },
      colors: {
        ink: "#132238",
        accent: "#f97316",
        accentSoft: "#ffedd5",
        sea: "#0891b2",
        mist: "#f8fafc",
      },
      animation: {
        "pulse-soft": "pulseSoft 2.2s ease-in-out infinite",
        floaty: "floaty 5s ease-in-out infinite",
        shimmer: "shimmer 1.8s linear infinite",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.85" },
          "50%": { transform: "scale(1.06)", opacity: "1" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
