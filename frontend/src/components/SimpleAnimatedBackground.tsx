import React from 'react'

const SimpleAnimatedBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 w-full h-full z-0 overflow-hidden">
      {/* Base gradient background */}
      <div 
        className="absolute inset-0 w-full h-full"
        style={{ 
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 30%, #7c2d12 60%, #991b1b 100%)' 
        }}
      />
      
      {/* Animated mesh lines using CSS */}
      <div className="absolute inset-0 w-full h-full">
        {/* Horizontal lines */}
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={`h-${i}`}
            className="absolute w-full h-px bg-gradient-to-r from-transparent via-orange-500/30 to-transparent"
            style={{
              top: `${(i * 5) + 10}%`,
              animation: `floatHorizontal ${8 + (i % 3)}s ease-in-out infinite`,
              animationDelay: `${i * 0.2}s`,
              transform: `translateX(${Math.sin(i) * 50}px)`
            }}
          />
        ))}
        
        {/* Vertical lines */}
        {Array.from({ length: 15 }).map((_, i) => (
          <div
            key={`v-${i}`}
            className="absolute h-full w-px bg-gradient-to-b from-transparent via-red-500/30 to-transparent"
            style={{
              left: `${(i * 7) + 5}%`,
              animation: `floatVertical ${10 + (i % 4)}s ease-in-out infinite`,
              animationDelay: `${i * 0.3}s`,
              transform: `translateY(${Math.cos(i) * 30}px)`
            }}
          />
        ))}
        
        {/* Floating particles */}
        {Array.from({ length: 50 }).map((_, i) => (
          <div
            key={`particle-${i}`}
            className="absolute w-1 h-1 bg-orange-400 rounded-full opacity-60"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `floatParticle ${12 + (i % 5)}s ease-in-out infinite`,
              animationDelay: `${i * 0.1}s`,
              boxShadow: '0 0 6px rgba(251, 146, 60, 0.8)'
            }}
          />
        ))}
      </div>
      
      {/* CSS Animations */}
        <style dangerouslySetInnerHTML={{ __html: `
        @keyframes floatHorizontal {
          0%, 100% { transform: translateX(0px) scaleX(1); opacity: 0.3; }
          25% { transform: translateX(20px) scaleX(1.1); opacity: 0.6; }
          50% { transform: translateX(-10px) scaleX(0.9); opacity: 0.4; }
          75% { transform: translateX(15px) scaleX(1.05); opacity: 0.7; }
        }
        
        @keyframes floatVertical {
          0%, 100% { transform: translateY(0px) scaleY(1); opacity: 0.3; }
          25% { transform: translateY(-15px) scaleY(1.1); opacity: 0.6; }
          50% { transform: translateY(10px) scaleY(0.9); opacity: 0.4; }
          75% { transform: translateY(-8px) scaleY(1.05); opacity: 0.7; }
        }
        
        @keyframes floatParticle {
          0%, 100% { 
            transform: translate(0px, 0px) scale(1); 
            opacity: 0.6; 
          }
          25% { 
            transform: translate(10px, -15px) scale(1.2); 
            opacity: 0.8; 
          }
          50% { 
            transform: translate(-5px, 8px) scale(0.8); 
            opacity: 0.4; 
          }
          75% { 
            transform: translate(8px, -5px) scale(1.1); 
            opacity: 0.9; 
          }
        }
      `}} />
    </div>
  )
}

export default SimpleAnimatedBackground
