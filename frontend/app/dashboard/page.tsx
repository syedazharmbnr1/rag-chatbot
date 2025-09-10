
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Trash2 } from "lucide-react";

// UUID generation utility with fallback
function generateUUID(): string {
  // Try to use crypto.randomUUID if available
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  
  // Fallback for environments without crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
} 

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  user_name?: string;
  timestamp?: Date;
  sources?: Array<{
    source: string;
    page: number;
    score: number;
  }>;
};

type Conversation = {
  id: string;
  title: string;
};

type KnowledgeBase = {
  name: string;
  id?: string;
};

const API_URL = 'http://34.70.203.66:8002';

export default function DashboardPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [ragMessages, setRagMessages] = useState<Message[]>([]); // Separate messages for RAG mode
  const [userInput, setUserInput] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // RAG Chat States
  const [chatMode, setChatMode] = useState<'direct' | 'rag'>('direct');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<string>('');
  const [embeddingModel, setEmbeddingModel] = useState('llama3.2:latest');
  const [retrievalK, setRetrievalK] = useState(4);
  
  // File Upload States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const embeddingModels = ['text-embedding-3-small', 'llama3.2:latest'] as const;
  type EmbeddingModelKey = typeof embeddingModels[number];
  const chatModelMap: Record<EmbeddingModelKey, string> = {
    'text-embedding-3-small': 'gpt-4o-mini',
    'llama3.2:latest': 'llama3.2:latest'
  };

  // Determine compatible embedding model from selected chat model, mirroring Streamlit logic
  useEffect(() => {
    const m = model || '';
    let compatible: EmbeddingModelKey = 'text-embedding-3-small';
    if (m.startsWith('gpt')) compatible = 'text-embedding-3-small';
    else if (m.startsWith('llama')) compatible = 'llama3.2:latest';
    if (compatible !== embeddingModel) {
      setEmbeddingModel(compatible);
    }
  }, [model]);


  const handleDeleteConversation = async (convId: string) => {
  if (!confirm("Are you sure you want to delete this conversation?")) return;

  try {
    await authFetch(`${API_URL}/delete/conversations/${convId}`, {
      method: "DELETE",
    });

    // Remove it from UI
    setConversations(prev => prev.filter(c => c.id !== convId));

    if (selectedConvId === convId) {
      setSelectedConvId(null);
      setMessages([]);
    }
  } catch (err) {
    console.error("Error deleting conversation:", err);
  }
};


  // Get current messages based on chat mode
  const getCurrentMessages = () => {
    return chatMode === 'direct' ? messages : ragMessages;
  };

  // Set current messages based on chat mode
  const setCurrentMessages = (newMessages: Message[] | ((prev: Message[]) => Message[])) => {
    if (chatMode === 'direct') {
      setMessages(newMessages);
    } else {
      setRagMessages(newMessages);
    }
  };

  // Check if chat interface should be shown
  const shouldShowChatInterface = () => {
    if (chatMode === 'direct') {
      return selectedConvId !== null;
    } else {
      return knowledgeBases.length > 0 && selectedKB !== '';
    }
  };

  // Fetch session token and user ID
  useEffect(() => {
    const t = localStorage.getItem('token');
    const u = localStorage.getItem('user_id');
    if (!t || !u) {
      router.push('/login');
    } else {
      setToken(t);
      setUserId(u);
    }
  }, [router]);

  // Helper fetch with Authorization header
  const authFetch = async (url: string, options: RequestInit = {}) => {
    if (!token) throw new Error("No token available");
    return fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        "Authorization": `Bearer ${token}`,
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      },
    });
  };

  // Function to refresh knowledge bases
  const refreshKnowledgeBases = async () => {
    if (!token) return;
    
    try {
      const res = await authFetch(`${API_URL}/knowledge_bases/compatible?embedding_model=${encodeURIComponent(embeddingModel)}`);
      const data = await res.json();
      
      // Backend returns List[str] of kb names. Normalize to { name } objects.
      let normalized: KnowledgeBase[] = [];
      if (Array.isArray(data)) {
        if (data.length > 0 && typeof data[0] === 'string') {
          normalized = (data as string[]).map((name) => ({ name }));
        } else {
          normalized = (data as any[]).map((kb) => ({ name: kb?.name ?? String(kb) }));
        }
      }
      
      setKnowledgeBases(normalized);
      
      // Auto-select the first KB if none is selected or if the current selection doesn't exist
      const hasSelected = normalized.some(kb => kb.name === selectedKB);
      if (!hasSelected && normalized.length > 0) {
        setSelectedKB(normalized[0].name);
      }
      
      console.log('Knowledge bases refreshed:', normalized);
    } catch (err) {
      console.error("Error refreshing knowledge bases:", err);
    }
  };

  // Fetch conversations
  useEffect(() => {
    if (!userId || !token) return;
    authFetch(`${API_URL}/conversations?user_id=${userId}`)
      .then(res => res.json())
      .then((rows: Array<{ id: number | string; title: string; created_at: string; conversation_type?: string }>) => {
        // Normalize id to string
        const normalized = rows.map(r => ({ id: String(r.id), title: r.title, conversation_type: r.conversation_type || 'direct' } as any));
        setConversations(normalized as any);
      })
      .catch(err => console.error("Error fetching conversations:", err));
  }, [userId, token]);

  // Fetch compatible knowledge bases for the selected embedding model
  useEffect(() => {
    if (!token) return;
    authFetch(`${API_URL}/knowledge_bases/compatible?embedding_model=${encodeURIComponent(embeddingModel)}`)
      .then(res => res.json())
      .then((data) => {
        // Backend returns List[str] of kb names. Normalize to { name } objects.
        let normalized: KnowledgeBase[] = [];
        if (Array.isArray(data)) {
          if (data.length > 0 && typeof data[0] === 'string') {
            normalized = (data as string[]).map((name) => ({ name }));
          } else {
            normalized = (data as any[]).map((kb) => ({ name: kb?.name ?? String(kb) }));
          }
        }
        setKnowledgeBases(normalized);
        // Ensure a selected KB is set if available
        const hasSelected = normalized.some(kb => kb.name === selectedKB);
        if (!hasSelected) {
          setSelectedKB(normalized.length > 0 ? normalized[0].name : '');
        }
      })
      .catch(err => console.error("Error fetching compatible knowledge bases:", err));
  }, [token, embeddingModel]);

  // Fetch messages for direct chat
  useEffect(() => {
    if (!selectedConvId || !token || chatMode !== 'direct') return;
    authFetch(`${API_URL}/messages?conversation_id=${selectedConvId}`)
      .then(res => res.json())
      .then(setMessages)
      .catch(err => console.error("Error fetching messages:", err));
  }, [selectedConvId, token, chatMode]);

  // Fetch messages for RAG chat
  useEffect(() => {
    if (!selectedConvId || !token || chatMode !== 'rag') return;
    authFetch(`${API_URL}/messages?conversation_id=${selectedConvId}`)
      .then(res => res.json())
      .then(setRagMessages)
      .catch(err => console.error("Error fetching RAG messages:", err));
  }, [selectedConvId, token, chatMode]);

  // Handle mode switching
  const handleModeSwitch = () => {
    const newMode = chatMode === 'direct' ? 'rag' : 'direct';
    setChatMode(newMode);
    
    // Clear selection when switching modes to avoid confusion
    if (newMode === 'rag') {
      setSelectedConvId(null);
    }
  };

  const handleNewConversation = async () => {
    try {
      const res = await authFetch(`${API_URL}/create/conversations`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, title: 'New Chat', conversation_type: 'direct' }),
      });
      const data = await res.json();
      setSelectedConvId(String(data.id));
      setConversations([...conversations, { id: String(data.id), title: data.title, conversation_type: data.conversation_type } as any]);
      setMessages([]);
      
      // Switch to direct mode when creating a new conversation
      if (chatMode !== 'direct') {
        setChatMode('direct');
      }
    } catch (err) {
      console.error("Error creating conversation:", err);
    }
  };

  const handleSendMessage = async () => {
    if (!userInput.trim() || isLoading) return;
    
    // Check requirements based on mode
    if (chatMode === 'direct' && !selectedConvId) return;
    if (chatMode === 'rag' && !selectedKB) return;
    
    const userMessage = {
      role: 'user' as const,
      content: userInput,
      id: generateUUID(),
      user_name: 'You',
      timestamp: new Date()
    };

    setCurrentMessages(prev => [...prev, userMessage]);
    setUserInput('');
    setIsLoading(true);

    try {
      let endpoint, payload;
      
      if (chatMode === 'direct') {
        endpoint = `${API_URL}/query/direct`;
        payload = {
          conversation_id: selectedConvId,
          query: userInput,
          model_name: model,
        };
      } else {
        endpoint = `${API_URL}/query/rag`;
        let convId = selectedConvId;
        if (!convId) {
          const createdRes = await authFetch(`${API_URL}/create/conversations`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, title: 'RAG Chat', conversation_type: 'rag' }),
          });
          const created = await createdRes.json();
          convId = String(created.id);
          setSelectedConvId(convId);
          setConversations(prev => [...prev, { id: convId, title: created.title, conversation_type: created.conversation_type } as any]);
        }
        payload = {
          conversation_id: convId,
          query: userInput,
          kb_names: [selectedKB],
          embedding_model: embeddingModel,
          chat_model: chatModelMap[embeddingModel as EmbeddingModelKey] || 'gpt-4o-mini',
          retrieval_k: retrievalK
        };
      }

      const res = await authFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      
      const assistantMessage = {
        role: 'assistant' as const,
        content: data.response,
        id: generateUUID(),
        timestamp: new Date(),
        sources: data.sources || undefined
      };

      setCurrentMessages(prev => [...prev, assistantMessage]);

      // Update conversation title for both modes
      if (selectedConvId) {
        try {
          await authFetch(`${API_URL}/update/conversations/${selectedConvId}/title`, {
            method: 'PUT'
          });
          // Refresh conversations to get updated title
          const updatedRes = await authFetch(`${API_URL}/conversations?user_id=${userId}`);
          const updatedRows = await updatedRes.json();
          const normalized = updatedRows.map((r: any) => ({ id: String(r.id), title: r.title, conversation_type: r.conversation_type || 'direct' } as any));
          setConversations(normalized as any);
        } catch (err) {
          console.error("Error updating title:", err);
        }
      }
    } catch (err) {
      console.error("Error sending message:", err);
      setCurrentMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!uploadFile || isUploading) return;
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('embedding_model_name', embeddingModel);
      formData.append('chunk_size', '1000');
      formData.append('chunk_overlap', '200');

      const res = await authFetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const result = await res.json();
        console.log('Upload successful:', result);
        setUploadFile(null);
        
        // Refresh knowledge bases using the compatible endpoint to get properly formatted data
        await refreshKnowledgeBases();
        
        // Auto-switch to RAG mode if not already in RAG mode
        if (chatMode !== 'rag') {
          setChatMode('rag');
        }
        
        // Show success message
        alert('Document uploaded successfully! You can now use it in RAG Chat.');
      } else {
        const errorText = await res.text();
        console.error('Upload failed with status:', res.status);
        console.error('Upload error response:', errorText);
        alert(`Upload failed: ${res.status} - ${errorText}`);
      }
    } catch (err) {
      console.error("Error uploading file:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push('/login');
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const currentMessages = getCurrentMessages();

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100 text-slate-800">
      {/* Sidebar */}
      <div className={`${sidebarCollapsed ? 'w-16' : 'w-80'} transition-all duration-300 bg-white/80 backdrop-blur-sm border-r border-slate-200 flex flex-col shadow-xl`}>
        {/* Header */}
        <div className=" border-slate-200">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className='flex flex-row items-center'>
                <img src="/rag-logo.png" alt="Logo" className="w- h-34 rounded-full " />                
              </div>
            )}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <svg className={`w-4 h-4 text-slate-600 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* User Info */}
        {!sidebarCollapsed && userId && (
          <div className="px-6 bg-slate-50 border-b border-slate-200">
            <p className="text-sm text-slate-600"> Hello, <span className="font-semibold">{userId}</span></p>
          </div>
        )}

        {/* Mode Toggle */}
        {!sidebarCollapsed && (
          <div className="p-4 border-b border-slate-200">
            <button
              onClick={handleModeSwitch}
              className="w-full bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-3 rounded-xl hover:from-red-800 hover:to-red-800 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center gap-2 font-medium"
            >
              {chatMode === 'direct' ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Switch to RAG Chat
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Switch to Direct Chat
                </>
              )}
            </button>
          </div>
        )}

        {/* New Chat Button - Only show in direct mode */}
        {!sidebarCollapsed && chatMode === 'direct' && (
          <div className="p-4">
            <button
              onClick={handleNewConversation}
              className="w-full bg-gradient-to-r from-slate-950 to-slate-950 text-white px-4 py-3 rounded-xl hover:from-slate-600 hover:to-slate-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center gap-2 font-medium"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Conversation
            </button>
          </div>
        )}

        {/* Conversations List - Only show in direct mode */}
        {/* {!sidebarCollapsed && chatMode === 'direct' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => setSelectedConvId(conv.id)}
                className={`p-3 rounded-xl cursor-pointer transition-all duration-200 group ${
                  selectedConvId === conv.id 
                    ? 'bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 shadow-sm' 
                    : 'hover:bg-slate-50 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full transition-all ${
                    selectedConvId === conv.id ? 'bg-blue-500' : 'bg-slate-300 group-hover:bg-slate-400'
                  }`} />
                  <span className={`text-sm font-medium truncate ${
                    selectedConvId === conv.id ? 'text-blue-700' : 'text-slate-700'
                  }`}>
                    {conv.title}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )} */}



{!sidebarCollapsed && chatMode === 'direct' && (
  <div className="flex-1 overflow-y-auto p-4 space-y-2">
    {conversations.filter((c: any) => (c.conversation_type || 'direct') === 'direct').map((conv: any) => (
      <div
        key={conv.id}
        className={`p-3 rounded-xl cursor-pointer transition-all duration-200 group flex items-center justify-between ${
          selectedConvId === conv.id 
            ? 'bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 shadow-sm' 
            : 'hover:bg-slate-50 border border-transparent'
        }`}
      >
        {/* Left side: dot + title */}
        <div
          className="flex items-center gap-3 flex-1"
          onClick={() => setSelectedConvId(conv.id)}
        >
          <div className={`w-2 h-2 rounded-full transition-all ${
            selectedConvId === conv.id ? 'bg-blue-500' : 'bg-slate-300 group-hover:bg-slate-400'
          }`} />
          <span className={`text-sm font-medium truncate ${
            selectedConvId === conv.id ? 'text-blue-700' : 'text-slate-700'
          }`}>
            {conv.title}
          </span>
        </div>

        {/* Right side: delete button */}
        <button
          onClick={(e) => {
            e.stopPropagation(); // prevent triggering setSelectedConvId
            handleDeleteConversation(conv.id);
          }}
          className="p-1 text-slate-400 hover:text-red-600 transition-colors"
        >
          <Trash2 size={16} />
        </button>
      </div>
    ))}
    {conversations.filter((c: any) => (c.conversation_type || 'direct') === 'direct').length === 0 && (
      <div className="text-xs text-slate-500 px-2">No direct conversations yet.</div>
    )}
  </div>
)}


        {/* RAG Mode Info - Only show in RAG mode */}
        {!sidebarCollapsed && chatMode === 'rag' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {conversations.filter((c: any) => c.conversation_type === 'rag').map((conv: any) => (
              <div
                key={conv.id}
                className={`p-3 rounded-xl cursor-pointer transition-all duration-200 group flex items-center justify-between ${
                  selectedConvId === conv.id 
                    ? 'bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 shadow-sm' 
                    : 'hover:bg-slate-50 border border-transparent'
                }`}
              >
                <div
                  className="flex items-center gap-3 flex-1"
                  onClick={() => setSelectedConvId(conv.id)}
                >
                  <div className={`w-2 h-2 rounded-full transition-all ${
                    selectedConvId === conv.id ? 'bg-emerald-500' : 'bg-slate-300 group-hover:bg-slate-400'
                  }`} />
                  <span className={`text-sm font-medium truncate ${
                    selectedConvId === conv.id ? 'text-emerald-700' : 'text-slate-700'
                  }`}>
                    {conv.title}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {conversations.filter((c: any) => c.conversation_type === 'rag').length === 0 && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-emerald-700 mb-2">RAG Chat Mode</h3>
                <p className="text-xs text-emerald-600 mb-3">
                  Ask questions about your uploaded documents using advanced retrieval.
                </p>
                {knowledgeBases.length === 0 ? (
                  <p className="text-xs text-amber-600">
                    ⚠️ No knowledge bases available. Upload documents to get started.
                  </p>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs text-emerald-600">
                      {knowledgeBases.length} knowledge base(s) available
                    </p>
                    <p className="text-xs text-slate-600">
                      Currently using: <strong>{selectedKB}</strong>
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* File Upload Section */}
        {!sidebarCollapsed && (
          <div className="p-4 border-t border-slate-200 space-y-4">
            <h3 className="text-sm font-Mobile text-slate-700"> Upload Document</h3>
            
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            
            {uploadFile && (
              <>
                <select
                  value={embeddingModel}
                  onChange={(e) => setEmbeddingModel(e.target.value)}
                  className="w-full p-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {embeddingModels.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
                
                <div className="text-xs text-slate-600 bg-slate-50 p-2 rounded-lg">
                  <span className="font-medium">Chunking Strategy:</span> Auto-selected (Semantic for GPT, Recursive for Llama)
                </div>
                
                <button
                  onClick={handleFileUpload}
                  disabled={isUploading}
                  className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white px-4 py-2 rounded-lg hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 text-sm font-medium"
                >
                  {isUploading ? 'Uploading...' : 'Upload to KB'}
                </button>
              </>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="p-4 border-t border-slate-200">
          <button
            onClick={handleLogout}
            className={`${sidebarCollapsed ? 'w-8 h-8 p-0' : 'w-full px-4 py-2'} text-red-500 hover:bg-red-50 rounded-lg transition-colors flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2'} text-sm font-medium`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {!sidebarCollapsed && 'Sign Out'}
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-Mobile text-slate-800">
                  {chatMode === 'direct' 
                    ? (selectedConvId ? conversations.find(c => c.id === selectedConvId)?.title || 'Chat' : 'Select a Conversation')
                    : (selectedConvId ? conversations.find(c => c.id === selectedConvId)?.title || 'RAG Chat' : 'RAG Chat')
                  }
                </h1>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  chatMode === 'direct' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'bg-emerald-100 text-emerald-700'
                }`}>
                  {chatMode === 'direct' ? 'Direct Chat' : 'RAG Chat'}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {chatMode === 'direct' 
                  ? (selectedConvId ? `Model: ${model}` : 'Choose a conversation to start chatting')
                  : (knowledgeBases.length > 0 
                      ? `KB: ${selectedKB} | Embedding: ${embeddingModel} | K: ${retrievalK}`
                      : 'Upload documents to start RAG chat'
                    )
                }
              </p>
            </div>
            
            {/* Model/Settings Selector */}
            <div className="flex items-center gap-4">
              {chatMode === 'direct' ? (
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-slate-600">Model:</label>
                  <select 
                    value={model} 
                    onChange={(e) => setModel(e.target.value)} 
                    className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
                  >
                    <option value="gpt-4o-mini">GPT-4O Mini</option>
                    <option value="llama3.2:latest">Llama 3.2</option>
                  </select>
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-slate-600">KB:</label>
                    <select 
                      value={selectedKB} 
                      onChange={(e) => setSelectedKB(e.target.value)}
                      className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent shadow-sm"
                    >
                      {knowledgeBases.map((kb, idx) => (
                        <option key={kb.id ?? `${kb.name}-${idx}`} value={kb.name}>{kb.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-slate-600">K:</label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={retrievalK}
                      onChange={(e) => setRetrievalK(parseInt(e.target.value))}
                      className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent shadow-sm w-20"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {shouldShowChatInterface() ? (
            currentMessages.length > 0 ? (
              currentMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                >
                  <div className={`max-w-3xl px-4 py-3 rounded-2xl shadow-sm ${
                    msg.role === 'user'
                      ? chatMode === 'direct'
                        ? 'bg-gradient-to-r from-slate-700 to-slate-600 text-white'
                        : 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-800'
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium opacity-75">
                        {msg.role === 'user' 
                          ? msg.user_name || 'You' 
                          : chatMode === 'rag' 
                            ? 'RAG Assistant' 
                            : 'Assistant'
                        }
                      </span>
                      {msg.timestamp && (
                        <span className="text-xs opacity-50">
                          {formatTime(msg.timestamp)}
                        </span>
                      )}
                    </div>
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-200">
                        <p className="text-xs font-medium text-slate-600 mb-2">Sources:</p>
                        <div className="space-y-1">
                          {msg.sources.map((source, idx) => (
                            <div key={idx} className="text-xs text-slate-500">
                              📄 {source.source} (Page {source.page}, Score: {source.score.toFixed(3)})
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 ${
                  chatMode === 'direct' 
                    ? 'bg-gradient-to-br from-blue-100 to-purple-100' 
                    : 'bg-gradient-to-br from-emerald-100 to-teal-100'
                }`}>
                  <svg className={`w-8 h-8 ${
                    chatMode === 'direct' ? 'text-blue-500' : 'text-emerald-500'
                  }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className={`text-lg font-semibold mb-2 ${
                  chatMode === 'direct' ? 'text-slate-700' : 'text-slate-700'
                }`}>
                  {chatMode === 'direct' 
                    ? 'Start a new conversation'
                    : 'Ready for RAG Chat'
                  }
                </h3>
                <p className="text-slate-500 text-sm max-w-md">
                  {chatMode === 'direct' 
                    ? 'Choose a conversation from the sidebar or create a new one to start chatting.'
                    : 'Ask questions about your uploaded documents and get AI-powered answers with source citations.'
                  }
                </p>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-amber-100 to-orange-100 rounded-2xl flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">
                {chatMode === 'direct' 
                  ? 'No conversation selected'
                  : 'No knowledge base available'
                }
              </h3>
              <p className="text-slate-500 text-sm max-w-md">
                {chatMode === 'direct' 
                  ? 'Please select a conversation from the sidebar or create a new one to start chatting.'
                  : 'Upload documents to create a knowledge base before you can start RAG chat.'
                }
              </p>
            </div>
          )}
        </div>

        {/* Input Area */}
        {shouldShowChatInterface() && (
          <div className="border-t border-slate-200 bg-white/80 backdrop-blur-sm p-6">
            <div className="max-w-4xl mx-auto">
              <div className="relative flex items-end gap-4">
                <div className="flex-1 relative">
                  <textarea
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={`Ask me anything${chatMode === 'rag' ? ' about your documents' : ''}...`}
                    disabled={isLoading}
                    className="w-full p-4 pr-12 border border-slate-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none min-h-[60px] max-h-32 bg-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    rows={1}
                    style={{ fieldSizing: 'content' } as any}
                  />
                  {isLoading && (
                    <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-slate-300 border-t-blue-500"></div>
                    </div>
                  )}
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={!userInput.trim() || isLoading}
                  className={`px-6 py-4 rounded-2xl font-medium transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                    chatMode === 'direct'
                      ? 'bg-gradient-to-r from-green-900 to-green-900 hover:from-emerald-600 hover:to-teal-700 text-white'
                      : 'bg-gradient-to-r from-slate-900 to-slate-900 hover:from-emerald-600 hover:to-teal-700 text-white'
                  }`}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  Send
                </button>
              </div>
              
              {/* Quick Actions */}
              <div className="flex items-center justify-between mt-4 text-sm text-slate-500">
                <div className="flex items-center gap-4">
                  <span>Press Enter to send, Shift+Enter for new line</span>
                  {chatMode === 'rag' && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      RAG Mode Active
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400">
                  {currentMessages.length} message{currentMessages.length !== 1 ? 's' : ''}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}