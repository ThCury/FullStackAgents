import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rivexx Squad Console",
  description: "Console de orquestração do squad de agentes de IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
