"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Leaf } from "lucide-react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function LandingPage() {
  const router = useRouter();
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    setAnimateIn(true);
  }, []);

  return (
    <div className="min-h-screen bg-[#FDF8F5] flex overflow-hidden font-sans">
      
      {/* Left Content Area (60%) */}
      <div className="w-full lg:w-3/5 flex flex-col justify-center px-8 sm:px-16 lg:px-24 xl:px-32 relative z-10">
        
        {/* Logo / Brand */}
        <div className={`absolute top-10 left-8 sm:left-16 lg:left-24 transition-all duration-1000 transform ${animateIn ? 'translate-y-0 opacity-100' : '-translate-y-10 opacity-0'}`}>
          <div className="flex items-center gap-2 text-[#D35400]">
            <Leaf className="w-8 h-8" />
            <span className="text-3xl font-extrabold tracking-tight">Khadira</span>
          </div>
        </div>

        <div className="max-w-xl">
          <div className={`transition-all duration-1000 delay-300 transform ${animateIn ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <p className="text-[#E67E22] font-semibold tracking-wider uppercase text-sm mb-4">
              Heritage Weaving System
            </p>
            <h1 className="text-5xl sm:text-6xl font-bold text-[#2C3E50] leading-tight mb-6 font-serif">
              Weaving tradition <br /> into the future.
            </h1>
            <p className="text-lg text-slate-600 mb-10 leading-relaxed">
              Experience the harmony of centuries-old craftsmanship and modern digital precision. Khadira connects your entire mill—from raw yarn intake to final dispatch—in one unified platform.
            </p>
            
            <button 
              onClick={() => router.push('/dashboard')}
              className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-white transition-all duration-300 bg-[#D35400] rounded-full hover:bg-[#A04000] hover:shadow-lg hover:shadow-[#D35400]/30 focus:outline-none focus:ring-4 focus:ring-[#D35400]/50 overflow-hidden"
            >
              <span className="relative z-10 flex items-center gap-3">
                Enter Dashboard
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Right Image Area (40%) */}
      <div className="hidden lg:block lg:w-2/5 relative bg-[#E67E22]/10 h-screen">
        <div className="absolute inset-0 w-full h-full">
          {/* Subtle gradient overlay to blend into the pink/terracotta background */}
          <div className="absolute inset-0 bg-gradient-to-l from-transparent to-[#FDF8F5] z-10"></div>
          
          <div className={`relative w-full h-full transition-all duration-1000 delay-500 transform ${animateIn ? 'translate-x-0 opacity-100' : 'translate-x-20 opacity-0'}`}>
            <Image 
              src="/hero-weaving.jpg" 
              alt="Indian woman weaving on a traditional charkha" 
              layout="fill" 
              objectFit="cover"
              objectPosition="center right"
              className="z-0 animate-[weave-pulse_4s_ease-in-out_infinite]"
              priority
            />
            {/* Overlay to warm up the image to match theme */}
            <div className="absolute inset-0 bg-[#D35400]/10 mix-blend-multiply z-10"></div>
          </div>
        </div>
      </div>

      {/* Custom Keyframes for gentle motion */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes weave-pulse {
          0% { transform: scale(1); filter: brightness(1); }
          50% { transform: scale(1.02); filter: brightness(1.05); }
          100% { transform: scale(1); filter: brightness(1); }
        }
      `}} />
    </div>
  );
}
