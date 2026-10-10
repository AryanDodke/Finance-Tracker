import { useEffect, useState } from 'react';
import { getTransactions, getCategories, patchTransaction } from '../api';
import { Filter } from 'lucide-react';
import { CustomFace } from '../components/CustomFaces';

export default function Transactions() {
  const [txns, setTxns] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [period, setPeriod] = useState('');
  const [status, setStatus] = useState('');

  const fetchTxns = () => {
    setLoading(true);
    const params: any = {};
    if (period) {
      params.start_date = `${period}-01`;
      params.end_date = `${period}-31`; // lazy end date
    }
    if (status) params.status = status;
    
    getTransactions(params)
      .then(setTxns)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    getCategories().then(setCategories).catch(console.error);
    fetchTxns();
  }, [period, status]);

  const handleCategoryChange = async (txnId: number, newCatId: number) => {
    try {
      const updated = await patchTransaction(txnId, {
        category_id: newCatId,
        apply_scope: 'this_only'
      });
      setTxns(txns.map(t => t.id === txnId ? updated : t));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h1>Transactions</h1>
          <p>View and edit your underlying bank data.</p>
        </div>
        
        <div className="flex gap-4">
          <div className="flex items-center gap-2 text-secondary">
            <Filter size={18} />
          </div>
          <input 
            type="month" className="input" style={{ width: 'auto' }}
            value={period} onChange={e => setPeriod(e.target.value)} 
          />
          <select 
            className="input" style={{ width: 'auto' }}
            value={status} onChange={e => setStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="auto">Auto-categorised</option>
            <option value="confirmed">Confirmed</option>
            <option value="pending">Pending Review</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        {loading ? (
          <div className="p-8 text-center text-secondary">Loading transactions...</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Narration / Payee</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {txns.map(t => (
                <tr key={t.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{t.txn_date}</td>
                  <td>
                    <div className="font-medium">{t.payee_raw || t.merchant_name || 'Unknown'}</div>
                    <div className="text-xs text-tertiary truncate" style={{ maxWidth: '300px' }}>
                      {t.raw_narration}
                    </div>
                  </td>
                  <td className={t.direction === 'credit' ? 'text-success font-semibold' : 'font-semibold'}>
                    {t.direction === 'credit' ? '+' : '-'}₹{parseFloat(t.amount).toFixed(2)}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <CustomFace 
                        name={categories.find(c => c.id === t.category_id)?.icon || 'face-unknown'} 
                        className="text-secondary" 
                      />
                      <select 
                        className="input" style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                        value={t.category_id || ''}
                        onChange={(e) => handleCategoryChange(t.id, parseInt(e.target.value))}
                      >
                        <option value="" disabled>Select...</option>
                        {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ 
                      background: t.status === 'confirmed' ? 'var(--success-bg)' : 
                                 t.status === 'auto' ? 'rgba(99, 102, 241, 0.2)' : 'var(--warning-bg)',
                      color: t.status === 'confirmed' ? 'var(--success)' : 
                             t.status === 'auto' ? '#a5b4fc' : 'var(--warning)'
                    }}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
              {txns.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center p-8 text-secondary">No transactions found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
