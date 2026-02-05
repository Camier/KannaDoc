"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const Homepage = () => {
  const router = useRouter();

  useEffect(() => {
    // Land directly in the primary workspace
    router.replace("/ai-chat");
  }, [router]);

  return (
    <div className="flex w-full h-screen items-center justify-center bg-slate-950">
      <div className="animate-pulse flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 font-serif italic tracking-widest text-sm">
          Initializing Research Workspace...
        </p>
      </div>
    </div>
  );
};

export default Homepage;
