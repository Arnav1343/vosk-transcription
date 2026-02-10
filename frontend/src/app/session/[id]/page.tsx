"use client"

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { mockSessions, Session } from '@/lib/mock-data';
import { WaveformTimeline } from '@/components/WaveformTimeline';
import { EvidencePanel } from '@/components/EvidencePanel';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Play,
  Pause,
  Search,
  Download,
  Tag,
  Filter,
  CheckCircle2,
  AlertCircle,
  Share2,
  MoreVertical,
  Volume2
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SessionPage() {
  const { id } = useParams();
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFlagIdx, setActiveFlagIdx] = useState<number | null>(null);
  const [aiFlags, setAiFlags] = useState<any[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const res = await fetch(`http://localhost:8000/session/${id}`);
        if (res.ok) {
          const data = await res.json();
          setSession(data);
          setAiFlags(data.aiFlags || []);
        } else {
          console.error("Session not found");
          // Optional: router.push('/'); // Don't redirect immediately to allow debugging
        }
      } catch (e) {
        console.error("Failed to fetch session", e);
      }
    };

    if (id) {
      fetchSession();
      // Optional: Poll for updates if status is processing
      const interval = setInterval(fetchSession, 3000);
      return () => clearInterval(interval);
    }
  }, [id, router]);

  const runAudit = async () => {
    // no-op now, as audit is run on upload
    alert("Audit is run automatically properly on upload!");
  };

  const audioRef = useRef<HTMLAudioElement>(null);

  const togglePlayback = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (audioRef.current.ended) {
        setIsPlaying(false);
      }
    }
  };

  const handleSeek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const filteredTranscript = session?.transcript.filter(t =>
    t.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.speaker.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!session) return <div className="flex h-screen items-center justify-center">Loading session data...</div>;

  return (
    <div className="flex flex-col h-screen bg-background">
      <audio
        ref={audioRef}
        src={session.audio_url}
        onTimeUpdate={handleTimeUpdate}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
      {/* Top Header */}
      <header className="h-16 border-b bg-card px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold text-foreground leading-none">{session.title}</h1>
            <p className="text-xs text-muted-foreground mt-1">{session.date} • {session.agent} vs {session.customer}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" className="gap-2">
            <Tag className="w-4 h-4" /> Tag
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="w-4 h-4" /> Export
          </Button>
          <Button size="sm" className="gap-2" onClick={runAudit} disabled={isAuditing}>
            {isAuditing ? 'Auditing...' : 'Run Audit'}
          </Button>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane: Audio & Timeline */}
        <div className="w-1/2 flex flex-col p-6 gap-6 border-r overflow-y-auto">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Call Playback</h2>
              <Badge variant={session.status === 'Flagged' ? 'destructive' : 'default'} className="rounded-md">
                {session.status}
              </Badge>
            </div>

            <WaveformTimeline
              duration={session.duration}
              currentTime={currentTime}
              onSeek={handleSeek}
              flags={aiFlags.map(f => ({ start: f.start, end: f.end, type: f.type }))}
            />

            <div className="flex items-center justify-center gap-6 py-2">
              <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-foreground">
                <Volume2 className="w-5 h-5" />
              </Button>
              <Button size="icon" className="h-14 w-14 rounded-full shadow-lg transition-transform active:scale-95" onClick={togglePlayback}>
                {isPlaying ? <Pause className="w-7 h-7 fill-current" /> : <Play className="w-7 h-7 fill-current ml-1" />}
              </Button>
              <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-foreground">
                <Share2 className="w-5 h-5" />
              </Button>
            </div>
          </div>

          {/* Insights Section */}
          <div className="space-y-4 pt-6 border-t">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Audit Evidence</h2>
            {aiFlags.length > 0 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  {aiFlags.map((flag, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveFlagIdx(idx)}
                      className={cn(
                        "text-left p-3 rounded-lg border transition-all hover:bg-muted group relative",
                        activeFlagIdx === idx ? "border-primary ring-1 ring-primary bg-primary/5 shadow-sm" : "border-border"
                      )}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-xs font-bold text-destructive flex items-center gap-1.5">
                          <AlertCircle className="w-3.5 h-3.5" /> {flag.type}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {Math.floor(flag.start / 60)}:{(flag.start % 60).toString().padStart(2, '0')}
                        </span>
                      </div>
                      <p className="text-xs text-foreground/80 line-clamp-2 italic">"{flag.evidence}"</p>
                    </button>
                  ))}
                </div>

                {activeFlagIdx !== null && (
                  <EvidencePanel
                    flag={aiFlags[activeFlagIdx]}
                    transcriptSegment={aiFlags[activeFlagIdx].evidence}
                  />
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center bg-card rounded-xl border border-dashed">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                  <CheckCircle2 className="w-6 h-6 text-muted-foreground" />
                </div>
                <p className="text-sm font-medium text-foreground">No flags detected yet</p>
                <p className="text-xs text-muted-foreground mt-1 px-8">Run the automated compliance audit to scan this call transcript for potential issues.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Transcript */}
        <div className="w-1/2 flex flex-col">
          <div className="p-4 border-b flex items-center gap-3 shrink-0 bg-card">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search transcript..."
                className="pl-9 bg-background h-10 text-sm border-none shadow-none ring-1 ring-border focus-visible:ring-primary"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button variant="outline" size="icon" className="h-10 w-10 shrink-0">
              <Filter className="w-4 h-4" />
            </Button>
          </div>

          <ScrollArea className="flex-1 transcript-scroll">
            <div className="p-6 space-y-6">
              {filteredTranscript?.map((segment) => {
                const isActive = currentTime >= segment.startTime && currentTime <= segment.endTime;
                const isFlagged = aiFlags.some(f =>
                  (segment.startTime >= f.start && segment.startTime <= f.end) ||
                  (segment.endTime >= f.start && segment.endTime <= f.end) ||
                  (f.start >= segment.startTime && f.end <= segment.endTime)
                );

                return (
                  <div
                    key={segment.id}
                    className={cn(
                      "group flex flex-col gap-2 p-3 rounded-xl transition-all duration-300",
                      isActive ? "bg-accent/10 border-l-4 border-accent" : "border-l-4 border-transparent",
                      isFlagged ? "bg-destructive/5 ring-1 ring-destructive/10" : ""
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="secondary"
                          className={cn(
                            "text-[10px] uppercase font-bold",
                            segment.speaker === 'Agent' ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                          )}
                        >
                          {segment.speaker}
                        </Badge>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {Math.floor(segment.startTime / 60)}:{(segment.startTime % 60).toString().padStart(2, '0')}
                        </span>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <MoreVertical className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                    <p className={cn(
                      "text-sm leading-relaxed",
                      isActive ? "text-foreground font-medium" : "text-muted-foreground"
                    )}>
                      {segment.text}
                    </p>
                  </div>
                );
              })}

              {filteredTranscript?.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                  <Search className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm">No matches found for "{searchQuery}"</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}