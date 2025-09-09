import React from 'react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  userName?: string;
}

export default function MessageBubble({ role, content, userName }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div
      className={`max-w-[70%] my-2 p-4 rounded-lg break-words
        ${isUser ? 'bg-blue-600 text-white self-end rounded-br-none' : 'bg-gray-200 text-gray-900 self-start rounded-bl-none'}`}
      style={{ whiteSpace: 'pre-wrap' }}
      aria-live="polite"
    >
      {isUser && userName && (
        <div className="text-xs font-semibold mb-1 opacity-80">{userName}</div>
      )}
      <div>{content}</div>
    </div>
  );
}

//how to use it
{/* <MessageBubble role="user" content="Hello! How can I help you?" userName="Irfan" />

<MessageBubble role="assistant" content="Hi Irfan, what do you want to know today?" /> */}
