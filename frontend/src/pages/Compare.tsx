import { useEffect, useState } from 'react';
import { getReconcile } from '../api';
import { FileWarning, CheckCircle2, XCircle } from 'lucide-react';

export default function Compare() {
  const [period, setPeriod] = useState('2025-06');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getReconcile(period)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h1>Notes vs Bank</h1>
          <p>Reconciliation report for {period}.</p>
        </div>
        <input 
          type="month" className="input" style={{ width: 'auto' }}
          value={period} onChange={e => setPeriod(e.target.value)} 
        />
      </div>

      {loading ? (
        <div className="text-center mt-8">Running reconciliation...</div>
      ) : !data ? (
        <div className="text-center mt-8 text-danger">Failed to load report.</div>
      ) : (
        <>
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <h3 className="flex items-center gap-2 text-warning mb-6">
              <FileWarning size={24} /> 
              Category Gaps
            </h3>
            
            {data.category_gaps.length === 0 ? (
              <p className="text-success">No significant gaps found between notes and bank.</p>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Notes Total</th>
                      <th>Bank Total</th>
                      <th>Gap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.category_gaps.map((g: any, i: number) => (
                      <tr key={i}>
                        <td className="font-medium">{g.category_name}</td>
                        <td>₹{g.noted_total.toFixed(2)}</td>
                        <td>₹{g.bank_total.toFixed(2)}</td>
                        <td className="text-danger font-semibold">
                          ₹{g.gap.toFixed(2)} ({(g.gap_pct * 100).toFixed(1)}%)
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-8">
            <div className="glass-panel" style={{ padding: '2rem' }}>
              <h3 className="flex items-center gap-2 mb-6 text-success">
                <CheckCircle2 size={20} /> Matched Lines
              </h3>
              <div className="flex-col gap-4">
                {data.matched.map((m: any, i: number) => (
                  <div key={i} className="flex justify-between items-center pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <div>
                      <div className="font-medium">{m.note_item}</div>
                      <div className="text-sm text-secondary">Bank: {m.merchant_name || 'Unknown'} on {m.txn_date}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-success">₹{m.note_amount.toFixed(2)}</div>
                      <div className="text-xs text-tertiary">Match: {(m.match_score * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                ))}
                {data.matched.length === 0 && <p className="text-secondary">No matched lines.</p>}
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '2rem' }}>
              <h3 className="flex items-center gap-2 mb-6 text-danger">
                <XCircle size={20} /> Unmatched Notes
              </h3>
              <div className="flex-col gap-4">
                {data.unmatched_notes.map((m: any, i: number) => (
                  <div key={i} className="flex justify-between items-center pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <div className="font-medium">{m.note_item}</div>
                    <div className="font-semibold text-danger">₹{m.note_amount.toFixed(2)}</div>
                  </div>
                ))}
                {data.unmatched_notes.length === 0 && <p className="text-success">All note lines were matched to bank transactions!</p>}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
