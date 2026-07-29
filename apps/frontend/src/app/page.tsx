"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { homePathForRole, readRoleCookie } from "@/lib/roles";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const role = readRoleCookie();
    if (token && role) {
      router.replace(homePathForRole(role));
    }
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-bmw-blue to-blue-900 px-6">
      <div className="max-w-xl text-center">
        <p className="mb-3 text-sm uppercase tracking-widest text-blue-200">
          BMW AI Platform
        </p>
        <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl">
          Sign in to continue
        </h1>
        <p className="mb-10 text-lg text-blue-100/90">
          Role-based access for drivers, fleet managers, and admins. Features
          unlock after login.
        </p>
        <Link
          href="/login"
          className="inline-block rounded-lg bg-white px-10 py-3.5 text-lg font-bold text-bmw-blue hover:bg-blue-50"
        >
          Login
        </Link>
        <p className="mt-6 text-sm text-blue-200/80">
          New org?{" "}
          <Link href="/register" className="underline hover:text-white">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
