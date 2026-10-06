import { useEffect, useState } from 'react';
import { CallStatus } from './components/CallStatus';
import { CallControls } from './components/CallControls';
import { Transcript } from './components/Transcript';
import { NoiseCancellationPanel } from './components/NoiseCancellationPanel';
import { voiceService, type CallState, type TranscriptItem } from './services/voice';
import { Radio } from 'lucide-react';
import './styles/App.css';

export function App() {
  const [callState, setCallState] = useState<CallState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [micActive, setMicActive] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);

  useEffect(() => {
    // Subscribe to voice call state changes
    voiceService.onStateUpdate = (newState: CallState) => {
      setCallState(newState);
      if (newState === 'listening' || newState === 'processing' || newState === 'speaking' || newState === 'connected') {
        setMicActive(true);
      } else if (newState === 'idle' || newState === 'disconnected' || newState === 'error') {
        setMicActive(false);
      }
    };

    // Subscribe to real-time conversation transcripts
    voiceService.onTranscriptUpdate = (item: TranscriptItem) => {
      setTranscript((prev) => {
        // If updating an ongoing AI response stream, replace or append
        const last = prev[prev.length - 1];
        if (last && last.sender === item.sender && item.sender === 'ai') {
          return [...prev.slice(0, -1), item];
        }
        return [...prev, item];
      });
    };
  }, []);

  const handleStartCall = async () => {
    setErrorMessage(null);
    setTranscript([]);
    setCallState('connecting');

    try {
      const { sessionId } = await voiceService.startCall();
      console.log(`[APP] Call session started successfully: ${sessionId}`);
    } catch (err: any) {
      console.error('[APP] Start call error:', err);
      setCallState('error');
      setMicActive(false);
      setErrorMessage(err.message || 'Unable to connect to the Voice AI service. Please check backend logs.');
    }
  };

  const handleEndCall = async () => {
    setCallState('ending');
    try {
      await voiceService.endCall();
    } catch (err) {
      console.error('[APP] End call error:', err);
    } finally {
      setMicActive(false);
    }
  };

  return (
    <div className="w-full max-w-3xl px-4 py-8 mx-auto">
      <header className="text-center mb-8">
        <div className="inline-flex items-center space-x-3 bg-slate-900/80 px-4 py-2 rounded-full border border-slate-800 mb-3 shadow-md">
          <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold tracking-wider text-slate-300 uppercase">
            Pipecat Real-time Voice Pipeline
          </span>
        </div>
        <h1 className="text-4xl font-extrabold text-white tracking-tight sm:text-5xl">
          Voice AI WebCall
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Real-Time Browser Voice Assistant with Dynamic Noise Cancellation & FreeSWITCH ESL Toolcalls
        </p>
      </header>

      <main className="glass-card rounded-3xl p-6 sm:p-8 relative overflow-hidden">
        <CallStatus state={callState} errorMessage={errorMessage} micActive={micActive} />

        <CallControls
          state={callState}
          onStartCall={handleStartCall}
          onEndCall={handleEndCall}
        />

        <Transcript items={transcript} />

        <NoiseCancellationPanel />
      </main>

      <footer className="text-center text-xs text-slate-500 mt-6">
        Voice AI WebCall POC &bull; Built with Pipecat, FreeSWITCH ESL & React + Vite
      </footer>
    </div>
  );
}

export default App;
