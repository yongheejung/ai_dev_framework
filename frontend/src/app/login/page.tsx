"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/features/auth/hooks/useLogin";
import { useRegister } from "@/features/auth/hooks/useRegister";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const register = useRegister();

  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registerForm, setRegisterForm] = useState({ username: "", password: "" });
  const [registerMessage, setRegisterMessage] = useState<string | null>(null);

  function handleLogin(event: FormEvent) {
    event.preventDefault();
    login.mutate(loginForm, { onSuccess: () => router.push("/") });
  }

  function handleRegister(event: FormEvent) {
    event.preventDefault();
    register.mutate(registerForm, {
      onSuccess: (username) => {
        setRegisterMessage(`${username} 계정이 생성되었습니다. 로그인해 주세요.`);
        setRegisterForm({ username: "", password: "" });
      },
    });
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>로그인</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="flex flex-col gap-3">
            <Input
              placeholder="아이디"
              value={loginForm.username}
              onChange={(event) => setLoginForm((form) => ({ ...form, username: event.target.value }))}
            />
            <Input
              type="password"
              placeholder="비밀번호"
              value={loginForm.password}
              onChange={(event) => setLoginForm((form) => ({ ...form, password: event.target.value }))}
            />
            <Button type="submit" disabled={login.isPending}>
              {login.isPending ? "로그인 중..." : "로그인"}
            </Button>
            {login.error && <p className="text-sm text-destructive">{login.error.message}</p>}
          </form>
          <p className="mt-3 text-xs text-muted-foreground">개발용 admin 계정: admin / admin1234</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>회원가입</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRegister} className="flex flex-col gap-3">
            <Input
              placeholder="아이디"
              value={registerForm.username}
              onChange={(event) =>
                setRegisterForm((form) => ({ ...form, username: event.target.value }))
              }
            />
            <Input
              type="password"
              placeholder="비밀번호 (8자 이상)"
              value={registerForm.password}
              onChange={(event) =>
                setRegisterForm((form) => ({ ...form, password: event.target.value }))
              }
            />
            <Button type="submit" variant="secondary" disabled={register.isPending}>
              {register.isPending ? "가입 중..." : "회원가입"}
            </Button>
            {register.error && <p className="text-sm text-destructive">{register.error.message}</p>}
            {registerMessage && <p className="text-sm text-muted-foreground">{registerMessage}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
