"use client"

import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';

interface Flag {
  start: number;
  end: number;
  type: string;
}

interface WaveformTimelineProps {
  duration: number;
  currentTime: number;
  onSeek: (time: number) => void;
  flags: Flag[];
}

export function WaveformTimeline({ duration, currentTime, onSeek, flags }: WaveformTimelineProps) {
  const barsCount = 60;
  
  const bars = useMemo(() => {
    return Array.from({ length: barsCount }).map((_, i) => ({
      height: Math.random() * 80 + 20,
      active: (i / barsCount) * duration <= currentTime
    }));
  }, [duration, currentTime]);

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    onSeek(percentage * duration);
  };

  return (
    <div className="relative w-full h-24 bg-card rounded-xl border p-4 cursor-pointer overflow-hidden group" onClick={handleTimelineClick}>
      <div className="flex items-center justify-between w-full h-full gap-1">
        {bars.map((bar, i) => (
          <div
            key={i}
            className={cn(
              "waveform-bar w-full rounded-full transition-all duration-300",
              bar.active ? "bg-primary" : "bg-muted-foreground/20"
            )}
            style={{ height: `${bar.height}%` }}
          />
        ))}
      </div>
      
      {/* Flag Indicators */}
      {flags.map((flag, idx) => {
        const left = (flag.start / duration) * 100;
        const width = ((flag.end - flag.start) / duration) * 100;
        return (
          <div
            key={idx}
            className="absolute top-0 h-1 bg-destructive rounded-full"
            style={{ 
              left: `${Math.max(0, left)}%`, 
              width: `${Math.max(1, width)}%` 
            }}
          />
        );
      })}

      {/* Current Time Indicator */}
      <div 
        className="absolute top-0 bottom-0 w-0.5 bg-accent transition-all duration-100 ease-linear pointer-events-none"
        style={{ left: `${(currentTime / duration) * 100}%` }}
      >
        <div className="absolute -top-1 -left-1.5 w-3 h-3 bg-accent rounded-full shadow-lg" />
      </div>

      {/* Time labels */}
      <div className="absolute bottom-1 left-2 text-[10px] text-muted-foreground font-mono">
        {formatTime(currentTime)}
      </div>
      <div className="absolute bottom-1 right-2 text-[10px] text-muted-foreground font-mono">
        {formatTime(duration)}
      </div>
    </div>
  );
}

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}