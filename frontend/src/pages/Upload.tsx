import { useState } from 'react';
import { uploadStatement, uploadNotes } from '../api';
import { UploadCloud, CheckCircle, AlertCircle } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [period, setPeriod] = useState('2025-06');
  
  const [notes, setNotes] = useState('');
  const [notesPeriod, setNotesPeriod] = useState('2025-06');
  
  const [status, setStatus] = useState<{type: 'idle'|'loading'|'success'|'error', message: string}>({type: 'idle', message: ''});

  const handlePdfUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !password || !period) return;
    
    setStatus({type: 'loading', message: 'Ingesting statement...'});
    try {
      const res = await uploadStatement(file, password, period);
      setStatus({type: 'success', message: res.message});
      setFile(null);
      setPassword('');
    } catch (err: any) {
      setStatus({type: 'error', message: err.message});
    }
  };

  const handleNotesUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes || !notesPeriod) return;
    
    setStatus({type: 'loading', message: 'Parsing notes...'});
    try {
      const res = await uploadNotes(notes, notesPeriod);
      setStatus({type: 'success', message: res.message});
      setNotes('');
    } catch (err: any) {
      setStatus({type: 'error', message: err.message});
    }
  };

  return (
    <div className="flex-col gap-8">
      <div>
        <h1>Upload Data</h1>
        <p>Ingest your SBI UPI bank statements and Apple Notes spending breakdown.</p>
      </div>

      {status.type !== 'idle' && (
        <div className={`glass-card flex items-center gap-3 ${
          status.type === 'success' ? 'text-success' : 
          status.type === 'error' ? 'text-danger' : 'text-warning'
        }`}>
          {status.type === 'success' ? <CheckCircle /> : <AlertCircle />}
          <span>{status.message}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        {/* PDF Upload */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Bank Statement PDF</h3>
          <p>Upload your password-protected SBI PDF statement.</p>
          
          <form onSubmit={handlePdfUpload} className="flex-col gap-4 mt-4">
            <div className="upload-zone" onClick={() => document.getElementById('pdf-input')?.click()}>
              <UploadCloud size={40} className="text-gradient mx-auto mb-2" />
              {file ? <p className="text-success">{file.name}</p> : <p>Click to select PDF</p>}
              <input 
                id="pdf-input" type="file" accept=".pdf" 
                style={{ display: 'none' }}
                onChange={e => setFile(e.target.files?.[0] || null)}
              />
            </div>
            
            <input 
              className="input" type="password" placeholder="PDF Password" 
              value={password} onChange={e => setPassword(e.target.value)} required 
            />
            
            <input 
              className="input" type="month" 
              value={period} onChange={e => setPeriod(e.target.value)} required 
            />
            
            <button type="submit" className="btn btn-primary" disabled={status.type === 'loading'}>
              Ingest Statement
            </button>
          </form>
        </div>

        {/* Notes Upload */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Apple Notes Breakdown</h3>
          <p>Paste your month's spending notes.</p>
          
          <form onSubmit={handleNotesUpload} className="flex-col gap-4 mt-4">
            <textarea 
              className="input" placeholder="Paste notes here..." rows={6}
              value={notes} onChange={e => setNotes(e.target.value)} required
              style={{ resize: 'none' }}
            />
            
            <input 
              className="input" type="month" 
              value={notesPeriod} onChange={e => setNotesPeriod(e.target.value)} required 
            />
            
            <button type="submit" className="btn btn-primary" disabled={status.type === 'loading'}>
              Parse Notes
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
