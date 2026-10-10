import { useEffect, useState } from 'react';
import { getBudgets, getCategories, upsertBudget } from '../api';
import { Save, Plus } from 'lucide-react';

export default function Settings() {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // New budget form
  const [catId, setCatId] = useState('');
  const [amount, setAmount] = useState('');
  const [period, setPeriod] = useState('2025-06');

  useEffect(() => {
    Promise.all([getBudgets(), getCategories()])
      .then(([bData, cData]) => {
        setBudgets(bData);
        setCategories(cData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSaveBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catId || !amount || !period) return;

    try {
      const b = await upsertBudget({
        category_id: parseInt(catId),
        monthly_amount: parseFloat(amount),
        effective_from: period
      });
      // Replace or append
      const existing = budgets.findIndex(x => x.category_id === b.category_id && x.effective_from === b.effective_from);
      if (existing >= 0) {
        const copy = [...budgets];
        copy[existing] = b;
        setBudgets(copy);
      } else {
        setBudgets([...budgets, b]);
      }
      setAmount('');
      setCatId('');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-col gap-8">
      <div>
        <h1>Settings</h1>
        <p>Manage categories, budgets, and system preferences.</p>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Monthly Budgets</h3>
          <p>Set spending targets per category.</p>

          <form onSubmit={handleSaveBudget} className="flex gap-3 mt-4 mb-6">
            <select className="input" value={catId} onChange={e => setCatId(e.target.value)} required>
              <option value="" disabled>Category...</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input 
              type="number" className="input" placeholder="₹ Amount" style={{ width: '120px' }}
              value={amount} onChange={e => setAmount(e.target.value)} required 
            />
            <input 
              type="month" className="input" style={{ width: '150px' }}
              value={period} onChange={e => setPeriod(e.target.value)} required 
            />
            <button type="submit" className="btn btn-primary"><Plus size={18} /></button>
          </form>

          {loading ? <p>Loading budgets...</p> : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Effective From</th>
                  </tr>
                </thead>
                <tbody>
                  {budgets.map((b, i) => (
                    <tr key={i}>
                      <td>{b.category_name}</td>
                      <td className="font-semibold">₹{parseFloat(b.monthly_amount).toFixed(2)}</td>
                      <td className="text-secondary">{b.effective_from}</td>
                    </tr>
                  ))}
                  {budgets.length === 0 && (
                    <tr><td colSpan={3} className="text-secondary text-center p-4">No budgets set.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Categories</h3>
          <p>System and user categories.</p>
          <div className="flex-col gap-2 mt-4" style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {categories.map(c => (
              <div key={c.id} className="glass-card flex justify-between" style={{ padding: '1rem' }}>
                <span className="font-medium">{c.name}</span>
                <span className="text-sm text-tertiary">ID: {c.id} {c.parent_id ? `• Parent: ${c.parent_id}` : ''}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
