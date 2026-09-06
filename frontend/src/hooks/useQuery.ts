import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useAskQuery() {
  return useMutation({
    mutationFn: ({ question, connectionId }: { question: string; connectionId: number }) =>
      api.query(question, connectionId),
  });
}
