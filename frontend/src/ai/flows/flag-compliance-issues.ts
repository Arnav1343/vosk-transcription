'use server';

/**
 * @fileOverview Automatically flags potential compliance issues in call audio and transcript.
 *
 * - flagComplianceIssues - A function to detect and flag compliance issues.
 * - FlagComplianceIssuesInput - The input type for the flagComplianceIssues function.
 * - FlagComplianceIssuesOutput - The return type for the flagComplianceIssues function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const FlagComplianceIssuesInputSchema = z.object({
  transcript: z.string().describe('The transcript of the call.'),
});
export type FlagComplianceIssuesInput = z.infer<typeof FlagComplianceIssuesInputSchema>;

const FlagComplianceIssuesOutputSchema = z.object({
  flags: z
    .array(
      z.object({
        start: z.number().describe('Start time of the flagged issue in seconds.'),
        end: z.number().describe('End time of the flagged issue in seconds.'),
        type: z.string().describe('Type of compliance issue.'),
        confidence: z.number().describe('Confidence score of the flag.'),
        evidence: z.string().describe('AI reasoning and supporting evidence for the flag.'),
      })
    )
    .describe('List of compliance issues flagged in the transcript.'),
});
export type FlagComplianceIssuesOutput = z.infer<typeof FlagComplianceIssuesOutputSchema>;

export async function flagComplianceIssues(
  input: FlagComplianceIssuesInput
): Promise<FlagComplianceIssuesOutput> {
  return flagComplianceIssuesFlow(input);
}

const flagComplianceIssuesPrompt = ai.definePrompt({
  name: 'flagComplianceIssuesPrompt',
  input: {schema: FlagComplianceIssuesInputSchema},
  output: {schema: FlagComplianceIssuesOutputSchema},
  prompt: `You are an AI-powered compliance officer. Review the following call transcript and identify any potential compliance issues.

Transcript: {{{transcript}}}

Flag any instances of:
- Violations of privacy regulations (e.g., discussing sensitive customer data without consent)
- Misleading or unsubstantiated claims about products or services
- Failure to disclose important terms and conditions
- Discriminatory or biased statements

For each flagged issue, provide the start and end time in seconds, the type of compliance issue, a confidence score (0-1), and the AI reasoning behind the flag with supporting evidence from the transcript.

Output the result in JSON format.`,
});

const flagComplianceIssuesFlow = ai.defineFlow(
  {
    name: 'flagComplianceIssuesFlow',
    inputSchema: FlagComplianceIssuesInputSchema,
    outputSchema: FlagComplianceIssuesOutputSchema,
  },
  async input => {
    const {output} = await flagComplianceIssuesPrompt(input);
    return output!;
  }
);
