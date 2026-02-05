import { NextIntlClientProvider, hasLocale } from "next-intl";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import type { Metadata } from "next";
import { Inter, Crimson_Pro, JetBrains_Mono } from "next/font/google";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const crimson = Crimson_Pro({ subsets: ["latin"], variable: "--font-crimson" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "Build Without Boundaries",
  description: "Towards Visual-Driven Intelligent RAG Agent",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  // Ensure that the incoming `locale` is valid
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  return (
    <html lang={locale} className="dark">
      <body className={`${inter.variable} ${crimson.variable} ${jetbrains.variable} font-sans bg-slate-950 text-slate-200 antialiased`}>
        <NextIntlClientProvider>
          <div className="absolute w-full h-full top-0 left-0">{children}</div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
