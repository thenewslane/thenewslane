'use client';

/**
 * The News Lane — Studio CMS
 * Subdomain: studio.thenewslane.com
 *
 * Full CMS connected to Supabase.
 * Tables used: trending_topics, categories, runs_log
 *
 * Required env vars in apps/studio/.env.local:
 *   NEXT_PUBLIC_SUPABASE_URL=https://tzkdsiqqbkpqxwvatlaw.supabase.co
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
 */

import { useState, useEffect, useCallback } from 'react';
import { createBrowserClient }              from '@supabase/ssr';

// ─── SUPABASE CLIENT ──────────────────────────────────────────────────────────
// Uses @supabase/ssr so the session is stored in cookies, which the
// middleware can read to keep the user authenticated across requests.
function getSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}

// ─── TYPES ────────────────────────────────────────────────────────────────────
type Topic = {
  id: string;
  title: string;
  slug: string;
  category_id: number | null;
  summary: string | null;
  article: string | null;
  status: string;
  viral_score: number | null;
  viral_tier: number | null;
  thumbnail_url: string | null;
  video_url: string | null;
  batch_id: string | null;
  created_at: string;
  published_at: string | null;
};

type Category = {
  id: number;
  name: string;
};

type RunLog = {
  id: string;
  batch_id: string;
  status: string;
  topics_collected: number | null;
  topics_published: number | null;
  errors: number | null;
  duration_seconds: number | null;
  created_at: string;
};

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const CATEGORY_MAP: Record<number, string> = {
  1: 'Technology',      2: 'Entertainment',   3: 'Sports',
  4: 'Politics',        5: 'Business & Finance', 6: 'Health & Science',
  7: 'Lifestyle',       8: 'World News',       9: 'Culture & Arts',
  10: 'Environment',
};

const API_INTEGRATIONS = [
  { id: 1,  name: 'Sora',             provider: 'OpenAI',           type: 'Video Generation',  icon: '🎬', envKey: 'SORA_API_KEY' },
  { id: 2,  name: 'Veo',              provider: 'Google DeepMind',  type: 'Video Generation',  icon: '🎥', envKey: 'VEO_API_KEY' },
  { id: 3,  name: 'Vizard',           provider: 'Vizard.ai',        type: 'Video Editing',     icon: '✂️', envKey: 'VIZARD_API_KEY' },
  { id: 4,  name: 'Anthropic',        provider: 'Anthropic',        type: 'Content Generation',icon: '🤖', envKey: 'ANTHROPIC_API_KEY' },
  { id: 5,  name: 'NewsAPI',          provider: 'NewsAPI.org',      type: 'News Collection',   icon: '📰', envKey: 'NEWSAPI_KEY' },
  { id: 6,  name: 'Unsplash',         provider: 'Unsplash',         type: 'Images',            icon: '🖼️', envKey: 'UNSPLASH_ACCESS_KEY' },
  { id: 7,  name: 'Pexels',           provider: 'Pexels',           type: 'Images',            icon: '📸', envKey: 'PEXELS_API_KEY' },
  { id: 8,  name: 'YouTube Data API', provider: 'Google',           type: 'Video Source',      icon: '▶️', envKey: 'YOUTUBE_API_KEY' },
  { id: 9,  name: 'Groq',             provider: 'Groq',             type: 'LLM',               icon: '⚡', envKey: 'GROQ_API_KEY' },
  { id: 10, name: 'Replicate',        provider: 'Replicate',        type: 'Image Generation',  icon: '🎨', envKey: 'REPLICATE_API_KEY' },
];

const ROLES = [
  { id: 1, name: 'Super Admin',  permissions: ['all'],                            color: '#ff4444' },
  { id: 2, name: 'Editor',       permissions: ['create', 'edit', 'publish', 'delete'], color: '#ff8800' },
  { id: 3, name: 'Contributor',  permissions: ['create', 'edit'],                 color: '#00aaff' },
  { id: 4, name: 'Viewer',       permissions: ['view'],                            color: '#888' },
];

// ─── STYLES ───────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0a0a0f;--surface:#111118;--surface2:#1a1a24;--surface3:#22222f;
    --border:#2a2a38;--accent:#e8c547;--accent2:#7c6af7;
    --text:#f0f0f8;--text2:#9090a8;--text3:#606078;
    --red:#ff4466;--green:#44dd88;--orange:#ff8833;--blue:#44aaff;
  }
  body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text)}
  .cms{display:flex;height:100vh;overflow:hidden}
  .sidebar{width:220px;min-width:220px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto}
  .sidebar-logo{padding:20px 20px 16px;border-bottom:1px solid var(--border)}
  .logo-mark{font-family:'DM Serif Display',serif;font-size:18px;color:var(--accent);letter-spacing:-.5px}
  .logo-sub{font-size:10px;color:var(--text3);letter-spacing:2px;text-transform:uppercase;margin-top:2px}
  .nav-section{padding:12px 0}
  .nav-label{font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:2px;padding:0 20px 8px}
  .nav-item{display:flex;align-items:center;gap:10px;padding:9px 20px;cursor:pointer;font-size:13px;color:var(--text2);transition:all .15s;position:relative}
  .nav-item:hover{color:var(--text);background:var(--surface2)}
  .nav-item.active{color:var(--accent);background:rgba(232,197,71,.08)}
  .nav-item.active::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent);border-radius:0 2px 2px 0}
  .nav-icon{width:16px;text-align:center;font-size:14px}
  .nav-badge{margin-left:auto;background:var(--accent2);color:#fff;font-size:10px;padding:1px 6px;border-radius:10px;font-weight:600}
  .nav-badge.red{background:var(--red)}
  .sidebar-footer{margin-top:auto;padding:16px 20px;border-top:1px solid var(--border)}
  .user-mini{display:flex;align-items:center;gap:10px}
  .avatar-sm{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,var(--accent2),var(--accent));display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0}
  .user-name-sm{font-size:12px;font-weight:500}
  .user-role-sm{font-size:10px;color:var(--text3)}
  .main{flex:1;display:flex;flex-direction:column;overflow:hidden}
  .topbar{height:56px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:16px;flex-shrink:0}
  .topbar-title{font-family:'DM Serif Display',serif;font-size:20px}
  .topbar-sub{font-size:12px;color:var(--text3)}
  .topbar-actions{margin-left:auto;display:flex;gap:10px;align-items:center}
  .content{flex:1;overflow-y:auto;padding:24px}
  .btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;border:none;font-family:'DM Sans',sans-serif;transition:all .15s}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .btn-primary{background:var(--accent);color:#0a0a0f}
  .btn-primary:hover:not(:disabled){background:#f0ce55}
  .btn-secondary{background:var(--surface3);color:var(--text);border:1px solid var(--border)}
  .btn-secondary:hover:not(:disabled){background:var(--surface2)}
  .btn-danger{background:rgba(255,68,102,.15);color:var(--red);border:1px solid rgba(255,68,102,.3)}
  .btn-danger:hover:not(:disabled){background:rgba(255,68,102,.25)}
  .btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}
  .btn-ghost:hover:not(:disabled){background:var(--surface2);color:var(--text)}
  .btn-sm{padding:5px 12px;font-size:12px}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px}
  .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
  .stat-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 20px}
  .stat-label{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1px}
  .stat-value{font-size:28px;font-weight:600;margin:6px 0 4px;font-family:'DM Serif Display',serif}
  .stat-change{font-size:12px;color:var(--green)}
  .table-wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{text-align:left;padding:10px 14px;color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:500;border-bottom:1px solid var(--border)}
  td{padding:12px 14px;border-bottom:1px solid rgba(42,42,56,.5);vertical-align:middle}
  tr:hover td{background:rgba(255,255,255,.02)}
  tr:last-child td{border-bottom:none}
  .badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500}
  .badge-published{background:rgba(68,221,136,.15);color:var(--green)}
  .badge-draft{background:rgba(144,144,168,.15);color:var(--text2)}
  .badge-review{background:rgba(255,136,51,.15);color:var(--orange)}
  .badge-running,.badge-pending{background:rgba(68,170,255,.15);color:var(--blue)}
  .badge-failed,.badge-error{background:rgba(255,68,102,.15);color:var(--red)}
  .badge-completed,.badge-connected{background:rgba(68,221,136,.15);color:var(--green)}
  .badge-idle,.badge-disconnected{background:rgba(144,144,168,.15);color:var(--text2)}
  .score-bar{display:flex;align-items:center;gap:8px}
  .score-track{flex:1;height:4px;background:var(--surface3);border-radius:2px;min-width:60px}
  .score-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent2),var(--accent))}
  .score-num{font-size:12px;font-weight:600;color:var(--accent);min-width:24px}
  .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px)}
  .modal{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:28px;width:600px;max-width:95vw;max-height:85vh;overflow-y:auto}
  .modal-title{font-family:'DM Serif Display',serif;font-size:22px;margin-bottom:6px}
  .modal-sub{font-size:13px;color:var(--text3);margin-bottom:24px}
  .modal-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:24px;padding-top:20px;border-top:1px solid var(--border)}
  .form-group{margin-bottom:18px}
  .form-label{font-size:12px;color:var(--text2);margin-bottom:6px;display:block;font-weight:500}
  .form-input,.form-select,.form-textarea{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:7px;padding:10px 14px;font-size:13px;color:var(--text);font-family:'DM Sans',sans-serif;transition:border-color .15s;outline:none}
  .form-input:focus,.form-select:focus,.form-textarea:focus{border-color:var(--accent2)}
  .form-textarea{resize:vertical;min-height:100px}
  .form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .form-select option{background:var(--surface2)}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
  .tabs{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:24px}
  .tab{padding:10px 20px;font-size:13px;cursor:pointer;color:var(--text3);border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .15s}
  .tab:hover{color:var(--text2)}
  .tab.active{color:var(--accent);border-bottom-color:var(--accent)}
  .section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
  .section-title{font-family:'DM Serif Display',serif;font-size:18px}
  .section-sub{font-size:12px;color:var(--text3);margin-top:2px}
  .search-bar{display:flex;align-items:center;gap:8px;background:var(--surface2);border:1px solid var(--border);border-radius:7px;padding:8px 14px}
  .search-bar input{background:none;border:none;outline:none;color:var(--text);font-size:13px;width:200px;font-family:'DM Sans',sans-serif}
  .search-bar input::placeholder{color:var(--text3)}
  .empty{text-align:center;padding:48px;color:var(--text3)}
  .empty-icon{font-size:36px;margin-bottom:12px}
  .empty-text{font-size:14px}
  .info-box{background:rgba(124,106,247,.1);border:1px solid rgba(124,106,247,.3);border-radius:8px;padding:12px 16px;font-size:12px;color:var(--text2);margin-bottom:16px}
  .activity-item{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid rgba(42,42,56,.5)}
  .activity-dot{width:8px;height:8px;border-radius:50%;background:var(--accent2);margin-top:4px;flex-shrink:0}
  .activity-text{font-size:12px;color:var(--text2);line-height:1.5}
  .activity-time{font-size:11px;color:var(--text3);margin-top:2px}
  .pulse-dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block}
  .pulse-dot.running{animation:pulse 1.5s infinite}
  .pulse-dot.failed{background:var(--red)}
  .pulse-dot.idle,.pulse-dot.completed{background:var(--text3)}
  @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.3)}}
  .role-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px}
  .permission-tag{display:inline-flex;padding:3px 10px;border-radius:20px;font-size:11px;background:var(--surface2);color:var(--text2);border:1px solid var(--border);margin:3px}
  .api-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:12px}
  .loading{display:flex;align-items:center;justify-content:center;padding:40px;color:var(--text3);font-size:14px}
  .error-box{background:rgba(255,68,102,.1);border:1px solid rgba(255,68,102,.3);border-radius:8px;padding:12px 16px;font-size:12px;color:var(--red);margin-bottom:16px}
  .checkbox{display:flex;align-items:center;gap:8px;cursor:pointer}
  .checkbox input{accent-color:var(--accent2);width:14px;height:14px}
  .checkbox span{font-size:13px;color:var(--text2)}
  ::-webkit-scrollbar{width:6px;height:6px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:var(--surface3);border-radius:3px}
  ::-webkit-scrollbar-thumb:hover{background:var(--border)}
`;

// ─── SMALL COMPONENTS ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const s = (status || 'draft').toLowerCase();
  return <span className={`badge badge-${s}`}>{s}</span>;
}

function ScoreBar({ score }: { score: number | null }) {
  const val = score ?? 0;
  return (
    <div className="score-bar">
      <div className="score-track"><div className="score-fill" style={{ width: `${val}%` }} /></div>
      <span className="score-num">{val}</span>
    </div>
  );
}

function AgentDot({ status }: { status: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span className={`pulse-dot ${status}`} />
      <span style={{ fontSize: 12, color: status === 'running' ? 'var(--blue)' : status === 'failed' ? 'var(--red)' : 'var(--text3)' }}>{status}</span>
    </span>
  );
}

function Spinner() {
  return <div className="loading">Loading…</div>;
}

// ─── DASHBOARD ────────────────────────────────────────────────────────────────

function Dashboard({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [stats, setStats] = useState({ total: 0, published: 0, draft: 0, avgScore: 0 });
  const [recentTopics, setRecentTopics] = useState<Topic[]>([]);
  const [recentRuns, setRecentRuns] = useState<RunLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const db = getSupabase();
    Promise.all([
      db.from('trending_topics').select('id, status, viral_score'),
      db.from('trending_topics').select('id, title, category_id, status, viral_score, created_at').order('created_at', { ascending: false }).limit(5),
      db.from('runs_log').select('*').order('created_at', { ascending: false }).limit(6),
    ]).then(([statsRes, topicsRes, runsRes]) => {
      if (statsRes.data) {
        const all = statsRes.data;
        const published = all.filter((t: any) => t.status === 'published').length;
        const draft     = all.filter((t: any) => t.status === 'draft').length;
        const scores    = all.map((t: any) => t.viral_score).filter(Boolean);
        const avg       = scores.length
          ? Math.round(scores.reduce((a: number, b: number) => a + b, 0) / scores.length * 10) / 10
          : 0;
        setStats({ total: all.length, published, draft, avgScore: avg });
      }
      if (topicsRes.data) setRecentTopics(topicsRes.data as Topic[]);
      if (runsRes.data)   setRecentRuns(runsRes.data as RunLog[]);
      setLoading(false);
    });
  }, []);

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="stats-grid">
        {[
          { label: 'Total Topics',    value: stats.total,     note: 'in database' },
          { label: 'Published',       value: stats.published, note: 'live on site' },
          { label: 'Drafts',          value: stats.draft,     note: 'pending review' },
          { label: 'Avg Viral Score', value: stats.avgScore,  note: 'across all topics' },
        ].map((s, i) => (
          <div key={i} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-change">{s.note}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="section-header">
            <div><div className="section-title">Recent Topics</div><div className="section-sub">From Supabase</div></div>
            <button className="btn btn-sm btn-ghost" onClick={() => onNavigate('topics')}>View all →</button>
          </div>
          {recentTopics.length === 0 && (
            <div className="empty"><div className="empty-icon">📭</div><div className="empty-text">No topics yet. Run the agent first.</div></div>
          )}
          {recentTopics.map(t => (
            <div key={t.id} style={{ padding: '10px 0', borderBottom: '1px solid rgba(42,42,56,.5)' }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StatusBadge status={t.status} />
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>{t.category_id ? CATEGORY_MAP[t.category_id] : '—'}</span>
                <ScoreBar score={t.viral_score} />
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="section-header">
            <div><div className="section-title">Agent Run History</div><div className="section-sub">From runs_log</div></div>
          </div>
          {recentRuns.length === 0 && (
            <div className="empty"><div className="empty-icon">🤖</div><div className="empty-text">No runs recorded yet.</div></div>
          )}
          {recentRuns.map((r, i) => (
            <div key={i} className="activity-item">
              <div className="activity-dot" style={{ background: r.status === 'completed' ? 'var(--green)' : r.status === 'failed' ? 'var(--red)' : 'var(--blue)' }} />
              <div>
                <div className="activity-text">
                  {r.topics_published ?? 0} published · {r.topics_collected ?? 0} collected · {r.errors ?? 0} errors
                  {r.duration_seconds ? ` · ${r.duration_seconds}s` : ''}
                </div>
                <div className="activity-time">{r.batch_id} · {new Date(r.created_at).toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── TOPICS PAGE ──────────────────────────────────────────────────────────────

function TopicsPage() {
  const [topics, setTopics]           = useState<Topic[]>([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreate, setShowCreate]   = useState(false);
  const [showEdit, setShowEdit]       = useState<Topic | null>(null);
  const [saving, setSaving]           = useState(false);
  const [error, setError]             = useState('');

  const emptyForm = { title: '', category_id: 1, status: 'draft', summary: '', article: '' };
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    const db = getSupabase();
    const { data } = await db
      .from('trending_topics')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(200);
    setTopics((data as Topic[]) || []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = topics.filter(t =>
    t.title.toLowerCase().includes(search.toLowerCase()) &&
    (filterStatus === 'all' || t.status === filterStatus),
  );

  const createTopic = async () => {
    setSaving(true); setError('');
    const db   = getSupabase();
    const slug = form.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '-' + Date.now();
    const { error: err } = await db.from('trending_topics').insert({
      title: form.title, slug, category_id: form.category_id,
      status: form.status, summary: form.summary || null,
      article: form.article || null, viral_score: 0,
    });
    if (err) { setError(err.message); setSaving(false); return; }
    await load();
    setShowCreate(false);
    setForm(emptyForm);
    setSaving(false);
  };

  const updateTopic = async () => {
    if (!showEdit) return;
    setSaving(true); setError('');
    const db = getSupabase();
    const { error: err } = await db.from('trending_topics').update({
      title: form.title, category_id: form.category_id,
      status: form.status, summary: form.summary || null,
      article: form.article || null,
    }).eq('id', showEdit.id);
    if (err) { setError(err.message); setSaving(false); return; }
    await load();
    setShowEdit(null);
    setSaving(false);
  };

  const deleteTopic = async (id: string) => {
    if (!confirm('Delete this topic? This cannot be undone.')) return;
    const db = getSupabase();
    await db.from('trending_topics').delete().eq('id', id);
    await load();
  };

  const togglePublish = async (id: string, current: string) => {
    const db        = getSupabase();
    const newStatus = current === 'published' ? 'draft' : 'published';
    await db.from('trending_topics').update({
      status: newStatus,
      published_at: newStatus === 'published' ? new Date().toISOString() : null,
    }).eq('id', id);
    await load();
  };

  const openEdit = (t: Topic) => {
    setForm({ title: t.title, category_id: t.category_id || 1, status: t.status, summary: t.summary || '', article: t.article || '' });
    setShowEdit(t);
  };

  const TopicModal = ({ isEdit }: { isEdit: boolean }) => (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) { setShowCreate(false); setShowEdit(null); } }}>
      <div className="modal">
        <div className="modal-title">{isEdit ? 'Edit Topic' : 'Create New Topic'}</div>
        <div className="modal-sub">{isEdit ? 'Update content and settings.' : 'Manually create a topic and publish it to the site.'}</div>
        {error && <div className="error-box">⚠ {error}</div>}
        <div className="form-group">
          <label className="form-label">Title *</label>
          <input className="form-input" placeholder="Topic headline" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Category</label>
            <select className="form-select" value={form.category_id} onChange={e => setForm({ ...form, category_id: Number(e.target.value) })}>
              {Object.entries(CATEGORY_MAP).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Status</label>
            <select className="form-select" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
              <option value="draft">Draft</option>
              <option value="review">Review</option>
              <option value="published">Published</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Summary</label>
          <textarea className="form-textarea" style={{ minHeight: 80 }} placeholder="Short summary shown in feeds…" value={form.summary} onChange={e => setForm({ ...form, summary: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">Article Body</label>
          <textarea className="form-textarea" placeholder="Full article content…" value={form.article} onChange={e => setForm({ ...form, article: e.target.value })} />
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => { setShowCreate(false); setShowEdit(null); }}>Cancel</button>
          <button className="btn btn-primary" disabled={!form.title || saving} onClick={isEdit ? updateTopic : createTopic}>
            {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Topic'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 20 }}>
        <div><div className="section-title">Topics</div><div className="section-sub">{topics.length} in database</div></div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div className="search-bar">
            <span style={{ color: 'var(--text3)' }}>🔍</span>
            <input placeholder="Search topics…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <select className="form-select" style={{ width: 130 }} value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="all">All Status</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
            <option value="review">Review</option>
          </select>
          <button className="btn btn-primary" onClick={() => { setForm(emptyForm); setShowCreate(true); }}>+ New Topic</button>
        </div>
      </div>

      {loading ? <Spinner /> : (
        <div className="card" style={{ padding: 0 }}>
          {filtered.length === 0
            ? <div className="empty"><div className="empty-icon">📭</div><div className="empty-text">No topics found.</div></div>
            : (
              <div className="table-wrap">
                <table>
                  <thead><tr>
                    <th>Title</th><th>Category</th><th>Status</th>
                    <th>Viral Score</th><th>Created</th><th>Actions</th>
                  </tr></thead>
                  <tbody>
                    {filtered.map(t => (
                      <tr key={t.id}>
                        <td style={{ fontWeight: 500, maxWidth: 300 }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.title}</div>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text2)' }}>{t.category_id ? CATEGORY_MAP[t.category_id] : '—'}</td>
                        <td><StatusBadge status={t.status} /></td>
                        <td><ScoreBar score={t.viral_score} /></td>
                        <td style={{ fontSize: 12, color: 'var(--text3)' }}>{new Date(t.created_at).toLocaleDateString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button className="btn btn-sm btn-ghost" onClick={() => openEdit(t)}>Edit</button>
                            <button className="btn btn-sm btn-secondary" onClick={() => togglePublish(t.id, t.status)}>
                              {t.status === 'published' ? 'Unpublish' : 'Publish'}
                            </button>
                            <button className="btn btn-sm btn-danger" onClick={() => deleteTopic(t.id)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </div>
      )}

      {showCreate && <TopicModal isEdit={false} />}
      {showEdit   && <TopicModal isEdit={true} />}
    </div>
  );
}

// ─── CATEGORIES PAGE ──────────────────────────────────────────────────────────

function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [topicCounts, setTopicCounts] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');

  const load = useCallback(async () => {
    const db = getSupabase();
    const [catRes, countRes] = await Promise.all([
      db.from('categories').select('*').order('id'),
      db.from('trending_topics').select('category_id'),
    ]);
    setCategories((catRes.data as Category[]) || []);
    const counts: Record<number, number> = {};
    (countRes.data || []).forEach((t: any) => {
      if (t.category_id) counts[t.category_id] = (counts[t.category_id] || 0) + 1;
    });
    setTopicCounts(counts);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const createCategory = async () => {
    if (!newName.trim()) return;
    const db = getSupabase();
    await db.from('categories').insert({ name: newName.trim() });
    setNewName(''); setShowCreate(false);
    await load();
  };

  const deleteCategory = async (id: number) => {
    if (!confirm('Delete this category? Topics using it will lose their category.')) return;
    const db = getSupabase();
    await db.from('categories').delete().eq('id', id);
    await load();
  };

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 20 }}>
        <div><div className="section-title">Categories</div><div className="section-sub">{categories.length} categories</div></div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Category</button>
      </div>

      {loading ? <Spinner /> : (
        <div className="card" style={{ padding: 0 }}>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Topics</th><th>Actions</th></tr></thead>
            <tbody>
              {categories.map(c => (
                <tr key={c.id}>
                  <td style={{ color: 'var(--text3)', fontSize: 12 }}>{c.id}</td>
                  <td style={{ fontWeight: 500 }}>{c.name}</td>
                  <td style={{ fontSize: 12, color: 'var(--text2)' }}>{topicCounts[c.id] || 0} topics</td>
                  <td>
                    <button className="btn btn-sm btn-danger" onClick={() => deleteCategory(c.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setShowCreate(false); }}>
          <div className="modal" style={{ width: 420 }}>
            <div className="modal-title">New Category</div>
            <div className="modal-sub">Added to the categories table and available in the agent pipeline.</div>
            <div className="form-group">
              <label className="form-label">Category Name *</label>
              <input className="form-input" placeholder="e.g. Real Estate" value={newName} onChange={e => setNewName(e.target.value)} autoFocus />
            </div>
            <div className="info-box">💡 After creating, add the new category ID to <code style={{ fontFamily: 'monospace' }}>classification_node.py</code> in the agent so it can assign topics to it.</div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" disabled={!newName.trim()} onClick={createCategory}>Create Category</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── AGENTS PAGE ──────────────────────────────────────────────────────────────

function AgentsPage() {
  const [activeTab, setActiveTab] = useState('runs');
  const [runs, setRuns]           = useState<RunLog[]>([]);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    const db = getSupabase();
    db.from('runs_log')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(20)
      .then(({ data }) => { setRuns((data as RunLog[]) || []); setLoading(false); });
  }, []);

  return (
    <div>
      <div className="tabs">
        {['runs', 'config'].map(t => (
          <div key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </div>
        ))}
      </div>

      {activeTab === 'runs' && (
        <div>
          <div className="info-box">
            🤖 The agent runs every 4 hours via Inngest CRON. Each run is logged to <strong>runs_log</strong>. To trigger manually: <code style={{ fontFamily: 'monospace', background: 'rgba(0,0,0,.3)', padding: '2px 6px', borderRadius: 4 }}>cd apps/agent && python main.py</code>
          </div>
          {loading ? <Spinner /> : (
            <div className="card" style={{ padding: 0 }}>
              {runs.length === 0
                ? <div className="empty"><div className="empty-icon">📋</div><div className="empty-text">No runs logged yet.</div></div>
                : (
                  <table>
                    <thead><tr>
                      <th>Batch ID</th><th>Status</th><th>Collected</th>
                      <th>Published</th><th>Errors</th><th>Duration</th><th>Time</th>
                    </tr></thead>
                    <tbody>
                      {runs.map(r => (
                        <tr key={r.id}>
                          <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--accent2)' }}>{r.batch_id}</td>
                          <td><StatusBadge status={r.status} /></td>
                          <td style={{ fontSize: 13 }}>{r.topics_collected ?? '—'}</td>
                          <td style={{ fontSize: 13, fontWeight: 600, color: 'var(--green)' }}>{r.topics_published ?? '—'}</td>
                          <td style={{ fontSize: 13, color: (r.errors ?? 0) > 0 ? 'var(--red)' : 'var(--text3)' }}>{r.errors ?? '—'}</td>
                          <td style={{ fontSize: 12, color: 'var(--text3)' }}>{r.duration_seconds ? `${r.duration_seconds}s` : '—'}</td>
                          <td style={{ fontSize: 12, color: 'var(--text3)' }}>{new Date(r.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'config' && (
        <div className="card">
          <div className="section-title" style={{ marginBottom: 20 }}>Pipeline Configuration</div>
          <div className="info-box">⚙️ These values come from <code style={{ fontFamily: 'monospace' }}>apps/agent/config/settings.py</code>. Update the source files to change them.</div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Cron Schedule (Inngest)</label>
              <input className="form-input" defaultValue="0 */4 * * *" readOnly style={{ opacity: .7 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Viral Score Threshold</label>
              <input className="form-input" defaultValue="50" type="number" readOnly style={{ opacity: .7 }} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Dedup Merge Threshold</label>
              <input className="form-input" defaultValue="70" type="number" readOnly style={{ opacity: .7 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Content Model</label>
              <input className="form-input" defaultValue="claude-sonnet-4-6" readOnly style={{ opacity: .7 }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── MEDIA PAGE ───────────────────────────────────────────────────────────────

function MediaPage() {
  const [activeTab, setActiveTab] = useState('sora');

  const tools: Record<string, { name: string; icon: string; provider: string; description: string; cost: string }> = {
    sora:   { name: 'Sora',   icon: '🎬', provider: 'OpenAI',          description: 'Generate cinematic video clips from text. Add SORA_API_KEY to apps/agent/.env to enable.',                        cost: '~$0.15/sec' },
    veo:    { name: 'Veo',    icon: '🎥', provider: 'Google DeepMind', description: 'Google\'s video generation model for realistic news-style footage. Add VEO_API_KEY to apps/agent/.env to enable.',  cost: '~$0.12/sec' },
    vizard: { name: 'Vizard', icon: '✂️', provider: 'Vizard.ai',       description: 'Auto-clip long videos into social shorts. Add VIZARD_API_KEY to apps/agent/.env to enable.',                        cost: '~$0.02/clip' },
  };

  const tool = tools[activeTab];

  return (
    <div>
      <div className="tabs">
        {Object.entries(tools).map(([key, t]) => (
          <div key={key} className={`tab ${activeTab === key ? 'active' : ''}`} onClick={() => setActiveTab(key)}>
            {t.icon} {t.name}
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
            <div style={{ fontSize: 32 }}>{tool.icon}</div>
            <div>
              <div style={{ fontFamily: 'DM Serif Display', fontSize: 20 }}>{tool.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>{tool.provider} · {tool.cost}</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.6, marginBottom: 16 }}>{tool.description}</p>
          <div className="info-box">
            Add the API key to <code style={{ fontFamily: 'monospace' }}>apps/agent/.env</code> and restart the agent. It will automatically use {tool.name} for media generation on each pipeline run.
          </div>
        </div>

        <div className="card">
          <div className="section-title" style={{ marginBottom: 16, fontSize: 16 }}>Manual Generation</div>
          <div className="form-group">
            <label className="form-label">Prompt</label>
            <textarea className="form-textarea" style={{ minHeight: 80 }} placeholder={`Describe what you want ${tool.name} to generate…`} />
          </div>
          {activeTab !== 'vizard' && (
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Duration (seconds)</label>
                <input className="form-input" type="number" defaultValue="10" />
              </div>
              <div className="form-group">
                <label className="form-label">Style</label>
                <select className="form-select">
                  <option>News broadcast</option>
                  <option>Documentary</option>
                  <option>Cinematic</option>
                  <option>Social media</option>
                </select>
              </div>
            </div>
          )}
          {activeTab === 'vizard' && (
            <div className="form-group">
              <label className="form-label">Source Video URL</label>
              <input className="form-input" placeholder="YouTube URL or direct video link" />
            </div>
          )}
          <div className="info-box">Connect the API key in apps/agent/.env to enable generation.</div>
          <button className="btn btn-primary" disabled>Connect API Key First</button>
        </div>
      </div>
    </div>
  );
}

// ─── USERS PAGE ───────────────────────────────────────────────────────────────

function UsersPage() {
  const [activeTab, setActiveTab] = useState('roles');

  return (
    <div>
      <div className="tabs">
        {['roles', 'invite'].map(t => (
          <div key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </div>
        ))}
      </div>

      {activeTab === 'roles' && (
        <div>
          <div className="info-box">
            👥 User authentication is handled by Supabase Auth. Manage users at <strong>supabase.com → Authentication → Users</strong>. Roles below are the defined permission levels.
          </div>
          <div className="grid-2">
            {ROLES.map(role => (
              <div key={role.id} className="role-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: role.color, flexShrink: 0 }} />
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{role.name}</div>
                </div>
                <div>
                  {role.permissions[0] === 'all'
                    ? <span className="permission-tag" style={{ color: 'var(--accent)', borderColor: 'rgba(232,197,71,.3)' }}>Full Access</span>
                    : role.permissions.map(p => <span key={p} className="permission-tag">{p}</span>)
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'invite' && (
        <div className="card" style={{ maxWidth: 500 }}>
          <div className="section-title" style={{ marginBottom: 6, fontSize: 16 }}>Invite Team Member</div>
          <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>Invitations are sent via Supabase Auth.</div>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input className="form-input" type="email" placeholder="colleague@thenewslane.com" />
          </div>
          <div className="form-group">
            <label className="form-label">Role</label>
            <select className="form-select">
              {ROLES.map(r => <option key={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="info-box">Configure Supabase Auth email templates in your project settings to enable invitations.</div>
          <button className="btn btn-primary">Send Invitation</button>
        </div>
      )}
    </div>
  );
}

// ─── API MANAGER PAGE ─────────────────────────────────────────────────────────

function APIPage() {
  const [selected, setSelected] = useState<number | null>(null);
  const [apiKeys, setApiKeys]   = useState<Record<number, string>>({});

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 20 }}>
        <div><div className="section-title">API Manager</div><div className="section-sub">All external service connections</div></div>
      </div>

      <div className="info-box" style={{ marginBottom: 20 }}>
        🔑 API keys are stored in <code style={{ fontFamily: 'monospace' }}>apps/agent/.env</code> for the Python agent and in <strong>Vercel Environment Variables</strong> for deployed apps. The <code style={{ fontFamily: 'monospace' }}>ENV KEY</code> column shows the variable name to use.
      </div>

      <div className="grid-3">
        {API_INTEGRATIONS.map(api => (
          <div
            key={api.id}
            className="api-card"
            style={{ cursor: 'pointer', border: selected === api.id ? '1px solid var(--accent2)' : '1px solid var(--border)' }}
            onClick={() => setSelected(selected === api.id ? null : api.id)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ fontSize: 24, width: 44, height: 44, background: 'var(--surface2)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{api.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{api.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)' }}>{api.provider}</div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text3)' }}>{api.type}</div>
            <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--accent2)', background: 'var(--surface2)', padding: '4px 8px', borderRadius: 4 }}>{api.envKey}</div>
            {selected === api.id && (
              <div style={{ marginTop: 4 }}>
                <label className="form-label">New Key Value</label>
                <input
                  className="form-input"
                  type="password"
                  placeholder="Paste API key…"
                  value={apiKeys[api.id] || ''}
                  onChange={e => setApiKeys({ ...apiKeys, [api.id]: e.target.value })}
                  onClick={e => e.stopPropagation()}
                />
                <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 6 }}>
                  Add to <code style={{ fontFamily: 'monospace' }}>apps/agent/.env</code> as <code style={{ fontFamily: 'monospace' }}>{api.envKey}=your_key</code>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── SIGN-OUT ─────────────────────────────────────────────────────────────────

async function handleSignOut() {
  const db = getSupabase();
  await db.auth.signOut();
  window.location.href = '/login';
}

// ─── ROOT APP ─────────────────────────────────────────────────────────────────

export default function StudioCMS() {
  const [activePage, setActivePage] = useState('dashboard');

  const nav = [
    { id: 'dashboard',  label: 'Dashboard',    icon: '⬜', section: 'overview' },
    { id: 'topics',     label: 'Topics',        icon: '📄', section: 'content' },
    { id: 'categories', label: 'Categories',    icon: '🏷️', section: 'content' },
    { id: 'agents',     label: 'Agent Runs',    icon: '🤖', section: 'content' },
    { id: 'media',      label: 'Media & Video', icon: '🎬', section: 'tools' },
    { id: 'api',        label: 'API Manager',   icon: '🔌', section: 'tools' },
    { id: 'users',      label: 'Users & Roles', icon: '👥', section: 'admin' },
  ];

  const sectionLabels: Record<string, string> = {
    overview: 'Overview', content: 'Content', tools: 'Tools', admin: 'Admin',
  };

  const pageInfo: Record<string, { title: string; sub: string }> = {
    dashboard:  { title: 'Dashboard',    sub: 'Live data from Supabase' },
    topics:     { title: 'Topics',        sub: 'Create, edit, publish' },
    categories: { title: 'Categories',    sub: 'Manage content structure' },
    agents:     { title: 'Agent Runs',    sub: 'Pipeline history & config' },
    media:      { title: 'Media & Video', sub: 'Sora · Veo · Vizard' },
    api:        { title: 'API Manager',   sub: 'External integrations' },
    users:      { title: 'Users & Roles', sub: 'Team permissions' },
  };

  const pages: Record<string, React.ComponentType<any>> = {
    dashboard: Dashboard, topics: TopicsPage, categories: CategoriesPage,
    agents: AgentsPage,   media: MediaPage,   api: APIPage,
    users: UsersPage,
  };
  const PageComponent = pages[activePage] || Dashboard;
  const sections      = ['overview', 'content', 'tools', 'admin'];

  return (
    <>
      <style suppressHydrationWarning>{css}</style>
      <div className="cms">
        {/* SIDEBAR */}
        <div className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-mark">theNewslane</div>
            <div className="logo-sub">Studio · CMS</div>
          </div>

          {sections.map(section => {
            const items = nav.filter(n => n.section === section);
            if (!items.length) return null;
            return (
              <div key={section} className="nav-section">
                <div className="nav-label">{sectionLabels[section]}</div>
                {items.map(item => (
                  <div
                    key={item.id}
                    className={`nav-item ${activePage === item.id ? 'active' : ''}`}
                    onClick={() => setActivePage(item.id)}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            );
          })}

          <div className="sidebar-footer">
            <div className="user-mini">
              <div className="avatar-sm">SA</div>
              <div style={{ flex: 1 }}>
                <div className="user-name-sm">Super Admin</div>
                <div className="user-role-sm">studio.thenewslane.com</div>
              </div>
              <button
                onClick={handleSignOut}
                title="Sign out"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: 14, padding: 4 }}
              >⏏</button>
            </div>
          </div>
        </div>

        {/* MAIN */}
        <div className="main">
          <div className="topbar">
            <div>
              <div className="topbar-title">{pageInfo[activePage]?.title}</div>
              <div className="topbar-sub">{pageInfo[activePage]?.sub}</div>
            </div>
            <div className="topbar-actions">
              <button className="btn btn-secondary btn-sm" onClick={() => window.open('https://thenewslane.com', '_blank')}>↗ View Site</button>
              <button className="btn btn-secondary btn-sm" onClick={() => window.open('https://app.supabase.com', '_blank')}>🗄 Supabase</button>
            </div>
          </div>

          <div className="content">
            <PageComponent onNavigate={setActivePage} />
          </div>
        </div>
      </div>
    </>
  );
}
