import { useState, useEffect, useRef } from 'react';
import { Mic, Activity, Lock, Sun, Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';

// Component: Pulse Visualizer (Twin Soul)
const TwinVisualizer = ({ active }) => {
  return (
    <div className="relative flex items-center justify-center w-64 h-64">
      {/* Core */}
      <motion.div
        animate={{ scale: active ? [1, 1.2, 1] : 1 }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
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

        {/* Center: The Twin */}
        <div className="flex flex-col items-center gap-6">
          <TwinVisualizer active={status === "Connected"} />
          <span className="text-2xl font-light tracking-[0.2em] uppercase glow-text">
            {twinState}
          </span>
        </div>

        {/* Right Panel: Transcript */}
        <div className="glass-panel w-80 h-96 p-4 flex flex-col gap-2 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-white/10 pb-2 mb-2">
            <Mic size={16} />
            <span className="text-xs uppercase opacity-70">Neural Log</span>
          </div>
          <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-2">
            {transcript.map((t, i) => (
              <div key={i} className={`text-sm ${t.role === 'user' ? 'text-right opacity-80' : 'text-left text-cyan-300'}`}>
                <p className="p-2 rounded bg-white/5 inline-block max-w-full break-words">
                  {t.text}
                </p>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </div>
        </div>

      </main>

    </div>
  );
}

export default App;
