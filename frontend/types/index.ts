// types/index.ts

export interface Conversation {
  id: string;
  title: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  user_name?: string;
  created_at?: string;
}

export interface User {
  id: string;
  username: string;
  full_name?: string;
  email?: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
}


//how to use the above 
// import { Conversation, Message } from '../types';

// function MyComponent({ conversations }: { conversations: Conversation[] }) {
//   // ...
// }
