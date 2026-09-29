import { useState } from 'react';
import { CallStatus } from './components/CallStatus';
import { CallControls } from './components/CallControls';
import { Transcript } from './components/Transcript';
import { voiceService, type CallState, type TranscriptItem } from './services/voice';
import { Radio } from 'lucide-react';
import './styles/App.css';

export function App() {
  const [callState, setCallState] = useState<CallState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [micActive, setMicActive] = useState<boolean>(false);
  const [transcript] = useState<TranscriptItem[]>([
    {
      id: 'demo-1',
      sender: 'user',
      text: 'Hello, how are you?',
      timestamp: '12:00 PM',
    },
    {
      id: 'demo-2',
      sender: 'ai',
      text: "I'm doing well. How can I help?",
      timestamp: '12:00 PM',
    },
  ]);

  const handleStartCall = async () => {
    setErrorMessage(null);
    setCallState('connecting');

    try {
      const { sessionId } = await voiceService.startCall();
      setMicActive(true);
      setCallState('connected');

      // Simulate real-time interaction states for POC demonstration
      setTimeout(() => {
        setCallState('listening');
      }, 1200);

      console.log(`Call session started: ${sessionId}`);
    } catch (err: any) {
      console.error('Start call error:', err);
      setCallState('error');
      setMicActive(false);
      setErrorMessage(err.message || 'Unable to connect to the Voice AI service. Please try again.');
    }
  };

  const handleEndCall = async () => {
    setCallState('ending');
    try {
      await voiceService.endCall();
    } catch (err) {
      console.error('End call error:', err);
    } finally {
      setMicActive(false);
      setCallState('disconnected');
      setTimeout(() => {
        setCallState('idle');
      }, 800);
    }
  };

  return (
    <div className="w-full max-w-2xl px-4 py-8 mx-auto">
      <header className="text-center mb-8">
        <div className="inline-flex items-center space-x-3 bg-slate-900/80 px-4 py-2 rounded-full border border-slate-800 mb-3 shadow-md">
          <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold tracking-wider text-slate-300 uppercase">
            Pipecat Real-time Pipeline
          </span>
        </div>
        <h1 className="text-4xl font-extrabold text-white tracking-tight sm:text-5xl">
          Voice AI WebCall
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Open-Source Real-Time Browser Voice Assistant
        </p>
      </header>

      <main className="glass-card rounded-3xl p-8 relative overflow-hidden">
        <CallStatus state={callState} errorMessage={errorMessage} micActive={micActive} />

        <CallControls
          state={callState}
          onStartCall={handleStartCall}
          onEndCall={handleEndCall}
        />

        <Transcript items={transcript} />
      </main>

      <footer className="text-center text-xs text-slate-500 mt-6">
        Voice AI WebCall POC &bull; Built with Pipecat & React + Vite
      </footer>
    </div>
  );
}

export default App;
