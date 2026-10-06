import React, { useState, useEffect } from 'react';
import { voiceService, type NoiseCancellationInfo, type FreeSwitchStatus } from '../services/voice';
import { Shield, Radio, Terminal, Cpu, CheckCircle2, Sliders, PhoneCall, RefreshCw, Send } from 'lucide-react';

interface Props {
  className?: string;
}

export const NoiseCancellationPanel: React.FC<Props> = ({ className = '' }) => {
  const [ncInfo, setNcInfo] = useState<NoiseCancellationInfo>({
    active_filter: 'Passthrough',
    filter_type: 'passthrough',
    description: 'Passthrough mode - raw audio without noise suppression processing.',
    stats: { frames_processed: 0, last_rms: 0, last_db: -100 },
  });

  const [eslStatus, setEslStatus] = useState<FreeSwitchStatus | null>(null);
  const [isChangingFilter, setIsChangingFilter] = useState(false);
  const [customCmd, setCustomCmd] = useState('');
  const [customArgs, setCustomArgs] = useState('');
  const [commandOutput, setCommandOutput] = useState<string | null>(null);
  const [isExecutingEsl, setIsExecutingEsl] = useState(false);

  // Available filter options requested by user
  const filters = [
    { name: 'Passthrough', type: 'passthrough', badge: 'Raw Audio', desc: 'No noise suppression' },
    { name: 'WebRTC APM', type: 'webrtc', badge: 'APM DSP', desc: 'High-pass filter & adaptive noise suppression' },
    { name: 'RNNoise', type: 'rnnoise', badge: 'RNN Model', desc: 'Recurrent Neural Network speech noise filter' },
    { name: 'DeepFilterNet', type: 'deepfilternet', badge: 'Deep AI', desc: 'Fullband deep neural network enhancement' },
  ];

  const fetchStatus = async () => {
    try {
      const nc = await voiceService.getNoiseCancellationStatus();
      setNcInfo(nc);
      const esl = await voiceService.getFreeSwitchStatus();
      setEslStatus(esl);
    } catch (e) {
      console.warn('[NC-PANEL] Error fetching status:', e);
    }
  };

  useEffect(() => {
    fetchStatus();

    // Poll status every 3 seconds for audio loop stats
    const interval = setInterval(fetchStatus, 3000);

    // Real-time DataChannel listener
    voiceService.onNoiseCancellationUpdate = (info) => {
      setNcInfo(info);
    };

    return () => clearInterval(interval);
  }, []);

  const handleSelectFilter = async (filterName: string) => {
    setIsChangingFilter(true);
    try {
      const updated = await voiceService.selectNoiseCancellation(filterName);
      setNcInfo(updated);
      await fetchStatus();
    } catch (err) {
      console.error('[NC-PANEL] Filter switch failed:', err);
    } finally {
      setIsChangingFilter(false);
    }
  };

  const handleExecuteEsl = async (cmd: string, args: string) => {
    setIsExecutingEsl(true);
    setCommandOutput(null);
    try {
      const res = await voiceService.executeFreeSwitchESL(cmd, args);
      setCommandOutput(`[${res.command}] -> ${res.body}`);
      await fetchStatus();
    } catch (err: any) {
      setCommandOutput(`[ERROR] ${err.message || 'ESL command execution failed'}`);
    } finally {
      setIsExecutingEsl(false);
    }
  };

  return (
    <div className={`mt-6 space-y-6 ${className}`}>
      {/* 1. CURRENTLY RUNNING NOISE CANCELLATION BADGE CARD */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Cpu className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Currently Running Noise Cancellation
              </div>
              <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                <span>{ncInfo.active_filter}</span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Active
                </span>
              </h2>
            </div>
          </div>
          <button
            onClick={fetchStatus}
            title="Refresh Status"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 mt-3 leading-relaxed">
          {ncInfo.description}
        </p>

        {/* Audio Loop Logging Statistics */}
        <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-800/80">
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Audio Loop Frames</div>
            <div className="text-sm font-bold text-indigo-300 mt-0.5">
              {ncInfo.stats?.frames_processed ?? 0} frames
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Signal Level (dB)</div>
            <div className="text-sm font-bold text-emerald-400 mt-0.5">
              {ncInfo.stats?.last_db ?? -100} dB
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">RMS Level</div>
            <div className="text-sm font-bold text-cyan-300 mt-0.5">
              {ncInfo.stats?.last_rms ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* 2. NOISE CANCELLATION SELECTOR BUTTONS */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md">
        <div className="flex items-center space-x-2 text-slate-200 text-sm font-semibold mb-3">
          <Sliders className="w-4 h-4 text-emerald-400" />
          <span>Switch Noise Cancellation Algorithm</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {filters.map((f) => {
            const isActive = ncInfo.active_filter.toLowerCase() === f.name.toLowerCase();
            return (
              <button
                key={f.name}
                onClick={() => handleSelectFilter(f.name)}
                disabled={isChangingFilter}
                className={`flex flex-col justify-between p-3 rounded-xl border text-left transition-all duration-200 ${
                  isActive
                    ? 'bg-emerald-500/10 border-emerald-500/50 text-white shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-500/30'
                    : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold">{f.name}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                        isActive ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {f.badge}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 line-clamp-2 leading-tight">
                    {f.desc}
                  </p>
                </div>
                {isActive && (
                  <div className="mt-2 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    Running Live
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. FREESWITCH ESL TOOLCALL CONTROL PANEL */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <Terminal className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-bold text-white">FreeSWITCH ESL ToolCall Console</h3>
              <p className="text-[11px] text-slate-400">Execute FreeSWITCH socket commands & telephony toolcalls</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                eslStatus?.esl_connected
                  ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              <Radio className="w-3 h-3 mr-1 animate-pulse" />
              {eslStatus?.esl_connected ? 'ESL Socket Connected' : 'ESL Offline'}
            </span>
          </div>
        </div>

        {/* Quick Toolcall Action Buttons */}
        <div className="mt-4">
          <div className="text-[11px] font-medium text-slate-400 mb-2">Quick Toolcall Commands:</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button
              onClick={() => handleExecuteEsl('uuid_transfer', 'channel-webcall-01 support_queue')}
              disabled={isExecutingEsl}
              className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-xs font-semibold hover:bg-indigo-600/30 transition-colors"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>Call Transfer</span>
            </button>

            <button
              onClick={() => handleExecuteEsl('noise_cancel', 'DeepFilterNet')}
              disabled={isExecutingEsl}
              className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-emerald-600/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-600/30 transition-colors"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>DeepFilterNet</span>
            </button>

            <button
              onClick={() => handleExecuteEsl('noise_cancel', 'WebRTC APM')}
              disabled={isExecutingEsl}
              className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-300 text-xs font-semibold hover:bg-cyan-600/30 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>WebRTC APM</span>
            </button>

            <button
              onClick={() => handleExecuteEsl('status', '')}
              disabled={isExecutingEsl}
              className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>ESL Status</span>
            </button>
          </div>
        </div>

        {/* Custom ESL Command Input */}
        <div className="mt-4 pt-4 border-t border-slate-800">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (customCmd.trim()) {
                handleExecuteEsl(customCmd, customArgs);
              }
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={customCmd}
              onChange={(e) => setCustomCmd(e.target.value)}
              placeholder="ESL Command (e.g. uuid_setvar)"
              className="w-1/3 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <input
              type="text"
              value={customArgs}
              onChange={(e) => setCustomArgs(e.target.value)}
              placeholder="Args (e.g. channel-webcall-01 noise_cancellation_filter RNNoise)"
              className="flex-1 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <button
              type="submit"
              disabled={isExecutingEsl || !customCmd.trim()}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
            >
              <Send className="w-3 h-3" />
              <span>Run</span>
            </button>
          </form>

          {/* Command execution output console log */}
          {commandOutput && (
            <div className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-cyan-300 overflow-x-auto whitespace-pre-wrap">
              {commandOutput}
            </div>
          )}

          {/* Recent ESL Command History */}
          {eslStatus?.recent_commands && eslStatus.recent_commands.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Recent ESL Execution Log:</div>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {eslStatus.recent_commands.slice(-3).map((cmd, i) => (
                  <div key={i} className="flex items-center justify-between text-[11px] text-slate-400 font-mono bg-slate-950/50 px-2.5 py-1 rounded border border-slate-800/40">
                    <span>[{cmd.timestamp}] {cmd.command}</span>
                    <span className="text-emerald-400 text-[10px]">{cmd.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
