import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { LayoutDashboard, FileText, CheckSquare, BarChart2, MessageSquare, Settings as SettingsIcon } from 'lucide-react';
import { useEffect, useState } from 'react';

// Pages
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Review from './pages/Review';
import Compare from './pages/Compare';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Transactions from './pages/Transactions';

import { getReviewCounts } from './api';

function Sidebar() {
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    getReviewCounts().then(data => {
      setReviewCount(data.total || 0);
    }).catch(console.error);
  }, []);

  const navItems = [
    { to: "/dashboard", icon: <LayoutDashboard size={20} />, label: "Dashboard" },
    { to: "/review", icon: <CheckSquare size={20} />, label: "Review Inbox", badge: reviewCount },
    { to: "/compare", icon: <BarChart2 size={20} />, label: "Notes vs Bank" },
    { to: "/transactions", icon: <FileText size={20} />, label: "Transactions" },
    { to: "/chat", icon: <MessageSquare size={20} />, label: "Ask AI" },
    { to: "/upload", icon: <FileText size={20} />, label: "Upload Data" },
    { to: "/settings", icon: <SettingsIcon size={20} />, label: "Settings" },
  ];

  return (
    <aside className="sidebar">
      <div>
        <h2 className="text-gradient" style={{ marginBottom: '2rem' }}>Spend Analyser</h2>
      </div>
      <nav className="nav-links flex-col">
        {navItems.map((item) => (
          <NavLink 
            key={item.to} 
            to={item.to} 
            className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {item.icon}
            <span style={{ flex: 1 }}>{item.label}</span>
            {item.badge ? <span className="badge">{item.badge}</span> : null}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content animate-fade-in">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/review" element={<Review />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
