import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bedrock",
  description: "Personal arXiv citation graph explorer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
