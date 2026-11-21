
import "./globals.css";
import { Analytics } from "@vercel/analytics/next";

export const metadata = {
  title: "APT Agent | Rowing Weather Assistant",
  description:
    "Your AI weather assistant for rowing conditions at Lac de Tunis.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
