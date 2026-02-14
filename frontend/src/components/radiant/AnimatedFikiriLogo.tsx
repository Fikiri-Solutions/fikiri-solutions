import React, { useState, useEffect } from 'react'
import { FikiriLogo } from '@/components/FikiriLogo'

type AnimationType = 'rotate' | 'slide' | 'bounce' | 'pulse' | 'fade' | 'scale' | 'float'

const animationStyles: Record<AnimationType, string> = {
  rotate: 'animate-spin',
  slide: 'animate-[slide_3s_ease-in-out_infinite]',
  bounce: 'animate-bounce',
  pulse: 'animate-pulse',
  fade: 'animate-[fade_2s_ease-in-out_infinite]',
  scale: 'animate-[scale_2s_ease-in-out_infinite]',
  float: 'animate-[float_3s_ease-in-out_infinite]',
}

export function AnimatedFikiriLogo() {
  const [animation, setAnimation] = useState<AnimationType>('float')
  const [key, setKey] = useState(0)

  useEffect(() => {
    // Randomly select an animation type on mount
    const animations: AnimationType[] = ['rotate', 'slide', 'bounce', 'pulse', 'fade', 'scale', 'float']
    const randomAnimation = animations[Math.floor(Math.random() * animations.length)]
    setAnimation(randomAnimation)

    // Change animation every 4-6 seconds (randomized)
    const changeAnimation = () => {
      const newAnimation = animations[Math.floor(Math.random() * animations.length)]
      setAnimation(newAnimation)
      setKey(prev => prev + 1) // Force re-render with new animation
    }

    const interval = setInterval(changeAnimation, 4000 + Math.random() * 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <>
      <style>{`
        @keyframes slide {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(15px); }
        }
        @keyframes fade {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @keyframes scale {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.15); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-12px); }
        }
      `}</style>
      <div className="flex items-center" key={key}>
        <div className={`transition-all duration-700 ease-in-out ${animationStyles[animation]}`}>
          <FikiriLogo size="lg" variant="circle" className="h-20 w-20 md:h-24 md:w-24" />
        </div>
      </div>
    </>
  )
}
