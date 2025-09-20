export type Direction = "in" | "out";
export type Tx = {
  id: string;
  date: string;        // ISO yyyy-mm-dd
  description: string;
  amount: number;      // positive
  direction: Direction;
  account: string;
  category?: string;
  note?: string;
};
