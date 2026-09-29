import React from 'react';
import type { TranscriptItem } from '../services/voice';
import { User, Bot } from 'lucide-react';

interface TranscriptProps {
  items: TranscriptItem[];
}

export const Transcript: React.FC<TranscriptProps> = ({ items }) => {
  return (
    <div className="transcript-panel glass-panel p-6 rounded-2xl flex-1 overflow-y-auto max-h-[380px] min-h-[220px]">
      <div className="text-xs uppercase tracking-wider text-gray-400 font-semibold mb-4">
        Conversation Transcript
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-gray-500 text-sm">
          <p>Click "Start Call" and begin speaking to start conversation.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div
              key={item.id}
              className={`flex space-x-3 ${item.sender === 'user' ? 'justify-start' : 'justify-start'}`}
            >
              <div
                className={`p-2 rounded-xl shrink-0 ${
                  item.sender === 'user'
                    ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30'
                    : 'bg-purple-600/30 text-purple-400 border border-purple-500/30'
                }`}
              >
                {item.sender === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>
              <div className="bg-gray-900/70 p-4 rounded-2xl border border-gray-800 text-gray-200 text-sm max-w-xl">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-xs text-gray-400">
                    {item.sender === 'user' ? 'User' : 'AI Assistant'}
                  </span>
                  <span className="text-[10px] text-gray-500">{item.timestamp}</span>
                </div>
                <p className="leading-relaxed">{item.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
