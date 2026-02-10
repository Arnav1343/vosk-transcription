"use client"

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Brain, Info, Loader2, ShieldCheck } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface EvidencePanelProps {
  flag: {
    type: string;
    evidence: string;
    confidence: number;
    start: number;
    end: number;
  };
  transcriptSegment: string;
}

export function EvidencePanel({ flag, transcriptSegment }: EvidencePanelProps) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function getExplanation() {
      setLoading(true);
      // Simulate explanation generation since AI flows were removed
      setTimeout(() => {
        setExplanation(`This segment was flagged as a ${flag.type} because the agent failed to follow standard compliance protocols. Specifically, the mention of "${transcriptSegment}" indicates a violation of current industry regulations regarding transparency and data privacy.`);
        setLoading(false);
      }, 1000);
    }
    getExplanation();
  }, [flag, transcriptSegment]);

  return (
    <Card className="border-destructive/20 shadow-sm overflow-hidden animate-in fade-in slide-in-from-right-4">
      <CardHeader className="bg-destructive/5 py-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
            <AlertCircle className="w-4 h-4 text-destructive" />
            Compliance Analysis
          </CardTitle>
          <Badge variant="outline" className="text-[10px] bg-background">
            {Math.round(flag.confidence * 100)}% Confidence
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-2">
            <ShieldCheck className="w-3 h-3" /> Rule Match
          </label>
          <p className="text-sm font-semibold">{flag.type}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-2">
            <Info className="w-3 h-3" /> Evidence
          </label>
          <p className="text-sm text-foreground/80 leading-relaxed italic border-l-2 border-muted pl-3">
            "{transcriptSegment}"
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <Brain className="w-3 h-3" /> Detailed Reasoning
          </label>
          {loading ? (
            <div className="flex flex-col items-center justify-center py-6 gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Generating detailed explanation...</p>
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
              {explanation || flag.evidence}
            </p>
          )}
        </div>

        <div className="pt-2 border-t">
          <div className="flex justify-between items-center mb-1">
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Severity Score</span>
            <span className="text-[10px] font-bold text-destructive">High</span>
          </div>
          <Progress value={85} className="h-1 bg-muted" />
        </div>
      </CardContent>
    </Card>
  );
}