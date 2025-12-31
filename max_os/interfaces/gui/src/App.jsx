import { useState, useEffect, useRef } from 'react';
import { Mic, Activity, Lock, Sun, Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';

// Component: Pulse Visualizer (Twin Soul)
const TwinVisualizer = ({ active, processing }) => {
  return (
    <div className="relative flex items-center justify-center w-64 h-64">
      {/* Core */}
      <motion.div
        animate={{
          scale: active ? (processing ? [1, 1.4, 1] : [1, 1.1, 1]) : 1,
          opacity: processing ? [0.4, 0.8, 0.4] : 0.5
        }}
        transition={{
          duration: processing ? 0.6 : 3,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="w-32 h-32 rounded-full bg-cyan-500 blur-xl opacity-50 absolute"
      />
      <div className="w-24 h-24 rounded-full bg-black border-2 border-cyan-400 z-10 flex items-center justify-center glass-panel">
        <Brain size={48} className="text-cyan-400" />
      </div>
      {/* Orbital Rings */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        className="w-48 h-48 rounded-full border border-dashed border-cyan-700 absolute opacity-30"
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        className="w-56 h-56 rounded-full border border-dotted border-purple-500 absolute opacity-30"
      />
    </div>
  );
};

function App() {
  const [brightness, setBrightness] = useState(100);
  const [socket, setSocket] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [status, setStatus] = useState("Offline");

  const [twinState, setTwinState] = useState("Frontman");
  const [processing, setProcessing] = useState(false);

  // Accessibility State
  const [settings, setSettings] = useState({
    gui_scale: 100,
    high_contrast: false
  });

  const transcriptEndRef = useRef(null);

  // WebSocket Connection
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      setStatus("Connected");
      console.log("Neural Link Connected");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    };

    ws.onclose = () => setStatus("Disconnected");
    setSocket(ws);

    return () => ws.close();
  }, []);

  // Scroll to bottom of transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const handleMessage = (msg) => {
    if (msg.type === "transcript") {
      setTranscript(prev => [...prev.slice(-10), msg.payload]); // Keep last 10
      if (msg.payload.role === 'assistant') {
        setProcessing(false);
      } else if (msg.payload.role === 'user') {
        setProcessing(true);
      }
    } else if (msg.type === "twin_state") {
      setTwinState(msg.payload);
    } else if (msg.type === "settings_update") {
      setSettings(prev => ({ ...prev, ...msg.payload }));
    }
  };

  const containerStyle = {
    filter: `brightness(${brightness}%) ${settings.high_contrast ? 'contrast(150%)' : ''}`,
    fontSize: `${settings.gui_scale}%`,
  };

  return (
    <div className="w-screen h-screen flex flex-col p-8 gap-6 transition-all duration-300 app-container" style={containerStyle}>

      {/* Top Bar */}
      <header className="flex justify-between items-center glass-panel p-4 h-16 w-full max-w-5xl mx-auto">
        <div className="flex items-center gap-4">
          <Activity size={20} className={status === "Connected" ? "text-green-400" : "text-red-500"} />
          <span className="font-mono text-sm tracking-widest uppercase">MaxOS V2.6 // {status}</span>
        </div>

        <div className="flex items-center gap-4">
          <Sun size={16} />
          <input
            type="range"
            min="10" max="100"
            value={brightness}
            onChange={(e) => setBrightness(e.target.value)}
            className="w-32 accent-cyan-500 cursor-pointer"
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center gap-12 w-full max-w-6xl mx-auto">

        {/* Left Panel: Status Grid */}
        <div className="flex flex-col gap-4 w-64">
          <div className="glass-panel p-4 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
            <span>Librarian</span>
          </div>
          <div className="glass-panel p-4 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
            <span>Scheduler</span>
          </div>
          <div className="glass-panel p-4 flex items-center gap-3">
            <Lock size={16} className="text-cyan-400" />
            <span>Watchman</span>
          </div>
        </div>


        {/* Center: The Twin soul */}
        <div className="flex flex-col items-center gap-6">
          <TwinVisualizer active={status === "Connected"} processing={processing} />
          <span className="text-2xl font-light tracking-[0.2em] uppercase glow-text">
            {twinState}
          </span>
        </div>


        {/* Right Panel: Transcript & Chat */}
        <div className="glass-panel w-96 h-[32rem] p-4 flex flex-col gap-2 overflow-hidden shadow-2xl border-cyan-500/20">
          <div className="flex justify-between items-center border-b border-white/10 pb-2 mb-2">
            <div className="flex items-center gap-2">
              <Mic size={16} className="text-cyan-400" />
              <span className="text-xs uppercase tracking-widest opacity-70">Neural Link</span>
            </div>
            <span className="text-[10px] font-mono opacity-40 uppercase">Encrypted</span>
          </div>

          <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-2 custom-scrollbar">
            {transcript.map((t, i) => (
              <motion.div
                initial={{ opacity: 0, x: t.role === 'user' ? 10 : -10 }}
                animate={{ opacity: 1, x: 0 }}
                key={i}
                className={`flex flex-col ${t.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className={`text-sm p-3 rounded-2xl max-w-[90%] break-words ${t.role === 'user'
                  ? 'bg-cyan-600/20 border border-cyan-500/30 rounded-tr-none'
                  : 'bg-purple-600/20 border border-purple-500/30 rounded-tl-none text-cyan-100'
                  }`}>
                  {t.text}
                </div>
                <span className="text-[9px] uppercase opacity-30 mt-1 px-1">{t.source || t.role}</span>
              </motion.div>
            ))}
            <div ref={transcriptEndRef} />
          </div>

          {/* Chat Input */}
          <div className="mt-2 flex gap-2 items-center bg-black/40 p-1 rounded-full border border-white/5 focus-within:border-cyan-500/50 transition-all">
            <input
              type="text"
              placeholder="Ask Max..."
              className="flex-1 bg-transparent border-none outline-none px-4 py-2 text-sm placeholder:opacity-30"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const text = e.target.value;
                  if (text.trim()) {
                    fetch('http://localhost:8000/command', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ text })
                    });
                    e.target.value = '';
                  }
                }
              }}
            />
            <button className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center hover:bg-cyan-500/40 transition-colors">
              <Activity size={14} className="text-cyan-400" />
            </button>
          </div>
        </div>

      </main>

    </div>
  );
}

export default App;
