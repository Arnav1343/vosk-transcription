"use client"

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { mockSessions } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Plus,
  Search,
  History,
  PhoneCall,
  Settings,
  Bell,
  ChevronRight,
  ShieldAlert,
  Calendar,
  Clock,
  User,
  Filter
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

export default function Dashboard() {
  const [search, setSearch] = useState('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Poll for sessions
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch('http://localhost:8000/sessions');
        if (res.ok) {
          const data = await res.json();
          setSessions(data);
        }
      } catch (e) {
        console.error("Failed to fetch sessions", e);
      }
    };

    fetchSessions();
    const interval = setInterval(fetchSessions, 3000); // Poll every 3s
    return () => clearInterval(interval);
  }, []);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      // Poll will catch the new session
    } catch (e) {
      console.error("Upload error", e);
      alert("Upload failed!");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const filtered = sessions.filter(s =>
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.agent.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar (Visual) */}
      <aside className="fixed left-0 top-0 bottom-0 w-64 bg-primary text-primary-foreground hidden lg:flex flex-col p-6 z-20">
        <div className="flex items-center gap-2 mb-10">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-primary" />
          </div>
          <span className="text-xl font-bold tracking-tight">AuditX</span>
        </div>

        <nav className="flex-1 space-y-2">
          <Link href="/" className="flex items-center gap-3 p-3 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
            <PhoneCall className="w-5 h-5" />
            <span className="font-medium">Call Audits</span>
          </Link>
          <Link href="/" className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/10 transition-colors">
            <History className="w-5 h-5" />
            <span className="font-medium">Recent History</span>
          </Link>
          <Link href="/" className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/10 transition-colors">
            <Bell className="w-5 h-5" />
            <span className="font-medium">Compliance Alerts</span>
          </Link>
        </nav>

        <div className="pt-6 border-t border-white/10">
          <Link href="/" className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/10 transition-colors">
            <Settings className="w-5 h-5" />
            <span className="font-medium">Settings</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 p-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Call Audit Workspace</h1>
              <p className="text-muted-foreground mt-2">Monitor and audit customer interactions with AI-driven insights.</p>
            </div>
            <div>
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".wav,.mp3"
                onChange={handleFileChange}
              />
              <Button size="lg" className="gap-2 shadow-md" onClick={handleUploadClick} disabled={isUploading}>
                {isUploading ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Plus className="w-5 h-5" />}
                {isUploading ? 'Uploading...' : 'Upload New Call'}
              </Button>
            </div>
          </header>

          {/* Stats Bar */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="bg-card border-none shadow-sm">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Audits</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold">{sessions.length}</span>
                  <span className="text-xs text-green-500 font-medium mb-1">+Live</span>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-card border-none shadow-sm">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-muted-foreground mb-1">Flagged Issues</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-destructive">
                    {sessions.filter(s => s.status === 'Flagged').length}
                  </span>
                  <span className="text-xs text-red-500 font-medium mb-1">Attention needed</span>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-card border-none shadow-sm">
              <CardContent className="p-6">
                <p className="text-sm font-medium text-muted-foreground mb-1">Review Rate</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-primary">98.2%</span>
                  <span className="text-xs text-muted-foreground mb-1">Avg. 4 min per call</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search calls by title, agent, or customer..."
                  className="pl-10 h-12 bg-card border-none shadow-sm"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Button variant="outline" className="h-12 px-6 gap-2">
                <Filter className="w-4 h-4" /> Filter
              </Button>
            </div>

            <div className="bg-card rounded-2xl border border-none shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Session Details</th>
                      <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Participants</th>
                      <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Audit Status</th>
                      <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Duration</th>
                      <th className="p-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Tags</th>
                      <th className="p-4"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {filtered.map((session) => (
                      <tr key={session.id} className="group hover:bg-muted/30 transition-colors">
                        <td className="p-4">
                          <Link href={`/session/${session.id}`} className="block hover:underline underline-offset-4">
                            <span className="font-bold text-foreground block">{session.title}</span>
                            <div className="flex items-center gap-1.5 mt-1">
                              <Calendar className="w-3 h-3 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">{session.date}</span>
                            </div>
                          </Link>
                        </td>
                        <td className="p-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                                <User className="w-3 h-3 text-primary" />
                              </div>
                              <span className="text-xs font-medium">{session.agent}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center">
                                <User className="w-3 h-3 text-muted-foreground" />
                              </div>
                              <span className="text-xs text-muted-foreground">{session.customer}</span>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge variant={session.status === 'Flagged' ? 'destructive' : session.status === 'Reviewed' ? 'default' : 'outline'}>
                            {session.status}
                          </Badge>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            {Math.floor(session.duration / 60)}:{(session.duration % 60).toString().padStart(2, '0')}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex flex-wrap gap-1">
                            {session.tags.map((tag, idx) => (
                              <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-medium uppercase">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="p-4 text-right">
                          <Link href={`/session/${session.id}`}>
                            <Button variant="ghost" size="icon" className="group-hover:translate-x-1 transition-transform">
                              <ChevronRight className="w-5 h-5" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}