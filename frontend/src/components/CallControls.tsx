import React from 'react';
import type { CallState } from '../services/voice';
import { PhoneCall, PhoneOff } from 'lucide-react';

interface CallControlsProps {
  state: CallState;
  onStartCall: () => void;
  onEndCall: () => void;
}

export const CallControls: React.FC<CallControlsProps> = ({ state, onStartCall, onEndCall }) => {
  const isCallActive =
    state === 'connecting' ||
    state === 'connected' ||
    state === 'listening' ||
    state === 'processing' ||
    state === 'speaking';

  return (
    <div className="flex items-center justify-center space-x-6 my-8">
      {!isCallActive ? (
        <button
          id="btn-start-call"
          onClick={onStartCall}
          className="btn-start shadow-lg shadow-emerald-500/20 flex items-center space-x-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-semibold text-lg transition-all duration-300 transform hover:scale-105 active:scale-95"
        >
          <PhoneCall className="w-6 h-6" />
          <span>Start Call</span>
        </button>
      ) : (
        <button
          id="btn-end-call"
          onClick={onEndCall}
          className="btn-end shadow-lg shadow-rose-500/20 flex items-center space-x-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-rose-600 to-red-700 hover:from-rose-500 hover:to-red-600 text-white font-semibold text-lg transition-all duration-300 transform hover:scale-105 active:scale-95"
        >
          <PhoneOff className="w-6 h-6" />
          <span>End Call</span>
        </button>
      )}
    </div>
  );
};
