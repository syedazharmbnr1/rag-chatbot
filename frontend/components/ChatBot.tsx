'use client';

import React, { useState, useEffect } from 'react';

type Message = {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  user_name?: string;
};

type Conversation = {
  id: string;
  title: string;
};

interface ChatbotProps {
  apiUrl: string;
  userId: string | null;
  token: string | null;
}

const embeddingModels = ["text-embedding-3-small", "gemma2:latest", "llama3.2:latest"] as const;
type EmbeddingModel = typeof embeddingModels[number];
const chatModels: Record<EmbeddingModel, string> = {
  "text-embedding-3-small": "gpt-4o-mini",
  "gemma2:latest": "gemma2:latest",
  "llama3.2:latest": "llama3.2:latest",
};

export default function Chatbot({ apiUrl, userId, token }: ChatbotProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState('');
  const [ragInput, setRagInput] = useState('');
  const [selectedKb, setSelectedKb] = useState<string>('');
  const [kbs, setKbs] = useState<{ name: string }[]>([]);
  const [embeddingModel, setEmbeddingModel] = useState(embeddingModels[0]);
  const [chatModel, setChatModel] = useState(chatModels[embeddingModels[0]]);
  const [retrievalK, setRetrievalK] = useState(4);
  const [loading, setLoading] = useState(false);

  // Fetch conversations on mount or userId change
  useEffect(() => {
    if (!userId) return;
    fetch(`${apiUrl}/conversations?user_id=${userId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(setConversations)
      .catch(console.error);
  }, [userId]);

  // Fetch messages when conversation changes
  useEffect(() => {
    if (!currentConvId) return;
    fetch(`${apiUrl}/messages?conversation_id=${currentConvId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(setMessages)
      .catch(console.error);
  }, [currentConvId]);

  // Fetch knowledge bases
  useEffect(() => {
    fetch(`${apiUrl}/knowledge_bases`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then((data) => {
        setKbs(data);
        if (data.length) setSelectedKb(data[0].name);
      })
      .catch(console.error);
  }, []);

  // Update chat model automatically when embedding model changes
  useEffect(() => {
    setChatModel(chatModels[embeddingModel] || chatModels[embeddingModels[0]]);
  }, [embeddingModel]);

  // Create new conversation
  const createConversation = async () => {
    if (!userId) return;
    const res = await fetch(`${apiUrl}/create/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId, title: 'New Chat' }),
    });
    const data = await res.json();
    setConversations(prev => [...prev, data]);
    setCurrentConvId(data.id);
    setMessages([]);
  };

  // Send direct chat message
  const sendDirectMessage = async () => {
    if (!userInput.trim() || !currentConvId) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/query/direct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          conversation_id: currentConvId,
          query: userInput,
          model_name: chatModel,
        }),
      });
      const data = await res.json();

      setMessages(prev => [
        ...prev,
        { role: 'user', content: userInput },
        { role: 'assistant', content: data.response },
      ]);
      setUserInput('');
    } catch (err) {
      console.error(err);
      alert('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  // Send RAG chat message
  const sendRagMessage = async () => {
    if (!ragInput.trim() || !currentConvId) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/query/rag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          conversation_id: currentConvId,
          query: ragInput,
          kb_names: [selectedKb],
          embedding_model: embeddingModel,
          chat_model: chatModel,
          retrieval_k: retrievalK,
        }),
      });
      const data = await res.json();

      setMessages(prev => [
        ...prev,
        { role: 'user', content: ragInput },
        { role: 'assistant', content: data.response },
      ]);
      setRagInput('');
    } catch (err) {
      console.error(err);
      alert('Failed to send RAG message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r p-4 flex flex-col">
        <button
          onClick={createConversation}
          className="mb-4 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + New Conversation
        </button>
        <div className="flex-1 overflow-y-auto">
          {conversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => setCurrentConvId(conv.id)}
              className={`cursor-pointer p-2 rounded ${
                currentConvId === conv.id ? 'bg-blue-100 font-semibold' : 'hover:bg-gray-100'
              }`}
            >
              {conv.title}
            </div>
          ))}
        </div>
      </aside>

      {/* Chat Area */}
      <main className="flex-1 flex flex-col p-6 bg-gray-50">
        <h1 className="text-2xl font-bold mb-4">Chatbot</h1>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 bg-white rounded shadow space-y-4 mb-4">
          {messages.length === 0 && <p className="text-gray-500">No messages yet. Start chatting!</p>}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`p-3 rounded max-w-xl ${
                msg.role === 'user' ? 'bg-blue-100 self-start' : 'bg-green-100 self-end'
              }`}
            >
              <strong>{msg.role === 'user' ? msg.user_name || 'You' : 'Assistant'}:</strong>{' '}
              {msg.content}
            </div>
          ))}
        </div>

        {/* Direct Chat Input */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold mb-2">Direct Chat</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={userInput}
              onChange={e => setUserInput(e.target.value)}
              disabled={loading}
              placeholder="Type your message..."
              className="flex-1 p-2 border rounded"
            />
            <select
              value={chatModel}
              onChange={e => setChatModel(e.target.value)}
              disabled={loading}
              className="border rounded p-2"
            >
              {Object.values(chatModels).map((modelName) => (
                <option key={modelName} value={modelName}>
                  {modelName}
                </option>
              ))}
            </select>
            <button
              onClick={sendDirectMessage}
              disabled={loading || !userInput.trim()}
              className="bg-green-600 text-white px-4 rounded hover:bg-green-700 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </section>

        {/* RAG Chat Input */}
        <section>
          <h2 className="text-lg font-semibold mb-2">RAG Chat</h2>
          <div className="flex flex-col gap-2">
            <input
              type="text"
              value={ragInput}
              onChange={e => setRagInput(e.target.value)}
              disabled={loading}
              placeholder="Type your RAG message..."
              className="p-2 border rounded"
            />
            <div className="flex gap-2 items-center">
              <label className="font-medium">Knowledge Base:</label>
              <select
                value={selectedKb}
                onChange={e => setSelectedKb(e.target.value)}
                disabled={loading}
                className="border rounded p-2 flex-1"
              >
                {kbs.map(kb => (
                  <option key={kb.name} value={kb.name}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2 items-center">
              <label className="font-medium">Embedding Model:</label>
              <select
                value={embeddingModel}
                onChange={e => setEmbeddingModel(e.target.value as EmbeddingModel)}
                disabled={loading}
                className="border rounded p-2 flex-1"
              >
                {embeddingModels.map(model => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2 items-center">
              <label className="font-medium">Top K Chunks:</label>
              <input
                type="number"
                min={1}
                max={10}
                value={retrievalK}
                onChange={e => setRetrievalK(Number(e.target.value))}
                disabled={loading}
                className="border rounded p-2 w-20"
              />
            </div>

            <button
              onClick={sendRagMessage}
              disabled={loading || !ragInput.trim()}
              className="bg-purple-600 text-white px-4 rounded hover:bg-purple-700 disabled:opacity-50"
            >
              Send RAG
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
