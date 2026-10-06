import React from 'react';
import type { TranscriptItem } from '../services/voice';
import { User, Bot, Wrench } from 'lucide-react';

interface TranscriptProps {
  items: TranscriptItem[];
}

export const Transcript: React.FC<TranscriptProps> = ({ items }) => {
  return (
    <div className="transcript-panel glass-panel p-6 rounded-2xl flex-1 overflow-y-auto max-h-[380px] min-h-[220px]">
      <div className="text-xs uppercase tracking-wider text-gray-400 font-semibold mb-4">
        Conversation Transcript & Live Tool Calls
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
                    : item.sender === 'tool'
                    ? 'bg-amber-600/30 text-amber-400 border border-amber-500/30'
                    : 'bg-purple-600/30 text-purple-400 border border-purple-500/30'
                }`}
              >
                {item.sender === 'user' ? (
                  <User className="w-5 h-5" />
                ) : item.sender === 'tool' ? (
                  <Wrench className="w-5 h-5" />
                ) : (
                  <Bot className="w-5 h-5" />
                )}
              </div>
              <div
                className={`p-4 rounded-2xl border text-sm max-w-xl ${
                  item.sender === 'tool'
                    ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                    : 'bg-gray-900/70 border-gray-800 text-gray-200'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-xs text-gray-400">
                    {item.sender === 'user' ? 'User' : item.sender === 'tool' ? 'Tool Call Executed' : 'AI Assistant'}
                  </span>
                  <span className="text-[10px] text-gray-500">{item.timestamp}</span>
                </div>
                {item.sender === 'tool' ? (
                  <div className="space-y-1 font-mono text-xs">
                    <div className="font-bold text-amber-300">⚙️ {item.toolName}</div>
                    <div className="text-amber-400/80">Args: {JSON.stringify(item.toolArgs)}</div>
                    {item.toolResult && (
                      <div className="text-emerald-400 text-[11px] bg-black/40 p-2 rounded border border-emerald-500/20 mt-1 overflow-x-auto">
                        Result: {JSON.stringify(item.toolResult)}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="leading-relaxed">{item.text}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
