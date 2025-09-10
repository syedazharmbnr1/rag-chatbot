"use client";

import { useRouter } from "next/navigation";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-200 flex flex-col items-center justify-center px-6">
      {/* Navbar */}
      {/* <header className="w-full flex justify-between items-center py-4 px-6 max-w-6xl">
        <img src="/ragchatbotimgbgremoved.png" alt="RAG Chatbot Logo" className="h-36"/>
       
      </header> */}

      {/* Hero Section */}
      <main className="flex flex-col items-center text-center mt-20 max-w-3xl">
        <img src='/rag-logo.png' alt='logo'className=" h-48 mx-auto rounded-full mb-6"/>
        <h2 className="text-5xl font-Mobile text-slate-800 mb-6 leading-tight">
          Smarter Conversations with <span className="text-slate-600">RAG Chatbot</span>
        </h2>
        <p className="text-lg text-slate-600 mb-8">
          Harness the power of Retrieval-Augmented Generation (RAG) to get precise, context-aware answers in real time.
        </p>
        <div className="flex space-x-4">
          <button
            onClick={() => router.push("/login")}
            className="px-6 py-3 rounded-xl bg-slate-600 text-white hover:bg-slate-700 transition shadow-lg"
          >
            Sign In
          </button>
          <button
            onClick={() => router.push("/signup")}
            className="px-6 py-3 rounded-xl border border-slate-400 text-slate-700 hover:bg-slate-100 transition"
          >
            Sign Up
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-slate-500 text-sm">
        © {new Date().getFullYear()} Data Panther. All rights reserved.
      </footer>
    </div>
  );
}