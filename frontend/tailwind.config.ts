import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#020617",
        ink: "#17202a",
        paper: "#f7f7f2",
        line: "#d8ddd2",
        moss: "#5f7f62",
        rust: "#b85f45",
        cyan: "#256f83"
      },
      boxShadow: {
        panel: "0 24px 80px rgba(2, 6, 23, 0.32)"
      }
    }
  },
  plugins: []
};

export default config;
