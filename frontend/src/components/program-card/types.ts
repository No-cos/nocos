// types.ts — ProgramCard component props

import type { Program } from "@/lib/api";

export interface ProgramCardProps {
  program: Program;
  /** Optional animation entrance index for stagger delay (matches IssueCard pattern) */
  animationIndex?: number;
}
