import { z } from "zod";
export const CsvRow = z.object({
  Date: z.string(),
  Description: z.string(),
  Amount: z.string(),
  Currency: z.string().optional(),
  Balance: z.string().optional(),
  Type: z.string().optional(),
  Account: z.string().optional(),
});
export type CsvRow = z.infer<typeof CsvRow>;
