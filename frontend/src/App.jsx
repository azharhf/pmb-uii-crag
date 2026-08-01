import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Bot,
  User,
  Send,
  Square,
  Sparkles,
  ShieldCheck,
  FileText,
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Info,
  CheckCircle2,
  BookOpen,
  GraduationCap,
  Download,
  Eye,
  EyeOff,
  X,
  PanelLeftClose,
  PanelLeft,
  FileDown,
  Search,
  Filter,
  ArrowRight,
  BookMarked,
  FileCode,
  Banknote,
  Award,
  ClipboardCheck,
  FileCheck,
  Building2,
  PhoneCall,
  HelpCircle,
  CreditCard,
  FolderDown,
  FileQuestion,
  FolderOpen,
  Settings,
  ListFilter,
  Copy,
  Check,
  Pencil,
  RotateCcw,
  Sliders
} from 'lucide-react';

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'https://azharhf-pmb-uii-crag-backend.hf.space'
).replace(/\/$/, '');

export default function App() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      isWelcome: true,
      text: 'Selamat datang di **Asisten Akademik PMB Universitas Islam Indonesia (UII) 2026**.\n\nSaya didukung oleh arsitektur **Corrective RAG (CRAG)** dengan model **Gemini 3.6 Flash** & vektor semantik **IndoBERT**. Silakan ajukan pertanyaan seputar jalur pendaftaran, tarif biaya studi, beasiswa, atau program studi.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      meta: null
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [activeCitationIdx, setActiveCitationIdx] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [fullMdDoc, setFullMdDoc] = useState(null);
  const [loadingMd, setLoadingMd] = useState(false);
  const [activeModuleFilter, setActiveModuleFilter] = useState(null);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // E-Book Reader State (Search & Auto Yellow Highlight)
  const [mdSearchQuery, setMdSearchQuery] = useState('');

  // Official PDF/DOCX Documents Hub Modal State & Search Query
  const [officialDocsModalOpen, setOfficialDocsModalOpen] = useState(false);
  const [officialDocsList, setOfficialDocsList] = useState([]);
  const [officialDocsSearchQuery, setOfficialDocsSearchQuery] = useState('');
  const [loadingOfficialDocs, setLoadingOfficialDocs] = useState(false);
  const [pdfPreviewModalDoc, setPdfPreviewModalDoc] = useState(null);

  // EDIT PROMPT & COPY STATE
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [copiedMsgId, setCopiedMsgId] = useState(null);

  // SETTINGS & HELP MODAL STATES
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [helpModalOpen, setHelpModalOpen] = useState(false);
  const [topKConfig, setTopKConfig] = useState(5);
  const [showMetadataBadges, setShowMetadataBadges] = useState(true);

  // Refs for scrolling sidebar and messages
  const abortControllerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const masterDocsSectionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const fetchOfficialDocs = async () => {
    setLoadingOfficialDocs(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/api/official_documents`);
      setOfficialDocsList(res.data.documents || []);
    } catch (err) {
      console.error("Failed to fetch official documents", err);
    } finally {
      setLoadingOfficialDocs(false);
    }
  };

  const handleOpenOfficialDocsHub = () => {
    setOfficialDocsSearchQuery('');
    setOfficialDocsModalOpen(true);
    fetchOfficialDocs();
  };

  const handleSlimRailMasterClick = () => {
    setSidebarOpen(true);
    setTimeout(() => {
      masterDocsSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 150);
  };

  const quickTopics = [
    { label: 'Jalur Pendaftaran PMB', query: 'Apa saja pilihan jalur seleksi pendaftaran mahasiswa baru di UII?' },
    { label: 'Rincian Biaya & SPP', query: 'Berapa rincian tarif biaya studi Catur Darma dan SPP di UII?' },
    { label: 'Beasiswa Hafiz Al-Qur\'an', query: 'Apa saja syarat pendaftaran dan fasilitas Beasiswa Hafiz Al-Qur\'an?' },
    { label: 'Program Studi FTI & Hukum', query: 'Program studi apa saja yang ada di Fakultas Teknologi Industri dan Fakultas Hukum UII?' }
  ];

  const academicModules = [
    { name: 'BROSUR', desc: 'Informasi Umum PMB', query: 'Tampilkan rangkuman brosur utama PMB Universitas Islam Indonesia 2026.', icon: BookOpen },
    { name: 'BIAYA', desc: 'Catur Darma & SPP', query: 'Berapa rincian tarif biaya studi Catur Darma dan SPP di UII?', icon: Banknote },
    { name: 'SELEKSI', desc: 'CBT, UTBK, Rapor', query: 'Apa saja rincian jalur seleksi penerimaan mahasiswa baru di UII?', icon: ClipboardCheck },
    { name: 'BEASISWA', desc: 'Hafiz, Santri, Duafa', query: 'Apa saja program beasiswa yang tersedia bagi calon mahasiswa UII?', icon: Award },
    { name: 'PRODI', desc: 'Fakultas & Jurusan', query: 'Fakultas dan program studi apa saja yang dibuka di UII?', icon: Building2 },
    { name: 'KONTAK', desc: 'Layanan & Alamat', query: 'Bagaimana cara menghubungi panitia pendaftaran PMB UII?', icon: PhoneCall }
  ];

  const masterKnowledgeDocs = [
    { name: 'biaya_pmb_knowledge_base.md', mod: 'BIAYA', title: 'Biaya & SPP PMB UII Master', icon: Banknote },
    { name: 'brosur_knowledge_base.md', mod: 'BROSUR', title: 'Brosur PMB UII 2026 Master', icon: BookOpen },
    { name: 'beasiswa_knowledge_base.md', mod: 'BEASISWA', title: 'Beasiswa UII 2026 Master', icon: Award },
    { name: 'prodi_knowledge_base.md', mod: 'PRODI', title: 'Fakultas & Prodi UII Master', icon: Building2 },
    { name: 'tes_knowledge_base.md', mod: 'SELEKSI', title: 'Jalur Seleksi CBT & UTBK', icon: ClipboardCheck },
    { name: 'rapor_knowledge_base.md', mod: 'RAPOR', title: 'Jalur Seleksi Rapor Master', icon: FileCheck },
    { name: 'kontak_knowledge_base.md', mod: 'KONTAK', title: 'Kontak Layanan Resmi Master', icon: PhoneCall },
    { name: 'faq_knowledge_base.md', mod: 'FAQ', title: 'Tanya Jawab Populer Master', icon: HelpCircle },
    { name: 'pembayaran_knowledge_base.md', mod: 'PEMBAYARAN', title: 'Panduan Bank & Transfer', icon: CreditCard },
    { name: 'unduh_knowledge_base.md', mod: 'UNDUH_DOKUMEN', title: 'Berkas Panduan & Syarat', icon: FolderDown },
    { name: 'soal_knowledge_base.md', mod: 'CONTOH_SOAL', title: 'Simulasi Soal Seleksi', icon: FileQuestion },
  ];

  const handleSend = async (customQuery = null, overrideMessages = null) => {
    const textToSend = customQuery || query;
    if (!textToSend.trim() || loading) return;

    abortControllerRef.current = new AbortController();

    const currentMsgList = overrideMessages || messages;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const aiMessageId = Date.now() + 1;
    const aiMessageStub = {
      id: aiMessageId,
      sender: 'ai',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      meta: null
    };

    setMessages([...currentMsgList, userMessage, aiMessageStub]);
    if (!customQuery) setQuery('');
    setLoading(true);

    try {
      const historyPayload = currentMsgList.map(m => ({
        sender: m.sender,
        text: m.text
      }));

      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend, top_k: topKConfig, chat_history: historyPayload }),
        signal: abortControllerRef.current.signal
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      let metaData = null;
      let citationsData = [];
      let suggestedFollowup = null;
      let latencyMs = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const payload = JSON.parse(line.slice(6));

              if (currentEvent === 'meta') {
                metaData = {
                  decisionPath: payload.decision_path,
                  confidenceLabel: payload.relevance_eval_label,
                  topScore: payload.top_relevance_score,
                  rewrittenQuery: payload.rewritten_query,
                  citations: [],
                  suggestedFollowup: null,
                  latencyMs: null
                };
                setMessages(prev => prev.map(m =>
                  m.id === aiMessageId ? { ...m, meta: { ...metaData } } : m
                ));
              } else if (currentEvent === 'citations') {
                citationsData = payload.citations || [];
                setMessages(prev => prev.map(m =>
                  m.id === aiMessageId ? { ...m, meta: { ...m.meta, citations: citationsData } } : m
                ));
              } else if (currentEvent === 'token') {
                accumulatedText += payload.chunk;
                setMessages(prev => prev.map(m =>
                  m.id === aiMessageId ? { ...m, text: accumulatedText } : m
                ));
              } else if (currentEvent === 'done') {
                suggestedFollowup = payload.suggested_followup || null;
                latencyMs = payload.total_latency_ms || null;
                setMessages(prev => prev.map(m =>
                  m.id === aiMessageId ? {
                    ...m,
                    text: accumulatedText,
                    meta: {
                      ...m.meta,
                      suggestedFollowup: suggestedFollowup,
                      latencyMs: latencyMs
                    }
                  } : m
                ));
              } else if (currentEvent === 'error') {
                accumulatedText = `[ERROR] Kendala backend: ${payload.detail || 'Unknown error'}`;
                setMessages(prev => prev.map(m =>
                  m.id === aiMessageId ? { ...m, text: accumulatedText, meta: null } : m
                ));
              }
            } catch (parseErr) {
              // Ignore non-JSON data lines
            }
            currentEvent = null;
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === aiMessageId ? {
            ...m,
            text: (m.text || '') + '\n\n**[PROCESS INTERRUPTED]** Generation stopped by user command.',
            meta: null
          } : m
        ));
      } else {
        console.error(err);
        setMessages(prev => prev.map(m =>
          m.id === aiMessageId ? {
            ...m,
            text: '[ERROR] Kendala koneksi backend server FastAPI port 7860.',
            meta: null
          } : m
        ));
      }
    } finally {
      setLoading(false);
      setActiveModuleFilter(null);
      abortControllerRef.current = null;
    }
  };

  const handleEditSave = (msgId, newText) => {
    if (!newText.trim() || loading) return;
    const msgIdx = messages.findIndex(m => m.id === msgId);
    if (msgIdx === -1) return;

    const truncatedHistory = messages.slice(0, msgIdx);
    setEditingMessageId(null);
    setEditingText('');

    handleSend(newText, truncatedHistory);
  };

  const handleRetryResponse = (aiMsgId) => {
    if (loading) return;
    const aiIdx = messages.findIndex(m => m.id === aiMsgId);
    if (aiIdx <= 0) return;
    const userMsg = messages[aiIdx - 1];
    if (!userMsg || userMsg.sender !== 'user') return;

    const truncatedHistory = messages.slice(0, aiIdx - 1);
    handleSend(userMsg.text, truncatedHistory);
  };

  const handleCopyPrompt = (msgId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(msgId);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const handleStopExecution = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const extractSmartKeyword = (titleStr) => {
    if (!titleStr) return '';
    const cleaned = titleStr.replace(/^[0-9\.\#\s\*]+/, '').replace(/[\(\)\[\]\+\:]/g, ' ').trim();
    const words = cleaned.split(/\s+/).filter(w => w.length > 2);
    if (words.length === 0) return titleStr.slice(0, 15);
    return words.slice(0, 3).join(' ');
  };

  const handleFetchFullMd = async (moduleName, highlightSearchRaw = '') => {
    setLoadingMd(true);
    const smartSearch = extractSmartKeyword(highlightSearchRaw);
    setMdSearchQuery(smartSearch);
    try {
      const res = await axios.get(`${API_BASE_URL}/api/document/${moduleName}`);
      setFullMdDoc(res.data);
    } catch (err) {
      console.error("Failed to fetch full md doc", err);
    } finally {
      setLoadingMd(false);
    }
  };

  const handleModuleClick = (mod) => {
    setActiveModuleFilter(mod.name);
    handleSend(mod.query);
  };

  const cleanPreviewText = (rawText) => {
    if (!rawText) return '';
    const lines = rawText.split('\n');
    const uniqueLines = [];
    lines.forEach((line) => {
      const trimmed = line.trim();
      if (trimmed && uniqueLines.length > 0 && uniqueLines[uniqueLines.length - 1].trim() === trimmed) {
        return;
      }
      uniqueLines.push(line);
    });
    let cleaned = uniqueLines.join('\n');
    cleaned = cleaned.replace(/\s+[a-zA-Z]{1,2}\.\.\.$/, '.');
    return cleaned;
  };

  const createYellowHighlightedText = (text, term) => {
    if (!term || !term.trim() || typeof text !== 'string') return text;
    const trimmedTerm = term.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${trimmedTerm})`, 'gi');
    const parts = text.split(regex);
    if (parts.length <= 1) return text;
    return parts.map((part, i) =>
      part.toLowerCase() === term.trim().toLowerCase() ? (
        <mark key={i} className="bg-amber-200 text-slate-900 font-bold px-1.5 py-0.5 rounded shadow-2xs">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const highlightMarkdownComponents = (term) => ({
    p: ({ children }) => <p>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</p>,
    h1: ({ children }) => <h1>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</h1>,
    h2: ({ children }) => <h2>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</h2>,
    h3: ({ children }) => <h3>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</h3>,
    li: ({ children }) => <li>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</li>,
    strong: ({ children }) => <strong>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</strong>,
    td: ({ children }) => <td>{React.Children.map(children, child => typeof child === 'string' ? createYellowHighlightedText(child, term) : child)}</td>
  });

  const isSystemOrErrorMessage = (text) => {
    if (!text) return false;
    const t = text.trim();
    return t.startsWith('[ERROR]') || 
           t.includes('unavailable or quota exceeded') ||
           t.startsWith('[PROCESS INTERRUPTED]') || 
           t.includes('Kendala koneksi') || 
           t.startsWith('[SECURITY FIREWALL') || 
           t.startsWith('[GUARDRAIL NOTICE]');
  };

  const renderBadge = (path) => {
    if (!path || !showMetadataBadges) return null;
    const upperPath = path.toUpperCase();
    if (upperPath.includes('GUARDRAIL') || upperPath.includes('FALLBACK')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FFE4E6] text-[#E11D48] border border-[#E11D48]/30 text-[11px] font-bold uppercase tracking-wider font-display">
          <ShieldCheck className="w-3.5 h-3.5 text-[#E11D48]" />
          Guardrail Notice
        </span>
      );
    } else if (upperPath.includes('DIRECT PASS')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#D1FAE5] text-[#059669] border border-[#059669]/30 text-[11px] font-bold uppercase tracking-wider font-display">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#059669]" />
          Direct Pass (High Confidence)
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FEF3C7] text-[#D97706] border border-[#D97706]/30 text-[11px] font-bold uppercase tracking-wider font-display">
          <Sparkles className="w-3.5 h-3.5 text-[#D97706]" />
          Multi-Query + HyDE + Reranker
        </span>
      );
    }
  };

  const extractTocHeadings = (markdownText, filterQuery = '') => {
    if (!markdownText) return [];
    const lines = markdownText.split('\n');
    const headings = [];
    lines.forEach((line) => {
      const match = line.match(/^(#{1,3})\s+(.+)$/);
      if (match) {
        const titleClean = match[2].replace(/[\*\_]/g, '').trim();
        if (!filterQuery || titleClean.toLowerCase().includes(filterQuery.toLowerCase())) {
          headings.push({
            level: match[1].length,
            title: titleClean
          });
        }
      }
    });
    return headings;
  };

  const filteredOfficialDocs = officialDocsList.filter((doc) => {
    if (!officialDocsSearchQuery.trim()) return true;
    const q = officialDocsSearchQuery.toLowerCase();
    return doc.title.toLowerCase().includes(q) || doc.category.toLowerCase().includes(q);
  });

  return (
    <div className="h-screen w-screen flex bg-white font-sans text-[#0F172A] antialiased overflow-hidden">
      {/* DESKTOP SIDEBAR (320px) & SLIM RAIL (64px) - HIDDEN ON MOBILE */}
      {sidebarOpen ? (
        /* EXPANDED ENTERPRISE SIDEBAR (320px) */
        <aside className="hidden md:flex w-[320px] bg-[#F8FAFC] border-r border-[#E2E8F0] flex-col flex-shrink-0 text-xs shadow-xs z-30 transition-all duration-200 h-full">
          {/* SIDEBAR HEADER */}
          <div className="h-[56px] px-4 border-b border-[#E2E8F0] flex items-center justify-between bg-white flex-shrink-0">
            <div className="flex items-center gap-2.5 whitespace-nowrap overflow-hidden">
              <div className="w-10 h-10 rounded-xl bg-white border border-[#E2E8F0] p-0.5 flex items-center justify-center shadow-xs flex-shrink-0 cursor-pointer hover:scale-105 transition-transform" title="PMB UII AI Academic Assistant">
                <img
                  src="/logo-uii.png"
                  alt="Logo UII"
                  className="w-full h-full object-contain drop-shadow-xs"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.parentNode.innerText = 'UII';
                  }}
                />
              </div>
              <div className="whitespace-nowrap overflow-hidden">
                <h2 className="font-bold text-xs text-[#22489E] font-display leading-tight truncate">
                  PMB UII AI Assistant
                </h2>
                <p className="text-[10px] text-slate-400 font-mono truncate">Academic Repository</p>
              </div>
            </div>

            <button
              onClick={() => setSidebarOpen(false)}
              className="w-9 h-9 rounded-xl bg-white hover:bg-[#EFEEF1] border border-[#E2E8F0] hover:border-[#22489E] text-[#22489E] transition-all duration-200 flex items-center justify-center shadow-xs flex-shrink-0 group relative overflow-hidden"
              title="Tutup Sidebar"
            >
              <PanelLeft className="w-5 h-5 text-[#22489E] group-hover:opacity-0 group-hover:scale-90 transition-all duration-200 absolute" />
              <PanelLeftClose className="w-5 h-5 text-[#22489E] opacity-0 group-hover:opacity-100 group-hover:scale-100 transition-all duration-200" />
            </button>
          </div>

          {/* SIDEBAR CONTENT AREA */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            {/* MODULE CARDS */}
            <div>
              <h3 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3 flex items-center gap-1.5 font-display whitespace-nowrap overflow-hidden">
                <Filter className="w-3.5 h-3.5 text-[#22489E] flex-shrink-0" /> Modul Akademik Interaktif
              </h3>
              <div className="grid grid-cols-2 gap-2.5">
                {academicModules.map((mod, idx) => {
                  const IconComp = mod.icon;
                  const isActive = activeModuleFilter === mod.name && loading;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleModuleClick(mod)}
                      className={`p-3 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between group ${
                        isActive
                          ? 'bg-[#22489E] text-white border-[#22489E] shadow-sm'
                          : 'bg-white hover:bg-[#EFEEF1] text-[#0F172A] border-[#E2E8F0] hover:border-[#22489E]'
                      }`}
                    >
                      <span className="font-bold text-xs flex items-center justify-between font-display whitespace-nowrap overflow-hidden">
                        <span className="flex items-center gap-2 truncate">
                          <IconComp className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-white' : 'text-[#22489E]'}`} />
                          <span className="truncate">{mod.name}</span>
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex-shrink-0" />
                      </span>
                      <span className={`text-[10px] mt-1.5 font-sans truncate ${
                        isActive ? 'text-white/90' : 'text-slate-500'
                      }`}>
                        {mod.desc}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* MASTER KNOWLEDGE .MD FILES LIST */}
            <div ref={masterDocsSectionRef} className="pt-4 border-t border-[#E2E8F0]">
              <h3 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3 flex items-center gap-1.5 font-display whitespace-nowrap overflow-hidden">
                <FileCode className="w-3.5 h-3.5 text-[#22489E] flex-shrink-0" /> Master Knowledge .md Utuh
              </h3>
              <div className="space-y-1.5">
                {masterKnowledgeDocs.map((doc, idx) => {
                  const DocIcon = doc.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleFetchFullMd(doc.mod)}
                      className="w-full p-2.5 bg-white hover:bg-[#EFEEF1] text-left rounded-xl border border-[#E2E8F0] hover:border-[#22489E] flex items-center justify-between text-xs transition-all duration-200"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <DocIcon className="w-4 h-4 text-[#22489E] flex-shrink-0" />
                        <span className="font-medium text-[#0F172A] text-xs truncate font-sans">{doc.title}</span>
                      </div>
                      <BookMarked className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                    </button>
                  );
                })}
              </div>
            </div>

            {/* DOKUMEN & BROSUR RESMI PDF HUB */}
            <div className="pt-4 border-t border-[#E2E8F0]">
              <h3 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3 flex items-center gap-1.5 font-display whitespace-nowrap overflow-hidden">
                <FileDown className="w-3.5 h-3.5 text-[#22489E] flex-shrink-0" /> Dokumen & Brosur PDF/DOCX
              </h3>
              <button
                onClick={handleOpenOfficialDocsHub}
                className="w-full p-3 bg-white hover:bg-[#EFEEF1] rounded-xl border border-[#E2E8F0] hover:border-[#22489E] text-[#22489E] font-bold text-xs flex items-center justify-between transition-all duration-200 shadow-xs"
              >
                <span className="flex items-center gap-2 font-display truncate">
                  <FolderOpen className="w-4 h-4 text-[#22489E] flex-shrink-0" />
                  <span className="truncate">Pusat Berkas PDF & Word</span>
                </span>
                <ArrowRight className="w-4 h-4 flex-shrink-0" />
              </button>
            </div>
          </div>

          {/* SIDEBAR FOOTER */}
          <div className="p-3 border-t border-[#E2E8F0] bg-white flex items-center justify-between text-xs whitespace-nowrap overflow-hidden">
            <button
              onClick={() => setSettingsModalOpen(true)}
              className="p-2 rounded-xl text-slate-500 hover:text-[#22489E] hover:bg-[#EFEEF1] transition-all flex items-center gap-1.5 font-display font-semibold text-[11px]"
              title="Pengaturan Sistem"
            >
              <Settings className="w-4 h-4 text-[#22489E] flex-shrink-0" />
              <span>Settings</span>
            </button>

            <button
              onClick={() => setHelpModalOpen(true)}
              className="p-2 rounded-xl text-slate-500 hover:text-[#22489E] hover:bg-[#EFEEF1] transition-all flex items-center gap-1.5 font-display font-semibold text-[11px]"
              title="Pusat Bantuan & Informasi Chatbot"
            >
              <HelpCircle className="w-4 h-4 text-[#22489E] flex-shrink-0" />
              <span>Bantuan</span>
            </button>
          </div>
        </aside>
      ) : (
        /* SLIM RAIL (64px) - HIDDEN ON MOBILE */
        <aside className="hidden md:flex w-16 bg-[#F8FAFC] border-r border-[#E2E8F0] flex-col items-center flex-shrink-0 z-30 transition-all duration-200 h-full">
          {/* SLIM RAIL HEADER */}
          <div className="h-[56px] w-full flex items-center justify-center border-b border-[#E2E8F0] bg-white flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="w-10 h-10 rounded-xl bg-white hover:bg-[#EFEEF1] border border-[#E2E8F0] hover:border-[#22489E] p-0.5 flex items-center justify-center shadow-xs transition-all duration-200 flex-shrink-0 hover:scale-105"
              title="Buka Sidebar Navigasi UII"
            >
              <img
                src="/logo-uii.png"
                alt="Logo UII"
                className="w-full h-full object-contain drop-shadow-xs"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.parentNode.innerText = 'UII';
                }}
              />
            </button>
          </div>

          {/* SLIM RAIL MAIN TOP ICON ITEMS */}
          <div className="flex-1 flex flex-col items-center py-4 space-y-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2.5 rounded-xl hover:bg-white text-slate-500 hover:text-[#22489E] transition-all duration-200"
              title="Modul Akademik Interaktif"
            >
              <Filter className="w-5 h-5" />
            </button>

            <button
              onClick={handleSlimRailMasterClick}
              className="p-2.5 rounded-xl hover:bg-white text-slate-500 hover:text-[#22489E] transition-all duration-200"
              title="Master Knowledge .md Utuh"
            >
              <FileCode className="w-5 h-5" />
            </button>

            <button
              onClick={handleOpenOfficialDocsHub}
              className="p-2.5 rounded-xl hover:bg-white text-slate-500 hover:text-[#22489E] transition-all duration-200"
              title="Pusat Dokumen PDF & Word"
            >
              <FolderOpen className="w-5 h-5" />
            </button>
          </div>

          {/* SLIM RAIL BOTTOM ANCHORED UTILITIES */}
          <div className="mt-auto flex flex-col items-center pb-4 space-y-3">
            <button
              onClick={() => setSettingsModalOpen(true)}
              className="p-2.5 rounded-xl hover:bg-white text-slate-500 hover:text-[#22489E] transition-all duration-200"
              title="Pengaturan Sistem (Settings)"
            >
              <Settings className="w-5 h-5" />
            </button>

            <button
              onClick={() => setHelpModalOpen(true)}
              className="p-2.5 rounded-xl hover:bg-white text-slate-500 hover:text-[#22489E] transition-all duration-200"
              title="Pusat Bantuan & Deskripsi Chatbot"
            >
              <HelpCircle className="w-5 h-5" />
            </button>
          </div>
        </aside>
      )}

      {/* MOBILE OVERLAY SIDEBAR DRAWER (80% WIDTH ~ w-[82vw] max-w-[340px]) */}
      {mobileDrawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* DARK BACKDROP OVERLAY WITH BLUR */}
          <div
            onClick={() => setMobileDrawerOpen(false)}
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
          />

          {/* SIDEBAR DRAWER PANEL */}
          <div className="relative w-[82vw] max-w-[340px] bg-[#F8FAFC] h-full flex flex-col z-10 shadow-2xl border-r border-[#E2E8F0] overflow-hidden">
            {/* DRAWER HEADER */}
            <div className="h-[56px] px-4 border-b border-[#E2E8F0] flex items-center justify-between bg-white flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <img src="/logo-uii.png" alt="Logo UII" className="w-7 h-7 object-contain" />
                <span className="font-bold text-xs text-[#22489E] font-display">Navigasi PMB UII</span>
              </div>
              <button
                onClick={() => setMobileDrawerOpen(false)}
                className="p-2 rounded-xl bg-[#F8FAFC] hover:bg-[#EFEEF1] border border-[#E2E8F0] text-slate-500"
              >
                <X className="w-5 h-5 text-[#22489E]" />
              </button>
            </div>

            {/* DRAWER BODY */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              <div>
                <h3 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3 flex items-center gap-1.5 font-display">
                  <Filter className="w-3.5 h-3.5 text-[#22489E]" /> Modul Akademik
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  {academicModules.map((mod, idx) => {
                    const IconComp = mod.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          setMobileDrawerOpen(false);
                          handleModuleClick(mod);
                        }}
                        className="p-2.5 bg-white hover:bg-[#EFEEF1] rounded-xl border border-[#E2E8F0] text-left text-xs transition-all flex flex-col justify-between"
                      >
                        <span className="font-bold text-[11px] flex items-center gap-1.5 font-display text-[#22489E] truncate">
                          <IconComp className="w-3.5 h-3.5 flex-shrink-0 text-[#22489E]" />
                          <span className="truncate">{mod.name}</span>
                        </span>
                        <span className="text-[10px] text-slate-500 truncate mt-1">{mod.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* MASTER KNOWLEDGE .MD */}
              <div className="pt-4 border-t border-[#E2E8F0]">
                <h3 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3 flex items-center gap-1.5 font-display">
                  <FileCode className="w-3.5 h-3.5 text-[#22489E]" /> Master .md Utuh
                </h3>
                <div className="space-y-1.5">
                  {masterKnowledgeDocs.map((doc, idx) => {
                    const DocIcon = doc.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          setMobileDrawerOpen(false);
                          handleFetchFullMd(doc.mod);
                        }}
                        className="w-full p-2 bg-white hover:bg-[#EFEEF1] rounded-xl border border-[#E2E8F0] text-left text-xs flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <DocIcon className="w-3.5 h-3.5 text-[#22489E] shrink-0" />
                          <span className="truncate text-slate-700 font-medium">{doc.title}</span>
                        </div>
                        <BookMarked className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* PDF & DOCX HUB */}
              <div className="pt-4 border-t border-[#E2E8F0]">
                <button
                  onClick={() => {
                    setMobileDrawerOpen(false);
                    handleOpenOfficialDocsHub();
                  }}
                  className="w-full p-2.5 bg-white hover:bg-[#EFEEF1] rounded-xl border border-[#E2E8F0] text-[#22489E] font-bold text-xs flex items-center justify-between"
                >
                  <span className="flex items-center gap-2 truncate font-display">
                    <FolderOpen className="w-4 h-4 text-[#22489E]" /> Pusat Berkas PDF & Word
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MAIN CHAT CANVAS (PURE WHITE BACKGROUND #FFFFFF) */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-white relative pb-44">
        {/* MOBILE STICKY TOPBAR WITH 2-LINE HAMBURGER BUTTON */}
        <div className="md:hidden flex items-center justify-between px-4 py-2.5 border-b border-[#E2E8F0] bg-white sticky top-0 z-30 shadow-2xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileDrawerOpen(true)}
              className="p-2 rounded-xl bg-[#F8FAFC] hover:bg-[#EFEEF1] border border-[#E2E8F0] text-[#22489E] flex items-center justify-center shadow-2xs"
              title="Buka Navigasi UII"
            >
              {/* 2-LINE HAMBURGER ICON */}
              <svg className="w-5 h-5 text-[#22489E]" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 8h16M4 16h16" />
              </svg>
            </button>
            <div className="flex items-center gap-2">
              <img src="/logo-uii.png" alt="Logo UII" className="w-6 h-6 object-contain" />
              <span className="font-bold text-xs text-[#22489E] font-display">PMB UII AI Assistant</span>
            </div>
          </div>
        </div>

        {/* MESSAGES CONTAINER */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6 w-full">
          <div className="max-w-3xl mx-auto space-y-4 sm:space-y-5">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3.5 ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.sender === 'ai' && (
                  <div className="w-9 h-9 rounded-xl bg-[#22489E] text-white flex items-center justify-center flex-shrink-0 shadow-xs font-bold font-display">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}

                {/* USER BUBBLE CONTAINER WITH ACTION BUTTONS OUTSIDE */}
                {msg.sender === 'user' ? (
                  <div className="flex flex-col items-end max-w-[85%] sm:max-w-[88%]">
                    <div className="rounded-2xl rounded-tr-none p-4 sm:p-5 shadow-xs border bg-[#F1F5F9] border-[#CBD5E1] text-[#0F172A] w-full font-sans font-medium">
                      {editingMessageId === msg.id ? (
                        <div className="space-y-3">
                          <textarea
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            className="w-full bg-white border border-[#22489E] rounded-xl p-3 text-xs text-[#0F172A] font-sans focus:outline-none focus:ring-2 focus:ring-[#22489E]/20"
                            rows={3}
                          />
                          <div className="flex items-center justify-end gap-2 text-xs font-display">
                            <button
                              onClick={() => setEditingMessageId(null)}
                              className="px-3 py-1.5 rounded-lg border border-[#E2E8F0] text-slate-600 font-semibold hover:bg-white"
                            >
                              Batal
                            </button>
                            <button
                              onClick={() => handleEditSave(msg.id, editingText)}
                              className="px-3.5 py-1.5 rounded-lg bg-[#22489E] text-white font-bold hover:bg-[#1E3A8A]"
                            >
                              Simpan & Kirim Ulang
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="markdown-body-light">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                        </div>
                      )}
                    </div>

                    {/* ACTION BUTTONS OUTSIDE USER BUBBLE */}
                    {editingMessageId !== msg.id && (
                      <div className="mt-1.5 flex items-center justify-end gap-2 text-[11px] text-slate-500 font-display">
                        <button
                          onClick={() => handleCopyPrompt(msg.id, msg.text)}
                          className="px-2 py-0.5 rounded-lg hover:bg-[#EFEEF1] text-slate-500 hover:text-[#22489E] flex items-center gap-1 transition-all duration-150"
                          title="Salin Perintah"
                        >
                          {copiedMsgId === msg.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-[#059669]" />
                              <span className="text-[#059669] font-bold">Tersalin</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5 text-slate-500" />
                              <span>Salin</span>
                            </>
                          )}
                        </button>

                        <button
                          onClick={() => {
                            setEditingMessageId(msg.id);
                            setEditingText(msg.text);
                          }}
                          className="px-2 py-0.5 rounded-lg hover:bg-[#EFEEF1] text-slate-500 hover:text-[#22489E] flex items-center gap-1 transition-all duration-150"
                          title="Edit Perintah ini"
                        >
                          <Pencil className="w-3.5 h-3.5 text-slate-500" />
                          <span>Edit Perintah</span>
                        </button>

                        <span className="text-[10px] text-slate-400 font-mono ml-1">
                          {msg.timestamp}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  /* AI MESSAGE CONTAINER (BOUNDED BETWEEN AI AVATAR & USER AVATAR COLUMN) */
                  <div className="flex flex-col items-start max-w-[85%] sm:max-w-[88%] w-full">
                    {/* AI CARD BUBBLE CONTAINER (COMPACT w-auto DURING LOADING, FULL w-full WHEN STREAMING) */}
                    <div className={`rounded-2xl rounded-tl-none shadow-xs border bg-white border-[#E2E8F0] text-[#0F172A] transition-all duration-200 ${
                      !msg.text || msg.text.trim() === '' ? 'p-3.5 px-5 w-auto inline-block' : 'p-5 sm:p-6 w-full'
                    }`}>
                      {/* IF MESSAGE IS STILL LOADING (EMPTY TEXT), SHOW IN-BUBBLE 3-DOT ANIMATION */}
                      {!msg.text || msg.text.trim() === '' ? (
                        <div className="flex items-center py-1 px-1">
                          <div className="flex space-x-2 items-center">
                            <span className="w-2.5 h-2.5 bg-[#22489E] rounded-full animate-bounce [animation-duration:0.8s]"></span>
                            <span className="w-2.5 h-2.5 bg-[#3B82F6] rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.2s]"></span>
                            <span className="w-2.5 h-2.5 bg-[#60A5FA] rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.4s]"></span>
                          </div>
                        </div>
                      ) : (
                        <>
                          {/* CRAG METADATA BADGE (HIDDEN FOR ERROR / SYSTEM MESSAGES) */}
                          {msg.meta && !isSystemOrErrorMessage(msg.text) && (
                            <div className="mb-2 pb-2 border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-2 text-xs">
                              {renderBadge(msg.meta.decisionPath)}
                              <span className="text-[11px] text-slate-400 font-mono">
                                Latency: {msg.meta.latencyMs} ms
                              </span>
                            </div>
                          )}

                          <div className="markdown-body-light">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                a: ({ node, ...props }) => (
                                  <a
                                    {...props}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 font-semibold text-[#22489E] bg-[#F1F5F9] hover:bg-[#E2E8F0] px-2 py-0.5 rounded-md border border-[#CBD5E1] hover:border-[#94A3B8] transition-all duration-150 cursor-pointer text-xs no-underline my-0.5 shadow-2xs"
                                  />
                                )
                              }}
                            >
                              {msg.text}
                            </ReactMarkdown>
                          </div>

                          {/* CITATIONS ACCORDION (HIDDEN FOR ERROR / SYSTEM MESSAGES) */}
                          {msg.meta && msg.meta.citations && msg.meta.citations.length > 0 && !isSystemOrErrorMessage(msg.text) && (
                            <div className="mt-4 border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
                              <details className="group">
                                <summary className="flex justify-between items-center text-xs font-semibold cursor-pointer list-none p-3 bg-[#F8FAFC] hover:bg-[#EFEEF1] transition-colors duration-200 font-display">
                                  <span className="text-[#22489E] font-bold flex items-center gap-2">
                                    <Info className="w-4 h-4 text-[#22489E]" />
                                    Sitasi Dokumen Terkait ({msg.meta.citations.length} Referensi)
                                  </span>
                                  <span className="transition-transform duration-200 group-open:rotate-180 text-slate-400">
                                    <ChevronDown className="w-4 h-4" />
                                  </span>
                                </summary>

                                <div className="p-3 border-t border-[#E2E8F0] bg-white flex flex-col gap-2.5">
                                  {msg.meta.citations.map((cit, cIdx) => (
                                    <div key={cIdx} className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                                      {/* LEFT COLUMN: TITLE & DOC ID */}
                                      <div className="truncate flex-1">
                                        <span className="font-bold text-[#0F172A] text-xs block truncate font-display">
                                          [{cit.module}] {cit.section_title}
                                        </span>
                                        <span className="text-[11px] text-slate-400 font-mono mt-0.5 block">
                                          Doc ID: {cit.doc_id}
                                        </span>
                                      </div>

                                      {/* RIGHT COLUMN: ACTION BUTTONS & SCORE BADGE ANCHORED AT FAR RIGHT */}
                                      <div className="flex items-center gap-2 shrink-0">
                                        <button
                                          onClick={() => setPreviewDoc(cit)}
                                          className="h-9 px-3 border border-[#E2E8F0] rounded-xl text-xs font-semibold text-[#0F172A] hover:bg-white transition-all duration-200 font-display flex items-center gap-1.5"
                                        >
                                          <Eye className="w-3.5 h-3.5 text-[#22489E]" />
                                          <span>Preview Section</span>
                                        </button>
                                        <button
                                          onClick={() => handleFetchFullMd(cit.module, cit.section_title)}
                                          className="h-9 px-3 bg-[#22489E] hover:bg-[#1E3A8A] text-white rounded-xl text-xs font-semibold transition-all duration-200 font-display flex items-center gap-1.5"
                                        >
                                          <BookMarked className="w-3.5 h-3.5" />
                                          <span>Baca Master .md Utuh</span>
                                        </button>
                                        <span className="text-[11px] font-bold text-[#059669] bg-[#D1FAE5] px-2.5 py-1.5 rounded-xl border border-[#059669]/20 font-display shadow-2xs shrink-0">
                                          Score: {cit.relevance_score}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </details>
                            </div>
                          )}

                          {/* SINGLE CONVERSATIONAL FOLLOW-UP QUESTION PILL (HIDDEN FOR ERROR / SYSTEM MESSAGES) */}
                          {msg.meta && msg.meta.suggestedFollowup && !isSystemOrErrorMessage(msg.text) && (
                            <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center gap-2 max-w-full overflow-hidden">
                              <span className="text-[11px] font-bold text-[#22489E] flex items-center gap-1 font-display shrink-0 whitespace-nowrap">
                                <Sparkles className="w-3.5 h-3.5 text-[#22489E]" /> Pertanyaan Lanjutan:
                              </span>
                              <button
                                onClick={() => handleSend(msg.meta.suggestedFollowup)}
                                className="text-xs font-semibold text-[#22489E] bg-[#EFEEF1] hover:bg-[#22489E] hover:text-white px-3 py-1.5 rounded-xl border border-[#E2E8F0] hover:border-[#22489E] transition-all duration-200 text-left font-display flex items-center justify-between gap-2 shadow-2xs group flex-1 min-w-0 max-w-full overflow-hidden"
                              >
                                <span className="truncate flex-1 min-w-0">{msg.meta.suggestedFollowup}</span>
                                <ArrowRight className="w-3.5 h-3.5 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* RIGHT-ALIGNED ACTION BAR UNDER AI CARD (HIDDEN FOR WELCOME & ERROR MESSAGES) */}
                    {!msg.isWelcome && msg.id !== 1 && msg.text && msg.text.trim() !== '' && !isSystemOrErrorMessage(msg.text) && (
                      <div className="mt-1.5 flex items-center justify-end gap-2 text-[11px] text-slate-500 font-display w-full">
                        <button
                          onClick={() => handleCopyPrompt(msg.id, msg.text)}
                          className="px-2 py-0.5 rounded-lg hover:bg-[#EFEEF1] text-slate-500 hover:text-[#22489E] flex items-center gap-1 transition-all duration-150"
                          title="Salin Jawaban AI ini"
                        >
                          {copiedMsgId === msg.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-[#059669]" />
                              <span className="text-[#059669] font-bold">Tersalin</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Salin Jawaban</span>
                            </>
                          )}
                        </button>

                        <button
                          onClick={() => handleRetryResponse(msg.id)}
                          className="px-2 py-0.5 rounded-lg hover:bg-[#EFEEF1] text-slate-500 hover:text-[#22489E] flex items-center gap-1 transition-all duration-150"
                          title="Ulangi Respon (Regenerate)"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Ulangi Respon</span>
                        </button>

                        <span className="text-[10px] text-slate-400 font-mono ml-1">
                          {msg.timestamp}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* USER PROFILE AVATAR WITH SOFT PERIWINKLE UII COLOR */}
                {msg.sender === 'user' && (
                  <div className="w-9 h-9 rounded-xl bg-[#BDCDEA] text-[#22489E] border border-[#BDCDEA]/50 flex items-center justify-center flex-shrink-0 shadow-xs font-bold text-xs">
                    <User className="w-4.5 h-4.5 text-[#22489E]" />
                  </div>
                )}
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* DYNAMIC RESPONSIVE CHAT INPUT CONTAINER */}
        <div className={`fixed bottom-0 right-0 bg-white/95 backdrop-blur-md border-t border-[#E2E8F0] p-4 z-30 transition-all duration-200 ${
          sidebarOpen ? 'left-0 md:left-[320px]' : 'left-0 md:left-[64px]'
        }`}>
          <div className="max-w-3xl mx-auto space-y-3">
            {/* QUICK CHIP BUTTONS */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar text-xs">
              {quickTopics.map((topic, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(topic.query)}
                  disabled={loading}
                  className="whitespace-nowrap px-4 py-1.5 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] hover:bg-[#EFEEF1] hover:border-[#22489E] text-xs font-semibold font-display text-[#0F172A] transition-all duration-200 disabled:opacity-50"
                >
                  {topic.label}
                </button>
              ))}
            </div>

            {/* INPUT PILL BAR WITH SEND OR STOP EXECUTION BUTTON */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="relative flex items-center"
            >
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ketik pertanyaan seputar pendaftaran, biaya, atau beasiswa UII..."
                disabled={loading}
                className="w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-3xl px-6 py-4 focus:outline-none focus:border-[#22489E] focus:ring-2 focus:ring-[#22489E]/20 transition-all duration-200 font-sans text-sm text-[#0F172A] placeholder-slate-400 shadow-xs disabled:opacity-50"
              />

              {loading ? (
                <button
                  type="button"
                  onClick={handleStopExecution}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center bg-slate-800 hover:bg-[#E11D48] text-white rounded-full transition-all duration-200 active:scale-95 shadow-xs"
                  title="Hentikan Generasi Jawaban (Stop)"
                >
                  <Square className="w-4 h-4 fill-white" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!query.trim()}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center bg-[#22489E] text-white rounded-full hover:bg-[#1E3A8A] transition-all duration-200 active:scale-95 shadow-xs disabled:opacity-30"
                  title="Kirim Pertanyaan"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </form>
          </div>
        </div>
      </main>

      {/* MODAL 1: SECTION CHUNK PREVIEW */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#22489E] text-white flex items-center justify-center font-bold">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#22489E] bg-[#EFEEF1] px-2.5 py-0.5 rounded-full border border-[#BDCDEA] font-display">
                    [{previewDoc.module}] {previewDoc.doc_id}
                  </span>
                  <h3 className="text-sm font-bold text-[#0F172A] font-display mt-0.5">
                    {previewDoc.section_title}
                  </h3>
                </div>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-[#EFEEF1] transition-all duration-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 text-xs text-slate-700 space-y-3 bg-white">
              <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] flex items-center justify-between text-[11px]">
                <span>Skor Relevansi Vektor Semantik:</span>
                <strong className="text-[#059669] font-bold bg-[#D1FAE5] px-2.5 py-0.5 rounded-full border border-[#059669]/30 font-display">
                  {previewDoc.relevance_score}
                </strong>
              </div>

              <div className="markdown-body-light pt-2">
                <h4 className="font-bold text-xs text-[#0F172A] mb-2 font-display">Teks Section Dokumen Terstruktur:</h4>
                <div className="p-4 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-xs font-sans leading-relaxed text-[#0F172A]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {cleanPreviewText(previewDoc.raw_text)}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between">
              <button
                onClick={() => {
                  setPreviewDoc(null);
                  handleFetchFullMd(previewDoc.module, previewDoc.section_title);
                }}
                className="px-4 py-2 rounded-xl bg-[#22489E] text-white text-xs font-bold hover:bg-[#1E3A8A] transition-all duration-200 font-display flex items-center gap-1.5"
              >
                <BookMarked className="w-4 h-4" />
                <span>Baca File Master .md Utuh</span>
              </button>

              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-2 rounded-xl border border-[#E2E8F0] text-slate-700 text-xs font-bold hover:bg-white transition-all duration-200 font-display"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: INTERACTIVE MARKDOWN E-BOOK READER WITH SMART YELLOW HIGHLIGHTING */}
      {fullMdDoc && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* READER E-BOOK HEADER WITH REAL-TIME SEARCH BAR */}
            <div className="p-4 border-b border-[#E2E8F0] bg-[#22489E] text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white text-[#22489E] flex items-center justify-center font-bold font-display">
                  <BookMarked className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#22489E] bg-[#BDCDEA] px-2.5 py-0.5 rounded-full font-display">
                    MARKDOWN E-BOOK READER (.MD)
                  </span>
                  <h3 className="text-sm sm:text-base font-bold font-display mt-0.5">
                    {fullMdDoc.filename} ({fullMdDoc.total_chars.toLocaleString()} Karakter)
                  </h3>
                </div>
              </div>

              {/* REAL-TIME FUNCTIONING SEARCH BAR */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={mdSearchQuery}
                    onChange={(e) => setMdSearchQuery(e.target.value)}
                    placeholder="Cari kata di dokumen..."
                    className="pl-9 pr-8 py-1.5 bg-white/10 text-white placeholder-white/60 text-xs rounded-xl border border-white/20 focus:outline-none focus:bg-white/20 transition-all font-sans"
                  />
                  {mdSearchQuery && (
                    <button
                      onClick={() => setMdSearchQuery('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/60 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <button
                  onClick={() => setFullMdDoc(null)}
                  className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-all duration-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* E-BOOK SPLIT BODY: TABLE OF CONTENTS (LEFT) & CONTENT (RIGHT) */}
            <div className="flex-1 flex overflow-hidden bg-[#F8FAFC]">
              {/* TABLE OF CONTENTS SIDE PANEL */}
              <div className="w-64 border-r border-[#E2E8F0] bg-white p-4 hidden md:flex flex-col flex-shrink-0 text-xs overflow-y-auto">
                <h4 className="font-bold text-slate-500 uppercase tracking-wider text-[11px] mb-3 flex items-center gap-1.5 font-display">
                  <ListFilter className="w-4 h-4 text-[#22489E]" /> Daftar Isi Bab (.md)
                </h4>
                <div className="space-y-1.5">
                  {extractTocHeadings(fullMdDoc.content, mdSearchQuery).map((head, hIdx) => (
                    <div
                      key={hIdx}
                      onClick={() => setMdSearchQuery(head.title)}
                      className={`p-2 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 ${
                        head.level === 1
                          ? 'bg-[#EFEEF1] text-[#22489E] font-bold font-display'
                          : 'text-slate-600 hover:bg-[#F8FAFC] pl-4 font-sans'
                      }`}
                    >
                      {head.title}
                    </div>
                  ))}
                </div>
              </div>

              {/* MAIN CONTENT READER CANVAS WITH AUTOMATIC REAL-TIME YELLOW HIGHLIGHTING */}
              <div className="flex-1 overflow-y-auto p-6 sm:p-8">
                <div className="max-w-3xl mx-auto bg-white p-6 sm:p-10 rounded-2xl border border-[#E2E8F0] shadow-xs markdown-body-light overflow-x-auto">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={highlightMarkdownComponents(mdSearchQuery)}
                  >
                    {fullMdDoc.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            {/* E-BOOK FOOTER */}
            <div className="p-4 border-t border-[#E2E8F0] bg-white flex items-center justify-between text-xs font-display">
              <span className="text-slate-500">
                {mdSearchQuery ? (
                  <span className="font-semibold text-[#22489E]">
                    Menampilkan penyorotan warna kuning untuk kata kunci: "{mdSearchQuery}"
                  </span>
                ) : (
                  'Layanan Informasi Resmi PMB Universitas Islam Indonesia 2026'
                )}
              </span>
              <button
                onClick={() => setFullMdDoc(null)}
                className="px-4 py-2 rounded-xl bg-[#22489E] text-white font-bold hover:bg-[#1E3A8A] transition-all duration-200"
              >
                Selesai Membaca
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: PUSAT DOKUMEN RESMI PDF & WORD HUB */}
      {officialDocsModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* HEADER WITH REAL-TIME SEARCH BAR */}
            <div className="p-4 border-b border-[#E2E8F0] bg-[#22489E] text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white text-[#22489E] flex items-center justify-center font-bold font-display">
                  <FolderOpen className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold font-display">
                    Pusat Dokumen & Brosur Resmi UII (PDF / DOCX)
                  </h3>
                  <p className="text-xs text-[#BDCDEA]">
                    Daftar lengkap berkas panduan, form pendaftaran, dan brosur resmi PMB UII
                  </p>
                </div>
              </div>

              {/* SEARCH BAR */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={officialDocsSearchQuery}
                    onChange={(e) => setOfficialDocsSearchQuery(e.target.value)}
                    placeholder="Cari brosur/dokumen..."
                    className="pl-9 pr-3 py-1.5 bg-white/10 text-white placeholder-white/60 text-xs rounded-xl border border-white/20 focus:outline-none focus:bg-white/20 transition-all font-sans"
                  />
                </div>
                <button
                  onClick={() => setOfficialDocsModalOpen(false)}
                  className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-all duration-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* DOKUMEN GRID */}
            <div className="flex-1 overflow-y-auto p-6 bg-[#F8FAFC] space-y-4">
              {loadingOfficialDocs ? (
                <div className="p-8 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin text-[#22489E]" />
                  <span>Memuat daftar dokumen resmi UII...</span>
                </div>
              ) : filteredOfficialDocs.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs font-display">
                  Tidak ada berkas resmi yang cocok dengan pencarian "{officialDocsSearchQuery}".
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {filteredOfficialDocs.map((doc, idx) => (
                    <div key={idx} className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs flex flex-col justify-between hover:border-[#22489E] transition-all duration-200">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 truncate">
                          <div className={`p-2.5 rounded-xl flex-shrink-0 ${
                            doc.type === 'PDF' ? 'bg-[#FFE4E6] text-[#E11D48]' : 'bg-[#EFEEF1] text-[#22489E]'
                          }`}>
                            <FileText className="w-5 h-5" />
                          </div>
                          <div className="truncate">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-display">
                              {doc.category}
                            </span>
                            <h4 className="font-bold text-xs text-[#0F172A] truncate mt-0.5 font-display">
                              {doc.title}
                            </h4>
                            <span className="text-[11px] text-slate-500 block mt-1">
                              Format: {doc.type} • Ukuran: {doc.size}
                            </span>
                          </div>
                        </div>

                        {/* EYE HOVER TRANSITION BUTTON FOR INLINE PDF PREVIEW */}
                        <button
                          onClick={() => setPdfPreviewModalDoc(doc)}
                          className="w-9 h-9 rounded-xl bg-[#F8FAFC] hover:bg-[#22489E] hover:text-white border border-[#E2E8F0] hover:border-[#22489E] text-slate-500 transition-all duration-200 flex items-center justify-center flex-shrink-0 group relative overflow-hidden"
                          title="Preview PDF Langsung (Inline Viewer)"
                        >
                          <EyeOff className="w-4.5 h-4.5 group-hover:opacity-0 group-hover:scale-90 transition-all duration-200 absolute" />
                          <Eye className="w-4.5 h-4.5 opacity-0 group-hover:opacity-100 group-hover:scale-100 transition-all duration-200" />
                        </button>
                      </div>

                      {/* DIRECT DOWNLOAD BUTTON */}
                      <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex items-center justify-between">
                        <a
                          href={`${API_BASE_URL}${doc.download_url}`}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="w-full px-3 py-2 rounded-xl bg-[#22489E] hover:bg-[#1E3A8A] text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all duration-200 font-display"
                        >
                          <Download className="w-4 h-4" />
                          <span>Download ({doc.type})</span>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="p-4 border-t border-[#E2E8F0] bg-white flex items-center justify-between text-xs font-display">
              <span className="text-slate-500">Total {filteredOfficialDocs.length} Berkas Resmi Tersedia</span>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: INLINE PDF PREVIEW VIEWER MODAL */}
      {pdfPreviewModalDoc && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-[#E2E8F0] bg-[#22489E] text-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white text-[#22489E] flex items-center justify-center font-bold font-display">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#22489E] bg-[#BDCDEA] px-2.5 py-0.5 rounded-full font-display">
                    INLINE PDF PREVIEW VIEWER
                  </span>
                  <h3 className="text-sm sm:text-base font-bold font-display mt-0.5">
                    {pdfPreviewModalDoc.title} ({pdfPreviewModalDoc.type})
                  </h3>
                </div>
              </div>
              <button
                onClick={() => setPdfPreviewModalDoc(null)}
                className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-all duration-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* IFRAME PDF VIEWER CANVAS */}
            <div className="flex-1 bg-[#F8FAFC] p-4 flex flex-col">
              <iframe
                src={`${API_BASE_URL}${pdfPreviewModalDoc.download_url}`}
                title={pdfPreviewModalDoc.title}
                className="w-full flex-1 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] shadow-xs min-h-[550px]"
              />
            </div>

            <div className="p-4 border-t border-[#E2E8F0] bg-white flex items-center justify-between text-xs font-display">
              <a
                href={`${API_BASE_URL}${pdfPreviewModalDoc.download_url}`}
                download
                className="px-4 py-2 rounded-xl bg-[#22489E] text-white font-bold hover:bg-[#1E3A8A] transition-all duration-200 flex items-center gap-1.5"
              >
                <Download className="w-4 h-4" />
                <span>Unduh Berkas Ini</span>
              </a>
              <button
                onClick={() => setPdfPreviewModalDoc(null)}
                className="px-4 py-2 rounded-xl bg-[#EFEEF1] text-[#0F172A] font-bold hover:bg-[#E2E8F0] transition-all duration-200"
              >
                Selesai Membaca
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: SYSTEM SETTINGS MODAL */}
      {settingsModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-[#E2E8F0] bg-[#22489E] text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-white text-[#22489E] flex items-center justify-center font-bold">
                  <Settings className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-display">Pengaturan Sistem AI & RAG Engine</h3>
                  <p className="text-[11px] text-[#BDCDEA]">Konfigurasi parameter retrieval dan visualisasi</p>
                </div>
              </div>
              <button
                onClick={() => setSettingsModalOpen(false)}
                className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 text-xs text-[#0F172A]">
              {/* TOP K RETRIEVAL CONFIG */}
              <div>
                <label className="font-bold text-xs block mb-1.5 font-display text-[#0F172A]">
                  Kedalaman Pencarian Vektor (Top-K Chunks):
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[3, 5, 8].map((k) => (
                    <button
                      key={k}
                      onClick={() => setTopKConfig(k)}
                      className={`p-2.5 rounded-xl border text-center font-bold font-display transition-all ${
                        topKConfig === k
                          ? 'bg-[#22489E] text-white border-[#22489E] shadow-xs'
                          : 'bg-[#F8FAFC] hover:bg-[#EFEEF1] text-slate-700 border-[#E2E8F0]'
                      }`}
                    >
                      Top-{k} Dokumen
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5">
                  Menentukan berapa banyak fragmen dokumen yang ditarik IndoBERT & BM25 ke Gemini.
                </p>
              </div>

              {/* METADATA BADGES TOGGLE */}
              <div className="pt-4 border-t border-[#E2E8F0] flex items-center justify-between">
                <div>
                  <span className="font-bold text-xs block font-display">Tampilkan Badge Metrik (CRAG Status):</span>
                  <span className="text-[11px] text-slate-400">Direct Pass, Latency, dan Score Relevansi</span>
                </div>
                <button
                  onClick={() => setShowMetadataBadges(!showMetadataBadges)}
                  className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ${
                    showMetadataBadges ? 'bg-[#059669]' : 'bg-slate-300'
                  }`}
                >
                  <div className={`w-4 h-4 rounded-full bg-white transition-transform duration-200 ${
                    showMetadataBadges ? 'translate-x-6' : 'translate-x-0'
                  }`} />
                </button>
              </div>

              {/* AI MODEL SPECS */}
              <div className="p-3.5 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] space-y-1">
                <span className="font-bold text-[11px] text-[#22489E] font-display block">Model AI Aktif:</span>
                <p className="text-[11px] text-slate-600 font-mono">
                  • LLM Generator: Google Gemini 3.6 Flash<br/>
                  • Embeddings: IndoBERT Semantic Vector (768-d)<br/>
                  • RAG Engine: Corrective RAG (CRAG) + HyDE
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-[#E2E8F0] bg-[#F8FAFC] flex justify-end font-display">
              <button
                onClick={() => setSettingsModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#22489E] text-white text-xs font-bold hover:bg-[#1E3A8A]"
              >
                Simpan Pengaturan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: HELP & CHATBOT INFORMATION MODAL */}
      {helpModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl max-w-xl w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-[#E2E8F0] bg-[#22489E] text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-white text-[#22489E] flex items-center justify-center font-bold">
                  <HelpCircle className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-display">Pusat Bantuan & Deskripsi Chatbot PMB UII</h3>
                  <p className="text-[11px] text-[#BDCDEA]">Informasi arsitektur dan panduan penggunaan</p>
                </div>
              </div>
              <button
                onClick={() => setHelpModalOpen(false)}
                className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs text-slate-700 max-h-[75vh] overflow-y-auto leading-relaxed">
              <div className="p-4 bg-[#EFEEF1] rounded-2xl border border-[#BDCDEA]/40 text-[#0F172A]">
                <h4 className="font-bold text-xs text-[#22489E] font-display mb-1">
                  Apa itu Asisten Akademik PMB UII AI 2026?
                </h4>
                <p>
                  Sistem ini adalah asisten kecerdasan buatan enterprise terintegrasi yang dirancang untuk menjawab seluruh pertanyaan calon mahasiswa baru Universitas Islam Indonesia (UII) tahun akademik 2026/2027 secara presisi dan faktual.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-xs text-[#0F172A] font-display mb-1.5">
                  Cakupan Informasi PMB UII:
                </h4>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  <li><strong>Biaya & SPP</strong>: Rincian tarif Catur Darma, SPP Tetap, dan SPP Variabel 8 Fakultas UII.</li>
                  <li><strong>Jalur Seleksi</strong>: Syarat & alur Jalur Rapor, CBT Umum/Kedokteran, UTBK, dan Beasiswa.</li>
                  <li><strong>Beasiswa</strong>: Beasiswa Hafiz Al-Qur'an (15 & 30 Juz), Beasiswa Santri, Juara, KIP Kuliah.</li>
                  <li><strong>Program Studi</strong>: Jenjang D3, D4, S1 Reguler & International Program (IP).</li>
                </ul>
              </div>

              <div>
                <h4 className="font-bold text-xs text-[#0F172A] font-display mb-1.5">
                  Fitur Utama Antarmuka:
                </h4>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  <li><strong>Sitasi Dokumen Terkait</strong>: Setiap jawaban dilengkapi sumber dokumen asli dan skor konfidensi.</li>
                  <li><strong>Edit & Salin Perintah</strong>: Anda dapat menyalin prompt atau mengedit pertanyaan kapan saja.</li>
                  <li><strong>Markdown E-Book Reader</strong>: Membaca dokumen `.md` utuh dengan penyorotan warna kuning otomatis.</li>
                </ul>
              </div>
            </div>

            <div className="p-4 border-t border-[#E2E8F0] bg-[#F8FAFC] flex justify-end font-display">
              <button
                onClick={() => setHelpModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#22489E] text-white text-xs font-bold hover:bg-[#1E3A8A]"
              >
                Tutup Pusat Bantuan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}