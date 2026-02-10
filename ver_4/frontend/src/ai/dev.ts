import { config } from 'dotenv';
config();

import '@/ai/flows/flag-compliance-issues.ts';
import '@/ai/flows/explain-flagged-events.ts';