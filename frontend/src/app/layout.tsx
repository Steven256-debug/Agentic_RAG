import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)", color: "#171717" },
  ],
};

export const metadata: Metadata = {
  title: "ComplyGH - Your AI Guide to Ghana's Financial Regulations",
  description: "Intelligent AI assistant for Ghanaian banking laws, capital adequacy, cybersecurity, and mobile money compliance.",
  openGraph: {
    title: "ComplyGH - Your AI Guide to Ghana's Financial Regulations",
    description: "Intelligent AI assistant for Ghanaian banking laws, capital adequacy, cybersecurity, and mobile money compliance.",
  },
  icons: {
    icon: "/favicon.ico",
  }
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full overscroll-none">
      <body className={`${inter.className} h-full antialiased overscroll-none text-foreground bg-background`}>
        {children}
      </body>
    </html>
  );
}

