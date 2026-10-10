import { useEffect, useState } from 'react';
import { getSummary } from '../api';
import { TrendingUp, AlertTriangle, RefreshCw, Wallet, ClipboardList } from 'lucide-react';
import { CustomFace } from '../components/CustomFaces';
import { 
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, LineChart, Line 
} from 'recharts';

const COLORS = ['#6366f1', '#a855f7', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#3b82f6'];

const CustomPieTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="glass-panel" style={{ padding: '0.75rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        <div className="flex items-center gap-2 font-medium">
          <CustomFace name={data.category_icon || 'face-unknown'} className="w-4 h-4 text-accent-primary" />
          {data.category_name}
        </div>
        <div className="text-lg font-bold">₹{data.total.toFixed(2)}</div>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const [period, setPeriod] = useState('2025-06');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSummary(period)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <div className="text-center mt-8">Loading dashboard...</div>;
  if (!data) return <div className="text-center mt-8">Failed to load data.</div>;

  const totalSpend = data.category_totals.reduce((sum: number, cat: any) => sum + cat.total, 0);

  return (
    <div className="flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h1>Dashboard</h1>
          <p>Your spending insights for {period}.</p>
        </div>
        <input 
          type="month" className="input" style={{ width: 'auto' }}
          value={period} onChange={e => setPeriod(e.target.value)} 
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="glass-card flex-col gap-2 transition-transform hover:-translate-y-1 hover:shadow-lg hover:shadow-indigo-500/10 cursor-default">
          <h3 className="flex items-center gap-2 text-secondary text-sm uppercase tracking-wider">
            <Wallet size={16} /> Total Spend
          </h3>
          <h2>₹{totalSpend.toFixed(2)}</h2>
          {data.savings_rate !== null && (
            <p className="text-success text-sm">Savings rate: {data.savings_rate.toFixed(1)}%</p>
          )}
        </div>
        
        <div className="glass-card flex-col gap-2 transition-transform hover:-translate-y-1 hover:shadow-lg hover:shadow-indigo-500/10 cursor-default">
          <h3 className="flex items-center gap-2 text-secondary text-sm uppercase tracking-wider">
            <TrendingUp size={16} /> Top Category
          </h3>
          <h2 className="flex items-center">
            {data.category_totals[0]?.category_icon && (
              <CustomFace name={data.category_totals[0].category_icon} className="mr-2 w-8 h-8 text-accent-primary" />
            )}
            {data.category_totals[0]?.category_name || '-'}
          </h2>
          <p className="text-sm">₹{data.category_totals[0]?.total.toFixed(2) || '0.00'}</p>
        </div>

        <div className="glass-card flex-col gap-2 transition-transform hover:-translate-y-1 hover:shadow-lg hover:shadow-indigo-500/10 cursor-default">
          <h3 className="flex items-center gap-2 text-secondary text-sm uppercase tracking-wider">
            <ClipboardList size={16} /> Pending Reviews
          </h3>
          <h2>{data.review_count}</h2>
          <p className="text-sm">Action required to improve accuracy</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Category Breakdown</h3>
          <div style={{ height: '300px', marginTop: '1rem' }} className="flex items-center justify-center">
            {data.category_totals.length === 0 ? (
              <p className="text-secondary">No spending data for this period.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.category_totals}
                    dataKey="total"
                    nameKey="category_name"
                    cx="50%" cy="50%"
                    outerRadius={100} innerRadius={60}
                    stroke="none"
                  >
                    {data.category_totals.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomPieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Top Merchants</h3>
          <div style={{ height: '300px', marginTop: '1rem' }} className="flex items-center justify-center">
            {data.top_merchants.length === 0 ? (
              <p className="text-secondary">No merchants found for this period.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.top_merchants.slice(0, 5)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="merchant_name" type="category" width={100} axisLine={false} tickLine={false} tick={{fill: 'rgba(255,255,255,0.6)'}} />
                  <Tooltip 
                    formatter={(value: number) => `₹${value.toFixed(2)}`}
                    contentStyle={{ background: '#0f1115', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="total" fill="url(#colorGradient)" radius={[0, 4, 4, 0]} barSize={20} />
                  <defs>
                    <linearGradient id="colorGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#6366f1" />
                      <stop offset="100%" stopColor="#a855f7" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3 className="flex items-center gap-2"><RefreshCw size={20} className="text-accent-primary" /> Recurring Charges</h3>
          <div className="flex-col gap-4 mt-4">
            {data.recurring.length === 0 ? <p>No recurring charges detected.</p> : null}
            {data.recurring.map((r: any) => (
              <div key={r.merchant_id} className="flex justify-between items-center pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <div>
                  <div className="font-medium">{r.merchant_name}</div>
                  <div className="text-sm text-secondary">Every ~{r.frequency_days} days (Last: {r.last_date})</div>
                </div>
                <div className="font-semibold">₹{r.typical_amount.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3 className="flex items-center gap-2"><AlertTriangle size={20} className="text-warning" /> Anomalies</h3>
          <div className="flex-col gap-4 mt-4">
            {data.anomalies.length === 0 ? <p>No unusual spending detected.</p> : null}
            {data.anomalies.map((a: any) => (
              <div key={a.txn_id} className="flex justify-between items-center pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <div>
                  <div className="font-medium">{a.merchant_name}</div>
                  <div className="text-sm text-secondary flex items-center">
                    {a.txn_date} &bull; 
                    <span className="flex items-center ml-2">
                      <CustomFace name={a.category_icon || 'face-unknown'} className="w-3 h-3 mr-1" />
                      {a.category_name}
                    </span>
                  </div>
                </div>
                <div className="font-semibold text-warning">₹{a.amount.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
