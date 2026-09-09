import React, { useState } from 'react';
import { Scan, api } from '../services/api';

interface AgentChatProps {
  selectedScan: Scan | null;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const AgentChat: React.FC<AgentChatProps> = ({ selectedScan }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your smolagents clinical assistant. Ask me about BraTS segmentation results, RANO criteria, or clinical interpretation.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => 'sess_' + Math.random().toString(36).substring(2, 9));

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setLoading(true);

    try {
      const res = await api.sendChatMessage(sessionId, userText, selectedScan?.id);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error communicating with the agent service.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: 'var(--bg-card)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', height: '480px' }}>
      <h2 style={{ fontSize: '1.2rem', marginBottom: '0.75rem', color: 'var(--accent)' }}>smolagents Clinical Chat</h2>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem', paddingRight: '0.5rem' }}>
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              padding: '0.65rem 0.85rem',
              borderRadius: '8px',
              fontSize: '0.9rem',
              lineHeight: '1.4',
              background: m.role === 'user' ? 'var(--accent)' : 'var(--bg-primary)',
              color: m.role === 'user' ? '#0f172a' : 'var(--text-primary)',
              border: m.role === 'assistant' ? '1px solid var(--border)' : 'none',
            }}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            smolagents is reasoning & evaluating tools...
          </div>
        )}
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={selectedScan ? `Ask about Scan #${selectedScan.id}...` : 'Type a clinical query...'}
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={loading} style={{ background: 'var(--accent)', color: '#0f172a', padding: '0.5rem 1rem' }}>
          Send
        </button>
      </form>
    </div>
  );
};
