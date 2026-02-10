'use server';

/**
 * @fileOverview Explains why a specific segment of the call was flagged, providing details such as confidence score,
 * relevant keywords, and the triggered compliance rule.
 *
 * - explainFlaggedEvent - A function that explains why a specific segment was flagged.
 * - ExplainFlaggedEventInput - The input type for the explainFlaggedEvent function.
 * - ExplainFlaggedEventOutput - The return type for the explainFlaggedEvent function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const ExplainFlaggedEventInputSchema = z.object({
  transcriptSegment: z
    .string()
    .describe('The specific segment of the transcript that was flagged.'),
  flaggedReason: z.string().describe('The reason why the segment was flagged.'),
  complianceRule: z.string().describe('The specific compliance rule triggered.'),
  confidenceScore: z
    .number()
    .describe('The confidence score of the flagged event (0-1).'),
  relevantKeywords: z
    .array(z.string())
    .describe('The keywords in the segment that contributed to the flag.'),
});
export type ExplainFlaggedEventInput = z.infer<typeof ExplainFlaggedEventInputSchema>;

const ExplainFlaggedEventOutputSchema = z.object({
  explanation: z
    .string()
    .describe(
      'A detailed explanation of why the segment was flagged, including the confidence score, relevant keywords, and the specific compliance rule that was triggered.'
    ),
});
export type ExplainFlaggedEventOutput = z.infer<typeof ExplainFlaggedEventOutputSchema>;

export async function explainFlaggedEvent(
  input: ExplainFlaggedEventInput
): Promise<ExplainFlaggedEventOutput> {
  return explainFlaggedEventFlow(input);
}

const prompt = ai.definePrompt({
  name: 'explainFlaggedEventPrompt',
  input: {schema: ExplainFlaggedEventInputSchema},
  output: {schema: ExplainFlaggedEventOutputSchema},
  prompt: `You are a compliance expert reviewing flagged segments of call transcripts.

You are provided with a transcript segment, the reason it was flagged, the compliance rule that was triggered, a confidence score, and relevant keywords.

Your task is to provide a clear and concise explanation of why the segment was flagged, using the provided information to support your explanation. Be sure to cite the compliance rule, relevant keywords, and confidence score appropriately.

Transcript Segment: {{{transcriptSegment}}}
Flagged Reason: {{{flaggedReason}}}
Compliance Rule: {{{complianceRule}}}
Confidence Score: {{{confidenceScore}}}
Relevant Keywords: {{#each relevantKeywords}}{{{this}}}{{#unless @last}}, {{/unless}}{{/each}}

Explanation:`,
});

const explainFlaggedEventFlow = ai.defineFlow(
  {
    name: 'explainFlaggedEventFlow',
    inputSchema: ExplainFlaggedEventInputSchema,
    outputSchema: ExplainFlaggedEventOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
