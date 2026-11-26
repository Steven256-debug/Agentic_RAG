import type { Metadata, Viewport } from "next";
import { Host_Grotesk, Atkinson_Hyperlegible_Mono } from "next/font/google";
import "./globals.css";

const hostGrotesk = Host_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-host-grotesk",
  display: "swap",
});

const atkinsonMono = Atkinson_Hyperlegible_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-atkinson-mono",
  display: "swap",
  adjustFontFallback: false,
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf8f4" },
    { media: "(prefers-color-scheme: dark)", color: "#15171c" },
  ],
};

export const metadata: Metadata = {
  title: "ComplyGH - Regulatory Compliance Workspace",
  description:
    "AI compliance workspace for Ghanaian banking laws, capital adequacy, cybersecurity directives, and mobile money regulations.",
  openGraph: {
    title: "ComplyGH - Regulatory Compliance Workspace",
    description:
      "AI compliance workspace for Ghanaian banking laws, capital adequacy, cybersecurity directives, and mobile money regulations.",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

const themeInitScript = `
(function() {
  try {
    var saved = localStorage.getItem("complygh_theme");
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved === "dark" || (!saved && prefersDark)) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${hostGrotesk.variable} ${atkinsonMono.variable} h-full overscroll-none`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="h-full antialiased overscroll-none text-ink bg-paper">
        {children}
      </body>
    </html>
  );
}
