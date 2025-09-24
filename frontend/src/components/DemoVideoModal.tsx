import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Play, Pause, Volume2, VolumeX, Maximize2, RotateCcw } from 'lucide-react'
import { FikiriLogo } from './FikiriLogo'

interface DemoVideoModalProps {
  isOpen: boolean
  onClose: () => void
  videoUrl?: string
}

export const DemoVideoModal: React.FC<DemoVideoModalProps> = ({ 
  isOpen, 
  onClose, 
  videoUrl = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' // Placeholder - replace with your Kling AI generated video
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [progress, setProgress] = useState(0)
  const videoRef = React.useRef<HTMLVideoElement>(null)

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  // Video event handlers
  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleMuteToggle = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime
      const total = videoRef.current.duration
      setCurrentTime(current)
      setDuration(total)
      setProgress((current / total) * 100)
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (videoRef.current) {
      const seekTime = (parseFloat(e.target.value) / 100) * duration
      videoRef.current.currentTime = seekTime
      setCurrentTime(seekTime)
    }
  }

  const handleRestart = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      setCurrentTime(0)
      setProgress(0)
    }
  }

  const handleFullscreen = () => {
    if (videoRef.current) {
      if (!isFullscreen) {
        if (videoRef.current.requestFullscreen) {
          videoRef.current.requestFullscreen()
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen()
        }
      }
      setIsFullscreen(!isFullscreen)
    }
  }

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="relative w-full max-w-6xl mx-4 bg-gray-900 rounded-2xl overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 bg-gradient-to-r from-orange-600 to-red-600">
              <div className="flex items-center space-x-3">
                <FikiriLogo size="sm" variant="white" />
                <div>
                  <h2 className="text-xl font-bold text-white">Fikiri Solutions Demo</h2>
                  <p className="text-orange-100 text-sm">See how automation transforms your business</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                aria-label="Close demo video"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Video Player */}
            <div className="relative bg-black">
              <video
                ref={videoRef}
                className="w-full h-auto max-h-[70vh]"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={() => {
                  if (videoRef.current) {
                    setDuration(videoRef.current.duration)
                  }
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                poster="/api/placeholder/800/450" // Placeholder poster image
              >
                <source src={videoUrl} type="video/mp4" />
                Your browser does not support the video tag.
              </video>

              {/* Video Controls Overlay */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                {/* Progress Bar */}
                <div className="mb-4">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={progress}
                    onChange={handleSeek}
                    className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
                    style={{
                      background: `linear-gradient(to right, #FF6B35 0%, #FF6B35 ${progress}%, #4B5563 ${progress}%, #4B5563 100%)`
                    }}
                  />
                </div>

                {/* Control Buttons */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={handlePlayPause}
                      className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                      aria-label={isPlaying ? 'Pause video' : 'Play video'}
                    >
                      {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                    </button>

                    <button
                      onClick={handleRestart}
                      className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                      aria-label="Restart video"
                    >
                      <RotateCcw className="w-5 h-5" />
                    </button>

                    <button
                      onClick={handleMuteToggle}
                      className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                      aria-label={isMuted ? 'Unmute video' : 'Mute video'}
                    >
                      {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                    </button>

                    <span className="text-white text-sm font-mono">
                      {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                  </div>

                  <button
                    onClick={handleFullscreen}
                    className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                    aria-label="Toggle fullscreen"
                  >
                    <Maximize2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 bg-gray-800">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-white mb-2">Ready to Transform Your Business?</h3>
                <p className="text-gray-300 mb-4">
                  See how Fikiri Solutions can automate your workflows and boost productivity
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <button
                    onClick={() => {
                      onClose()
                      window.location.href = '/signup'
                    }}
                    className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-red-700 transition-all duration-300"
                  >
                    Get Started Free
                  </button>
                  <button
                    onClick={() => {
                      onClose()
                      window.location.href = '/pricing'
                    }}
                    className="px-6 py-3 border border-orange-400 text-orange-400 font-semibold rounded-lg hover:bg-orange-500/20 transition-all duration-300"
                  >
                    View Pricing
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default DemoVideoModal
