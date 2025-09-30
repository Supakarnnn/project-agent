"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export default function AdminGuard({ children }) {
  const r = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(null);

  const isPublic = pathname === "/admin/login";
  useEffect(() => {
    if (isPublic) { setOk(true); return; }

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(process.env.NEXT_PUBLIC_API_URL + "/auth/check", {
          credentials: "include",
          cache: "no-store",
        });
        if (!cancelled) {
          if (res.ok) setOk(true);
          else { setOk(false); r.replace("/admin/login"); }
        }
      } catch {
        if (!cancelled) { setOk(false); r.replace("/admin/login"); }
      }
    })();
    return () => { cancelled = true; };
  }, [r, isPublic]);

  if (ok === null) {
    return <div className="min-h-screen grid place-items-center">Checking session…</div>;
  }
  if (!ok) return null;

  return <>{children}</>;
}
