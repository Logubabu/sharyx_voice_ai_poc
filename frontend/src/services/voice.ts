/**
 * Voice AI WebCall Service
 * Handles API calls to backend, microphone access, and WebRTC call state management.
 */

export type CallState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'ending'
  | 'disconnected'
  | 'error';

export interface TranscriptItem {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export class VoiceCallService {
  private sessionId: string | null = null;
  private mediaStream: MediaStream | null = null;
  private peerConnection: RTCPeerConnection | null = null;

  /**
   * Requests browser microphone permission.
   */
  async requestMicrophone(): Promise<MediaStream> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      this.mediaStream = stream;
      return stream;
    } catch (error) {
      console.error('Microphone access error:', error);
      throw new Error('Unable to access microphone. Please allow microphone access and try again.');
    }
  }

  /**
   * Connects local browser WebRTC peer connection with backend via SDP offer/answer.
   */
  async connectWebRTC(sessionId: string): Promise<void> {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    this.peerConnection = pc;

    // Attach local microphone audio track to peer connection
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((track) => {
        pc.addTrack(track, this.mediaStream!);
      });
    }

    // Play incoming audio stream from Voice AI Assistant
    pc.ontrack = (event) => {
      const remoteAudio = new Audio();
      remoteAudio.srcObject = event.streams[0];
      remoteAudio.play().catch((err) => console.warn('Remote audio playback warning:', err));
    };

    // Create WebRTC SDP offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    // Send SDP offer to backend WebRTC offer endpoint
    const response = await fetch(`${BACKEND_URL}/api/webrtc/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('WebRTC SDP negotiation error:', errorText);
      throw new Error(`WebRTC SDP negotiation failed (${response.status})`);
    }

    const answer = await response.json();
    await pc.setRemoteDescription(new RTCSessionDescription({
      type: answer.type,
      sdp: answer.sdp,
    }));
  }

  /**
   * Starts a new WebCall session with backend and connects WebRTC audio stream.
   */
  async startCall(sessionId?: string): Promise<{ sessionId: string; roomUrl: string; token?: string }> {
    const generatedSessionId = sessionId || `session_${crypto.randomUUID().slice(0, 8)}`;

    try {
      // 1. Request microphone and start backend session concurrently
      const micPromise = this.requestMicrophone();
      const apiPromise = fetch(`${BACKEND_URL}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: generatedSessionId }),
      });

      const [, response] = await Promise.all([micPromise, apiPromise]);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend start call error:', response.status, errorText);
        throw new Error(`Backend service error (${response.status}): ${errorText || response.statusText}`);
      }

      const data = await response.json();
      this.sessionId = data.session_id;

      // 2. Establish real-time WebRTC audio connection with backend
      try {
        await this.connectWebRTC(this.sessionId!);
      } catch (webrtcErr) {
        console.warn('WebRTC peer connection notice (running in session mode):', webrtcErr);
      }

      return {
        sessionId: data.session_id,
        roomUrl: data.room_url,
        token: data.token,
      };
    } catch (err: any) {
      console.error('startCall exception:', err);
      throw err;
    }
  }

  /**
   * Ends current call session and cleans up microphone and peer connections.
   */
  async endCall(): Promise<void> {
    if (this.sessionId) {
      try {
        await fetch(`${BACKEND_URL}/api/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.sessionId }),
        });
      } catch (err) {
        console.warn('Error sending stop request to backend:', err);
      }
    }

    // Stop microphone tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Close peer connection if open
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    this.sessionId = null;
  }

  getSessionId(): string | null {
    return this.sessionId;
  }
}

export const voiceService = new VoiceCallService();
