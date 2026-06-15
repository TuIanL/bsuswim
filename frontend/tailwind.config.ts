import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        "brand-black": "#050505",
        "brand-dark": "#0f0f0f",
        "brand-gray": "#1a1a1a",
        "brand-muted": "#666666",
        "brand-light": "#999999"
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"]
      },
      letterSpacing: {
        widest: "0.2em",
        ultra: "0.3em"
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "4px",
        md: "4px",
        lg: "4px",
        xl: "4px",
        "2xl": "4px"
      },
      boxShadow: {
        "white-glow": "0 0 28px rgba(255, 255, 255, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
