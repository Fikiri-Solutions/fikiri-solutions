import { useCallback } from 'react'
import Particles from '@tsparticles/react'
import { loadSlim } from '@tsparticles/slim'
import type { Engine } from '@tsparticles/engine'

export default function ParticleBackground() {
  // Initialize particles engine
  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine)
  }, [])

  // Particle configuration optimized for mobile
  const particlesConfig = {
    background: {
      color: {
        value: "transparent",
      },
    },
    fpsLimit: 30, // Lower FPS for mobile battery life
    interactivity: {
      events: {
        onClick: {
          enable: true,
          mode: "push",
        },
        onHover: {
          enable: true,
          mode: "repulse",
        },
        resize: true,
      },
      modes: {
        push: {
          quantity: 4,
        },
        repulse: {
          distance: 200,
          duration: 0.4,
        },
      },
    },
    particles: {
      color: {
        value: "#F97316", // Fikiri orange
      },
      links: {
        color: "#F97316", // Fikiri orange
        distance: 150,
        enable: true,
        opacity: 0.3,
        width: 1,
      },
      move: {
        direction: "none",
        enable: true,
        outModes: {
          default: "bounce",
        },
        random: false,
        speed: 0.5,
        straight: false,
        // Add wave-like movement
        path: {
          enable: true,
          options: {
            sides: {
              count: 1,
              value: 1
            }
          }
        },
        // Add gravity for wave effect
        gravity: {
          enable: true,
          acceleration: 0.1,
          maxSpeed: 0.5
        }
      },
      number: {
        density: {
          enable: true,
          area: 800,
        },
        value: 50, // Reduced for mobile performance
      },
      opacity: {
        value: 0.4,
        animation: {
          enable: true,
          speed: 0.5,
          minimumValue: 0.1,
          sync: false
        }
      },
      shape: {
        type: "circle",
      },
      size: {
        value: { min: 1, max: 4 },
        animation: {
          enable: true,
          speed: 1,
          minimumValue: 0.5,
          sync: false
        }
      },
    },
    detectRetina: true,
  }

  return (
    <div className="fixed inset-0 w-full h-full z-0">
      <div 
        className="absolute inset-0 w-full h-full"
        style={{ 
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 30%, #7c2d12 60%, #991b1b 100%)' 
        }}
      />
      <Particles
        id="tsparticles"
        init={particlesInit}
        options={particlesConfig}
        className="absolute inset-0 w-full h-full"
      />
    </div>
  )
}
