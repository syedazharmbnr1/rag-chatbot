
import './globals.css'; // Your TailwindCSS styles import

export const metadata = {
  title: 'RAG Chatbot',
  description: 'A professional chatbot frontend built with Next.js and TailwindCSS',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* You can add meta tags, fonts here */}
        <link
          rel="preconnect"
          href="https://fonts.googleapis.com"
        />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-gray-50 font-sans text-gray-900 min-h-screen">
        {children}
      </body>
    </html>
  );
}
