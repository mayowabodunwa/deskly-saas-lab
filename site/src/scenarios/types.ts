// The shape of a ticket-simulator scenario. One scenario = one ticket, with
// several possible hidden causes ("variants"). Each run picks a variant at
// random, so the same ticket can be practised more than once.

export type Action = {
  id: string;
  label: string;        // what the reader chooses, in plain words
  command?: string;     // the command it stands for, if any
  minutes: number;      // how long it takes in real life
};

export type Result = {
  text: string;         // what happened, in plain words
  output?: string;      // real output, quoted exactly
};

export type Variant = {
  id: string;
  cause: string;        // id of the matching Cause
  results: Record<string, Result>;  // one per Action id
  fix: { command: string; text: string };
  fastest: string;      // the most direct route to the answer
};

export type Scenario = {
  title: string;
  ticket: string;
  actions: Action[];
  causes: { id: string; label: string }[];
  wrongFixMinutes: number;
  variants: Variant[];
};
