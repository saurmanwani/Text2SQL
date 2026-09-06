import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useAskQuery() {
  return useMutation({
    mutationFn: ({
      question,
      connectionId,
      history,
    }: {
      question: string;
      connectionId: number;
      history: { question: string; sql: string }[];
    }) => api.query(question, connectionId, history),
  });
}
