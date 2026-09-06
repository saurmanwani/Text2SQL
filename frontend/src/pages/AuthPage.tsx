import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { authenticate } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await authenticate(mode, email, password);
      navigate("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed");
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 px-6">
      <Card className="w-full max-w-sm">
        <CardHeader><CardTitle>{mode === "login" ? "Welcome back" : "Create account"}</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <input type="email" required placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-md border px-3 py-2" />
            <input type="password" required minLength={8} placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-md border px-3 py-2" />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="w-full rounded-md bg-primary py-2 text-primary-foreground">
              {mode === "login" ? "Log in" : "Register"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {mode === "login" ? "Need an account? " : "Already registered? "}
            <Link className="underline" to={mode === "login" ? "/register" : "/login"}>
              {mode === "login" ? "Register" : "Log in"}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
