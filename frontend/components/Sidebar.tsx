'use client';

import React from 'react';

interface Conversation {
  id: string;
  title: string;
}

interface SidebarProps {
  conversations: Conversation[];
  currentConvId: string | null;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
  username: string | null;
  onLogout: () => void;
}

export default function Sidebar({
  conversations,
  currentConvId,
  onSelectConversation,
  onCreateConversation,
  username,
  onLogout,
}: SidebarProps) {
  return (
    <aside className="w-64 bg-white border-r flex flex-col h-full p-4">
      <div className="mb-6">
        <h2 className="text-xl font-bold mb-2">👋 Hello{username ? `, ${username}` : ''}</h2>
        <button
          onClick={onLogout}
          className="text-sm text-red-600 hover:text-red-800 transition-colors"
          aria-label="Logout"
        >
          🚪 Logout
        </button>
      </div>

      <button
        onClick={onCreateConversation}
        className="mb-4 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        aria-label="Create new conversation"
      >
        + New Conversation
      </button>

      <nav className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <p className="text-gray-500 text-center mt-8">No conversations yet.</p>
        ) : (
          conversations.map(({ id, title }) => {
            const isSelected = currentConvId === id;
            return (
              <button
                key={id}
                onClick={() => onSelectConversation(id)}
                className={`w-full text-left px-3 py-2 rounded mb-1 transition-colors
                  ${
                    isSelected
                      ? 'bg-blue-100 font-semibold text-blue-700'
                      : 'hover:bg-gray-100'
                  }`}
                aria-current={isSelected ? 'page' : undefined}
              >
                {title}
              </button>
            );
          })
        )}
      </nav>
    </aside>
  );
}


//how to use the above code

// import Sidebar from '../components/Sidebar';

// function Page() {
//   const [conversations, setConversations] = React.useState<Conversation[]>([]);
//   const [currentConvId, setCurrentConvId] = React.useState<string | null>(null);
//   const username = "irfan";

//   const handleCreateConversation = () => {
//     // Your logic to create conversation
//   };

//   const handleSelectConversation = (id: string) => {
//     setCurrentConvId(id);
//   };

//   const handleLogout = () => {
//     // Your logout logic
//   };

//   return (
//     <div className="flex h-screen">
//       <Sidebar
//         conversations={conversations}
//         currentConvId={currentConvId}
//         onCreateConversation={handleCreateConversation}
//         onSelectConversation={handleSelectConversation}
//         username={username}
//         onLogout={handleLogout}
//       />
//       {/* Your main content */}
//     </div>
//   );
// }
