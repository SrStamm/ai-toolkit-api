import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // ts-agent: agente (streaming, routing, LLM)
      "/agent": "http://localhost:3000",
      // python backend: RAG (ingestión, búsqueda, documentos)
      "/rag": "http://localhost:8000",
    },
  },
  build: {
    chunkSizeWarningLimit: 600, // Increase warning limit for syntax highlighter
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-syntax": ["react-syntax-highlighter"],
          "vendor-icons": ["lucide-react"],
          "vendor-markdown": ["react-markdown"],
          "vendor-ui": [
            "sonner",
            "@radix-ui/react-progress",
            "@radix-ui/react-slot",
            "@radix-ui/react-tabs",
            "class-variance-authority",
            "clsx",
            "tailwind-merge",
            "next-themes",
          ],
        },
      },
    },
  },
});
