import { useEffect, useState } from 'react';
import { getReviewQueue, resolveReviewItem, getCategories } from '../api';
import { HelpCircle, AlertCircle, SearchX } from 'lucide-react';
import { CustomFace } from '../components/CustomFaces';

export default function Review() {
  const [groups, setGroups] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getReviewQueue(), getCategories()])
      .then(([gData, cData]) => {
        setGroups(gData);
        setCategories(cData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleResolve = async (itemId: number, catId: number, scope: string) => {
    try {
      await resolveReviewItem(itemId, { category_id: catId }, scope);
      // Optimistically remove the item/group
      const newGroups = groups.map(g => ({
        ...g,
        items: g.items.filter((i: any) => i.id !== itemId)
      })).filter(g => g.items.length > 0);
      setGroups(newGroups);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="text-center mt-8">Loading review queue...</div>;

  if (groups.length === 0) {
    return (
      <div className="flex-col items-center justify-center gap-4 mt-16 text-center">
        <div style={{ padding: '2rem', background: 'var(--success-bg)', borderRadius: '50%', color: 'var(--success)' }}>
          <CheckSquare size={48} />
        </div>
        <h2>All caught up!</h2>
        <p>No transactions require your review right now.</p>
      </div>
    );
  }

  return (
    <div className="flex-col gap-8">
      <div>
        <h1>Review Inbox</h1>
        <p>Help the system learn by categorising unknowns and resolving mismatches.</p>
      </div>

      <div className="flex-col gap-6">
        {groups.map(group => (
          <div key={group.payee} className="glass-panel" style={{ padding: '2rem' }}>
            <div className="flex justify-between items-center mb-6">
              <h2 className="flex items-center gap-3">
                {group.kind === 'unknown_payee' ? <HelpCircle className="text-warning" /> : 
                 group.kind === 'low_conf' ? <AlertCircle className="text-warning" /> : 
                 <SearchX className="text-danger" />}
                {group.payee}
                <span className="badge" style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>
                  {group.items.length} items
                </span>
              </h2>
            </div>
            
            {group.items.map((item: any) => (
              <div key={item.id} className="glass-card mb-4">
                <p className="font-medium text-lg mb-4">{item.question}</p>
                
                {item.txn && (
                  <div className="flex gap-4 mb-4 text-sm text-secondary">
                    <span>{item.txn.txn_date}</span>
                    <span>₹{item.txn.amount}</span>
                    {item.txn.raw_narration && (
                      <span style={{ maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.txn.raw_narration}
                      </span>
                    )}
                  </div>
                )}
                
                <div className="flex gap-4 items-center">
                  <div className="flex items-center gap-2">
                    <CustomFace name="face-unknown" className="text-secondary" />
                    <select 
                      className="input" style={{ width: '250px' }}
                      defaultValue=""
                      onChange={(e) => {
                        if(e.target.value) handleResolve(item.id, parseInt(e.target.value), 'all_past_and_future');
                      }}
                    >
                      <option value="" disabled>Select Category...</option>
                      {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <span className="text-sm text-tertiary">Select to create a permanent rule</span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// Ensure the icon is imported for the empty state
import { CheckSquare } from 'lucide-react';
