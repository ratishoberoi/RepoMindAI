import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#080b10",
        ink: "#0d1118",
        graphite: "#151b24",
        paper: "#f8fafc",
        line: "rgba(255,255,255,0.1)",
        mint: "#34d399",
        amber: "#f59e0b",
        rose: "#fb7185",
        cyan: "#38bdf8"
      },
      boxShadow: {
        panel: "0 24px 80px rgba(0, 0, 0, 0.34)"
      }
    }
  },
  plugins: []
};

export default config;
