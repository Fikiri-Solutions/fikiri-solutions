import { useEffect, useState } from "react"
import MeshBackground from "./MeshBackground"
import ParticleBackground from "./ParticleBackground"

export default function HybridBackground() {
  const [isMobile, setIsMobile] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkDevice = () => {
      const isMobileDevice = window.innerWidth < 768 || 
        /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
      setIsMobile(isMobileDevice)
      setIsLoading(false)
    }
    
    checkDevice()
    window.addEventListener("resize", checkDevice)
    return () => window.removeEventListener("resize", checkDevice)
  }, [])

  // Show loading state briefly to prevent flash
  if (isLoading) {
    return (
      <div className="fixed inset-0 w-full h-full z-0">
        <div 
          className="absolute inset-0 w-full h-full"
          style={{ 
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 30%, #7c2d12 60%, #991b1b 100%)' 
          }}
        />
      </div>
    )
  }

  // Use 3D mesh for desktop, particles for mobile
  return isMobile ? <ParticleBackground /> : <MeshBackground />
}
