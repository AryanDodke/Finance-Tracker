import { useState } from 'react';
import { askChat } from '../api';
import { Send, Bot, User, Sparkles } from 'lucide-react';

export default function Chat() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Array<{role: 'user'|'assistant', content: string, data?: any, chartType?: string}>>([
    { role: 'assistant', content: "Hi! I'm your spending analyst. Ask me questions like 'How much did I spend on food last month?' or 'Show me my top merchants for Travel.'" }
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMsg = query;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setQuery('');
    setLoading(true);

    try {
      const res = await askChat(userMsg);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.answer,
        data: res.data,
        chartType: res.chart_type
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-col" style={{ height: 'calc(100vh - 4rem)' }}>
      <div className="mb-6">
        <h1>Ask AI</h1>
        <p>Chat with your financial data using natural language.</p>
      </div>

      <div className="glass-panel flex-col" style={{ flex: 1, overflow: 'hidden' }}>
        {/* Chat History */}
        <div className="p-6 flex-col gap-6" style={{ flex: 1, overflowY: 'auto' }}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className="mt-1" style={{ 
                color: msg.role === 'assistant' ? 'var(--accent-primary)' : 'var(--text-secondary)'
              }}>
                {msg.role === 'assistant' ? <Bot /> : <User />}
              </div>
              
              <div className={`glass-card ${msg.role === 'user' ? 'bg-surface-hover' : ''}`} style={{ maxWidth: '80%' }}>
                <p className={msg.role === 'user' ? 'mb-0 text-primary' : ''}>{msg.content}</p>
                
                {/* Optional Data Viz Rendering here */}
                {msg.data && Array.isArray(msg.data) && msg.data.length > 0 && msg.role === 'assistant' && (
                  <div className="mt-4 table-container">
                     <table className="table" style={{ fontSize: '0.85rem' }}>
                       <tbody>
                         {msg.data.slice(0, 5).map((row: any, i: number) => (
                           <tr key={i}>
                             {Object.values(row).map((val: any, j: number) => (
                               <td key={j}>{typeof val === 'number' ? `₹${val.toFixed(2)}` : String(val)}</td>
                             ))}
                           </tr>
                         ))}
                       </tbody>
                     </table>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-4">
              <div className="mt-1 text-accent-primary"><Sparkles className="animate-pulse" /></div>
              <div className="glass-card"><p className="mb-0 animate-pulse">Analysing data...</p></div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4" style={{ borderTop: '1px solid var(--border-light)' }}>
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input 
              type="text" className="input" style={{ flex: 1 }}
              placeholder="Ask a question about your spending..."
              value={query} onChange={e => setQuery(e.target.value)}
              disabled={loading}
            />
            <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
